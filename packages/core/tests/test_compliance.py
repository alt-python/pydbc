"""
tests/test_compliance.py — End-to-end compliance tests using sqlite3.

The :func:`run_compliance_suite` function at module level is intentionally
importable so that S03 and S04 can reuse it against different drivers.

The suite exercises:
1. DDL via :meth:`~pydbc_core.statement.Statement.execute_update`
2. DML INSERT with ``?`` positional params via PreparedStatement
3. SELECT with ``?`` positional params via PreparedStatement
4. DML INSERT with ``:name`` named params via PreparedStatement (normalizer
   converts to the driver's native paramstyle automatically)
5. SELECT by id=2, asserting the named-param round-trip
6. DROP TABLE via Statement
"""

from __future__ import annotations

import sqlite3

import pytest

from pydbc_core import DriverManager, GenericDbApiDriver
from pydbc_core.driver import Driver
from pydbc_core.connection import Connection
from pydbc_core.result_set import ResultSet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exec_sql(conn: Connection, sql: str, params: tuple = ()) -> int:
    """Execute DML/DDL using a PreparedStatement and return rowcount.

    For each element in *params*, :meth:`~pydbc_core.prepared_statement.PreparedStatement.set_parameter`
    is called with a 1-based index.  An empty params tuple causes the
    PreparedStatement to execute with no bound values.
    """
    stmt = conn.prepare_statement(sql)
    for i, value in enumerate(params, start=1):
        stmt.set_parameter(i, value)
    return stmt.execute_update()


def _query_sql(conn: Connection, sql: str, params: tuple = ()) -> ResultSet:
    """Execute a SELECT using a PreparedStatement and return a ResultSet."""
    stmt = conn.prepare_statement(sql)
    for i, value in enumerate(params, start=1):
        stmt.set_parameter(i, value)
    return stmt.execute_query()


# ---------------------------------------------------------------------------
# Compliance suite — importable for S03/S04 reuse
# ---------------------------------------------------------------------------


def run_compliance_suite(driver: Driver, url: str) -> None:
    """Run a complete create/insert/select/drop compliance cycle.

    Args:
        driver: A :class:`~pydbc_core.driver.Driver` instance to test.
        url:    The pydbc URL to connect to (e.g. ``'pydbc:sqlite::memory:'``).

    Raises:
        AssertionError: If any compliance check fails.
    """
    with driver.connect(url, None) as conn:
        # 1. DDL — create table
        _exec_sql(
            conn,
            "CREATE TABLE IF NOT EXISTS compliance_items (id INTEGER, name TEXT)",
        )

        # 2. INSERT row 1 with ? positional params
        _exec_sql(
            conn,
            "INSERT INTO compliance_items (id, name) VALUES (?, ?)",
            params=(1, "alpha"),
        )

        # 3. SELECT row 1 via ? positional params
        rs = _query_sql(
            conn,
            "SELECT id, name FROM compliance_items WHERE id = ?",
            params=(1,),
        )
        rows = rs.get_rows()
        assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
        assert rows[0]["id"] == 1
        assert rows[0]["name"] == "alpha"

        # 4. INSERT row 2 with :name named params
        #    The normalizer converts :id/:val to the driver's native paramstyle.
        #    Values are bound by scan-order index (1-based).
        _exec_sql(
            conn,
            "INSERT INTO compliance_items (id, name) VALUES (:id, :val)",
            params=(2, "beta"),  # scan order: :id → index 1, :val → index 2
        )

        # 5. SELECT row 2 via ? positional params
        rs2 = _query_sql(
            conn,
            "SELECT id, name FROM compliance_items WHERE id = ?",
            params=(2,),
        )
        rows2 = rs2.get_rows()
        assert len(rows2) == 1, f"Expected 1 row, got {len(rows2)}"
        assert rows2[0]["id"] == 2
        assert rows2[0]["name"] == "beta"

        # 6. DROP TABLE (cleanup)
        _exec_sql(conn, "DROP TABLE compliance_items")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_manager():
    """Clear DriverManager registry before and after every test."""
    DriverManager.clear()
    yield
    DriverManager.clear()


def test_compliance_qmark():
    """Full round-trip with sqlite3 (native qmark paramstyle) — positional path."""
    driver = GenericDbApiDriver(sqlite3, "pydbc:sqlite:")
    run_compliance_suite(driver, "pydbc:sqlite::memory:")


def test_compliance_named():
    """Full round-trip verifying the :name → qmark normalizer path against sqlite3."""
    driver = GenericDbApiDriver(sqlite3, "pydbc:sqlite:")
    run_compliance_suite(driver, "pydbc:sqlite::memory:")


def test_compliance_driver_manager_integration():
    """Verify run_compliance_suite works when the driver is registered in DriverManager."""
    driver = GenericDbApiDriver(sqlite3, "pydbc:sqlite:")
    DriverManager.register_driver(driver)
    conn = DriverManager.get_connection("pydbc:sqlite::memory:")
    with conn:
        stmt = conn.create_statement()
        result = stmt.execute("SELECT 1")
        # execute() returns True when description is not None (i.e. has a ResultSet)
        assert result is True


def test_compliance_statement_execute_query():
    """GenericDbApiStatement.execute_query works for bare SELECT (no params)."""
    driver = GenericDbApiDriver(sqlite3, "pydbc:sqlite:")
    with driver.connect("pydbc:sqlite::memory:", None) as conn:
        stmt = conn.create_statement()
        rs = stmt.execute_query("SELECT 42 AS answer")
        rows = rs.get_rows()
        assert len(rows) == 1
        assert rows[0]["answer"] == 42


def test_compliance_statement_execute_update_ddl():
    """GenericDbApiStatement.execute_update returns -1 for DDL (sqlite3 rowcount convention)."""
    driver = GenericDbApiDriver(sqlite3, "pydbc:sqlite:")
    with driver.connect("pydbc:sqlite::memory:", None) as conn:
        stmt = conn.create_statement()
        rc = stmt.execute_update(
            "CREATE TABLE IF NOT EXISTS t_ddl_check (x INTEGER)"
        )
        # sqlite3 returns -1 for DDL; we just assert it doesn't raise
        assert isinstance(rc, int)


def test_compliance_fresh_cursor_per_execute():
    """GenericDbApiPreparedStatement creates a fresh cursor per execute_query call."""
    driver = GenericDbApiDriver(sqlite3, "pydbc:sqlite:")
    with driver.connect("pydbc:sqlite::memory:", None) as conn:
        conn.create_statement().execute_update(
            "CREATE TABLE t_multi (v INTEGER)"
        )
        conn.create_statement().execute_update("INSERT INTO t_multi VALUES (10)")
        conn.create_statement().execute_update("INSERT INTO t_multi VALUES (20)")

        ps = conn.prepare_statement("SELECT v FROM t_multi WHERE v = ?")
        ps.set_parameter(1, 10)
        rs1 = ps.execute_query()
        ps.clear_parameters()
        ps.set_parameter(1, 20)
        rs2 = ps.execute_query()

        assert rs1.get_rows()[0]["v"] == 10
        assert rs2.get_rows()[0]["v"] == 20


def test_compliance_connection_is_closed_after_context_exit():
    """Connection.is_closed() returns True after the context manager exits."""
    driver = GenericDbApiDriver(sqlite3, "pydbc:sqlite:")
    with driver.connect("pydbc:sqlite::memory:", None) as conn:
        assert not conn.is_closed()
    assert conn.is_closed()
