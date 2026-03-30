"""
tests/test_teradata_compliance.py — Compliance tests for pydbc-teradata.

Imports pydbc_teradata to trigger self-registration, then exercises the
Teradata-compatible compliance suite.

Notes:
  - Teradata does NOT support ``CREATE TABLE IF NOT EXISTS`` (K019).
  - Teradata does NOT support ``DROP TABLE IF EXISTS`` — plain ``DROP TABLE``
    is used with errors swallowed (same as jsdbc ``ignoreDropError:true``).
  - Paramstyle is ``qmark`` — teradatasql uses ``?`` natively.
  - ``conn.commit()`` is called after DML regardless of autocommit setting
    (K027).
  - ``test_accepts_url`` and ``test_self_registers_on_import`` do NOT depend
    on the ``teradata_url`` fixture — they pass unconditionally whether or not
    TERADATA_HOST is set.
  - ``test_compliance_suite`` takes the session-scoped ``teradata_url``
    fixture; it is automatically skipped when TERADATA_HOST is unset.
"""

from __future__ import annotations

import importlib
import sys

import pytest

import pydbc_teradata  # noqa: F401 — triggers self-registration
from pydbc_teradata import TeradataDriver
from pydbc_core import DriverManager
from pydbc_core.connection import Connection


# ---------------------------------------------------------------------------
# Local compliance suite (Teradata-compatible DDL)
# ---------------------------------------------------------------------------


def _exec_sql(conn: Connection, sql: str, params: tuple = ()) -> int:
    """Execute DML/DDL using a PreparedStatement and return rowcount."""
    stmt = conn.prepare_statement(sql)
    for i, value in enumerate(params, start=1):
        stmt.set_parameter(i, value)
    return stmt.execute_update()


def _query_sql(conn: Connection, sql: str, params: tuple = ()):
    """Execute a SELECT using a PreparedStatement and return a ResultSet."""
    stmt = conn.prepare_statement(sql)
    for i, value in enumerate(params, start=1):
        stmt.set_parameter(i, value)
    return stmt.execute_query()


def run_teradata_compliance_suite(driver: TeradataDriver, url: str) -> None:
    """Run a complete create/insert/select/drop compliance cycle against Teradata.

    Uses plain ``CREATE TABLE`` (no ``IF NOT EXISTS``) and a table name
    distinct from other driver suites to avoid cross-test collisions.

    Steps:
        1. Pre-cleanup: ``DROP TABLE pydbc_teradata_compliance`` wrapped in
           try/except that swallows all errors — prevents CREATE TABLE from
           failing on stale state from a prior crashed run.  Teradata does not
           support ``DROP TABLE IF EXISTS`` (jsdbc: ``ignoreDropError: true``).
        2. ``CREATE TABLE pydbc_teradata_compliance (id INTEGER, name VARCHAR(100))``
        3. INSERT row 1 with ``?`` positional params (qmark paramstyle — confirmed
           by jsdbc PreparedStatement tests).
        4. INSERT row 2 with ``:name`` named params — the normalizer converts
           ``:name`` to ``?`` for the qmark target.
        5. ``conn.commit()`` after DML (K027 — safe whether autocommit is on or off).
        6. SELECT and assert 2 rows.
        7. ``DROP TABLE pydbc_teradata_compliance`` (cleanup — plain drop, no IF EXISTS).

    Args:
        driver: A :class:`TeradataDriver` instance to test.
        url:    The pydbc URL to connect to (e.g. ``'pydbc:teradata://...'``).

    Raises:
        AssertionError: If any compliance check fails.
    """
    with driver.connect(url, None) as conn:
        # 1. Pre-cleanup: drop stale table, ignore errors (Teradata has no IF EXISTS)
        try:
            _exec_sql(conn, "DROP TABLE pydbc_teradata_compliance")
        except Exception:  # noqa: BLE001
            pass

        # 2. CREATE TABLE — plain; no IF NOT EXISTS on Teradata (K019)
        _exec_sql(
            conn,
            "CREATE TABLE pydbc_teradata_compliance "
            "(id INTEGER, name VARCHAR(100))",
        )

        # 3. INSERT row 1 with ? positional params (qmark passthrough)
        _exec_sql(
            conn,
            "INSERT INTO pydbc_teradata_compliance VALUES (?, ?)",
            params=(1, "hello"),
        )

        # 4. INSERT row 2 with :name named params (normalizer converts → ?)
        _exec_sql(
            conn,
            "INSERT INTO pydbc_teradata_compliance VALUES (:id, :name)",
            params=(2, "world"),
        )

        # 5. Commit DML (K027 — teradatasql may not autocommit on close)
        conn.commit()

        # 6. SELECT and assert 2 rows returned
        rs = _query_sql(
            conn,
            "SELECT id, name FROM pydbc_teradata_compliance",
        )
        rows = rs.get_rows()
        assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}: {rows!r}"

        # 7. DROP TABLE cleanup (plain drop — no IF EXISTS on Teradata)
        _exec_sql(conn, "DROP TABLE pydbc_teradata_compliance")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_drivers():
    """Clear DriverManager before each test and re-register TeradataDriver (K023)."""
    DriverManager.clear()
    DriverManager.register_driver(TeradataDriver())
    yield
    DriverManager.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_accepts_url():
    """TeradataDriver accepts pydbc:teradata: URLs and rejects other prefixes."""
    driver = TeradataDriver()
    assert driver.accepts_url("pydbc:teradata://localhost/mydb") is True
    assert driver.accepts_url("pydbc:teradata://localhost:1025/mydb") is True
    assert driver.accepts_url("pydbc:teradata://user:pw@host/db") is True
    assert driver.accepts_url("pydbc:oracle://localhost/FREEPDB1") is False
    assert driver.accepts_url("pydbc:sqlite://localhost/test") is False
    assert driver.accepts_url("pydbc:mysql://localhost/test") is False


def test_self_registers_on_import():
    """Module-level self-registration: after clearing and re-importing, a Teradata
    driver is registered and accepts_url returns True for pydbc:teradata: URLs."""
    # Clear the registry and evict the module so the import side-effect re-runs.
    DriverManager.clear()
    if "pydbc_teradata" in sys.modules:
        del sys.modules["pydbc_teradata"]

    import pydbc_teradata as _td  # noqa: F401 — triggers self-registration

    # At least one registered driver must accept a pydbc:teradata: URL.
    test_url = "pydbc:teradata://x"
    registered = DriverManager._drivers  # access internal list for assertion
    assert any(d.accepts_url(test_url) for d in registered), (
        f"No registered driver accepts {test_url!r}; registered: {registered!r}"
    )

    # Reload the canonical module reference so other tests see a clean state.
    importlib.reload(_td)


def test_compliance_suite(teradata_url):
    """Full compliance cycle: DDL, DML with ? params, DML with :name params, SELECT, DROP."""
    run_teradata_compliance_suite(TeradataDriver(), teradata_url)
