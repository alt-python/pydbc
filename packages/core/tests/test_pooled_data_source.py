"""
tests/test_pooled_data_source.py — Tests for PooledDataSource and SimpleConnectionPool.

Each test gets a freshly-registered sqlite driver via the ``sqlite_driver``
autouse fixture.  The fixture re-registers the driver before and clears the
registry after, mirroring the pattern used by test_driver_manager.py and
test_compliance.py so tests can run in any order.
"""

from __future__ import annotations

import queue
import sqlite3
import threading
import time

import pytest

from pydbc_core import PooledDataSource, SimpleConnectionPool
from pydbc_core.driver_manager import DriverManager
from pydbc_core.generic_db_api_driver import GenericDbApiDriver


# ---------------------------------------------------------------------------
# Fixture: ensure the sqlite driver is registered for every test in this module
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def sqlite_driver() -> None:  # type: ignore[return]
    """Register a fresh SqliteDriver before each test and clear the registry after."""
    driver = GenericDbApiDriver(sqlite3, "pydbc:sqlite:")
    DriverManager.register_driver(driver)
    yield
    DriverManager.clear()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

SQLITE_URL = "pydbc:sqlite::memory:"


def _make_ds(max: int = 5, **extra: object) -> PooledDataSource:  # noqa: A002
    return PooledDataSource(SQLITE_URL, pool={"max": max, **extra})


# ---------------------------------------------------------------------------
# Test 1: acquired connection is usable
# ---------------------------------------------------------------------------


def test_get_connection_returns_usable_connection() -> None:
    """get_connection() returns a connection that can execute SELECT 1."""
    ds = _make_ds(max=5)
    try:
        conn = ds.get_connection()
        try:
            stmt = conn.create_statement()
            rs = stmt.execute_query("SELECT 1")
            assert rs is not None
        finally:
            conn.close()
    finally:
        ds.destroy()


# ---------------------------------------------------------------------------
# Test 2: pool limit is enforced — third acquire blocks until a slot opens
# ---------------------------------------------------------------------------


def test_pool_limit_enforced_with_blocking() -> None:
    """A third acquire blocks when max=2; releasing one slot unblocks it."""
    ds = _make_ds(max=2, acquire_timeout=2.0)
    pool = ds._pool
    try:
        conns = [ds.get_connection() for _ in range(2)]
        assert pool.num_used == 2

        result: list[object] = []

        def try_acquire() -> None:
            try:
                c = ds.get_connection()  # will block until a slot opens
                result.append(c)
            except Exception as exc:  # noqa: BLE001
                result.append(exc)

        t = threading.Thread(target=try_acquire, daemon=True)
        t.start()
        time.sleep(0.05)  # give the thread time to reach the blocking acquire
        assert len(result) == 0, "thread should still be blocked"

        conns[0].close()  # release one → unblocks the background thread
        t.join(timeout=2.0)
        assert t.is_alive() is False, "background thread did not unblock in time"
        assert len(result) == 1
        assert not isinstance(result[0], Exception), f"expected connection, got {result[0]}"

        # Clean up remaining connections
        result[0].close()  # type: ignore[union-attr]
        conns[1].close()

        assert pool.num_used == 0
    finally:
        ds.destroy()


# ---------------------------------------------------------------------------
# Test 3: context manager returns connection to pool
# ---------------------------------------------------------------------------


def test_with_conn_returns_to_pool() -> None:
    """After 'with ds.get_connection()', conn.is_closed() is True and pool counters reset."""
    ds = _make_ds(max=3)
    pool = ds._pool
    try:
        with ds.get_connection() as conn:
            assert not conn.is_closed()
            assert pool.num_used == 1

        assert conn.is_closed(), "proxy should be closed after context exit"
        assert pool.num_free == 1, f"expected 1 free, got {pool.num_free}"
        assert pool.num_used == 0, f"expected 0 used, got {pool.num_used}"
    finally:
        ds.destroy()


# ---------------------------------------------------------------------------
# Test 4: pool counters are consistent across acquire/release cycle
# ---------------------------------------------------------------------------


def test_pool_counters_consistent() -> None:
    """num_used + num_free <= max at all points; counters reset after full release."""
    ds = _make_ds(max=5)
    pool = ds._pool
    try:
        conns = [ds.get_connection() for _ in range(3)]

        assert pool.num_used == 3, f"expected 3 used, got {pool.num_used}"
        # No pre-warmed connections, so num_free == 0 before any are returned.
        assert pool.num_free == 0, f"expected 0 free, got {pool.num_free}"
        assert pool.num_used + pool.num_free <= 5

        for c in conns:
            c.close()

        assert pool.num_used == 0, f"expected 0 used after release, got {pool.num_used}"
        assert pool.num_free == 3, f"expected 3 free after release, got {pool.num_free}"
        assert pool.num_used + pool.num_free <= 5
    finally:
        ds.destroy()


# ---------------------------------------------------------------------------
# Test 5: acquire_timeout raises queue.Empty when pool is exhausted
# ---------------------------------------------------------------------------


def test_acquire_timeout_raises() -> None:
    """Acquiring beyond max with a short timeout raises queue.Empty."""
    ds = _make_ds(max=1, acquire_timeout=0.1)
    try:
        held = ds.get_connection()
        try:
            with pytest.raises(queue.Empty):
                ds.get_connection()
        finally:
            held.close()
    finally:
        ds.destroy()


# ---------------------------------------------------------------------------
# Test 6: destroy drains the pool
# ---------------------------------------------------------------------------


def test_destroy_drains_pool() -> None:
    """destroy() closes all idle connections; num_free and num_used both reach 0."""
    ds = _make_ds(max=3)
    pool = ds._pool
    conns = [ds.get_connection() for _ in range(2)]
    for c in conns:
        c.close()

    assert pool.num_free == 2

    ds.destroy()

    assert pool.num_free == 0, f"expected 0 free after destroy, got {pool.num_free}"
    assert pool.num_used == 0, f"expected 0 used after destroy, got {pool.num_used}"


# ---------------------------------------------------------------------------
# Test 7: connection_pool kwarg bypasses internal SimpleConnectionPool creation
# ---------------------------------------------------------------------------


def test_connection_pool_kwarg_accepted() -> None:
    """PooledDataSource accepts an external connection_pool= and uses it."""
    factory = {
        "create": lambda: sqlite3.connect(":memory:"),
        "destroy": lambda c: c.close(),
    }
    external_pool = SimpleConnectionPool(factory, {"max": 3})
    ds = PooledDataSource(SQLITE_URL, connection_pool=external_pool)
    try:
        conn = ds.get_connection()
        try:
            # The underlying raw sqlite3 connection doesn't have create_statement,
            # so exercise it via the proxy's underlying real connection directly.
            stmt = conn._real.execute("SELECT 1")
            row = stmt.fetchone()
            assert row == (1,)
        finally:
            conn.close()
    finally:
        ds.destroy()
