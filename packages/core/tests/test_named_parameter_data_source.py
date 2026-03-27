"""
tests/test_named_parameter_data_source.py — Tests for NamedParameterDataSource.

Each test gets a freshly-registered sqlite driver via the ``sqlite_driver``
autouse fixture, following the K023 pattern from test_pooled_data_source.py.

Because DataSource opens a new connection per call and :memory: SQLite is
per-connection, tests that need persistent state (CREATE TABLE, then INSERT,
then SELECT) use a temporary file-backed SQLite database so that all
connections within a test share the same on-disk data.  Tests that only need
a single connection use :memory: directly via get_connection().
"""

from __future__ import annotations

import sqlite3
import tempfile
import os

import pytest

from pydbc_core import NamedParameterDataSource
from pydbc_core.driver_manager import DriverManager
from pydbc_core.generic_db_api_driver import GenericDbApiDriver

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SQLITE_MEMORY_URL = "pydbc:sqlite::memory:"


@pytest.fixture(autouse=True)
def sqlite_driver() -> None:  # type: ignore[return]
    """Register a fresh sqlite driver before each test and clear the registry after."""
    driver = GenericDbApiDriver(sqlite3, "pydbc:sqlite:")
    DriverManager.register_driver(driver)
    yield
    DriverManager.clear()


@pytest.fixture()
def file_ds(tmp_path):
    """Return a NamedParameterDataSource backed by a temp file SQLite DB.

    Each connection call opens the same on-disk file, so DDL/DML from one
    call is visible to subsequent calls within the same test.
    """
    db_path = str(tmp_path / "test.db")
    return NamedParameterDataSource(f"pydbc:sqlite:{db_path}")


# ---------------------------------------------------------------------------
# Test 1: import smoke
# ---------------------------------------------------------------------------


def test_import_smoke() -> None:
    """NamedParameterDataSource can be imported from pydbc_core without error."""
    from pydbc_core import NamedParameterDataSource as NPDS  # noqa: PLC0415

    assert NPDS is not None


# ---------------------------------------------------------------------------
# Test 2: query returns a ResultSet with correct data
# ---------------------------------------------------------------------------


def test_query_returns_result_set(file_ds) -> None:
    """query() with a single named param returns a ResultSet with the matching row."""
    file_ds.update("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)", {})
    file_ds.update("INSERT INTO t (id, name) VALUES (:id, :name)", {"id": 1, "name": "Alice"})

    rs = file_ds.query("SELECT name FROM t WHERE id = :id", {"id": 1})

    assert rs.next() is True
    assert rs.get_object(1) == "Alice"
    assert rs.next() is False  # only one matching row


# ---------------------------------------------------------------------------
# Test 3: query with multiple named params filters correctly
# ---------------------------------------------------------------------------


def test_query_multiple_params(file_ds) -> None:
    """query() with two named params returns only the row matching both conditions."""
    file_ds.update("CREATE TABLE t (a INTEGER, b INTEGER, label TEXT)", {})
    file_ds.update("INSERT INTO t VALUES (:a, :b, :label)", {"a": 1, "b": 2, "label": "match"})
    file_ds.update("INSERT INTO t VALUES (:a, :b, :label)", {"a": 1, "b": 9, "label": "no-b"})
    file_ds.update("INSERT INTO t VALUES (:a, :b, :label)", {"a": 9, "b": 2, "label": "no-a"})

    rs = file_ds.query("SELECT label FROM t WHERE a = :a AND b = :b", {"a": 1, "b": 2})

    assert rs.next() is True
    assert rs.get_object("label") == "match"
    assert rs.next() is False  # only one matching row


# ---------------------------------------------------------------------------
# Test 4: update inserts a row and returns count 1
# ---------------------------------------------------------------------------


def test_update_inserts_row(file_ds) -> None:
    """update() for an INSERT returns 1 and the row is visible on subsequent query."""
    file_ds.update("CREATE TABLE t (name TEXT)", {})

    count = file_ds.update("INSERT INTO t (name) VALUES (:name)", {"name": "Bob"})
    assert count == 1

    rs = file_ds.query("SELECT name FROM t", {})
    assert rs.next() is True
    assert rs.get_object("name") == "Bob"


# ---------------------------------------------------------------------------
# Test 5: update returns correct row count across multiple calls
# ---------------------------------------------------------------------------


def test_update_returns_row_count(file_ds) -> None:
    """Each update() call returns the exact number of affected rows."""
    file_ds.update("CREATE TABLE t (id INTEGER, val INTEGER)", {})

    # Each INSERT affects 1 row
    for i in range(3):
        cnt = file_ds.update("INSERT INTO t VALUES (:id, :val)", {"id": i, "val": i * 10})
        assert cnt == 1

    # A bulk UPDATE affecting multiple rows
    bulk = file_ds.update("UPDATE t SET val = :val WHERE val >= :floor", {"val": 99, "floor": 0})
    assert bulk == 3


# ---------------------------------------------------------------------------
# Test 6: get_connection is inherited and returns a usable connection
# ---------------------------------------------------------------------------


def test_get_connection_inherited() -> None:
    """get_connection() (inherited from DataSource) returns a working connection."""
    ds = NamedParameterDataSource(SQLITE_MEMORY_URL)
    conn = ds.get_connection()
    try:
        stmt = conn.create_statement()
        rs = stmt.execute_query("SELECT 1")
        assert rs.next() is True
        assert rs.get_object(1) == 1
    finally:
        conn.close()
