"""
tests/test_mssql_compliance.py — Compliance tests for pydbc-mssql.

Imports pydbc_mssql to trigger self-registration, then runs an MSSQL-specific
compliance suite.

Note: MSSQL does NOT support ``CREATE TABLE IF NOT EXISTS`` — the local
``run_mssql_compliance_suite()`` uses plain ``CREATE TABLE`` and
``DROP TABLE``.

Requires a running Azure SQL Edge instance provided by the session-scoped
``mssql_url`` fixture in conftest.py (managed via Docker).
"""

from __future__ import annotations

import pytest

import pydbc_mssql  # noqa: F401 — triggers self-registration
from pydbc_mssql import MssqlDriver
from pydbc_core import DriverManager
from pydbc_core.connection import Connection


# ---------------------------------------------------------------------------
# Local compliance suite (MSSQL-compatible DDL — no IF NOT EXISTS)
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


def run_mssql_compliance_suite(driver: MssqlDriver, url: str) -> None:
    """Run a complete create/insert/select/drop compliance cycle against MSSQL.

    Uses plain ``CREATE TABLE`` (no ``IF NOT EXISTS``) and a table name
    distinct from the core suite to avoid cross-test collisions.

    Args:
        driver: A :class:`MssqlDriver` instance to test.
        url:    The pydbc URL to connect to (e.g. ``'pydbc:mssql://...'``).

    Raises:
        AssertionError: If any compliance check fails.
    """
    with driver.connect(url, None) as conn:
        # 1. DDL — create table (plain CREATE TABLE; MSSQL has no IF NOT EXISTS)
        _exec_sql(
            conn,
            "CREATE TABLE pydbc_compliance_test (id INT, name VARCHAR(100))",
        )

        # 2. INSERT row 1 with ? positional params
        _exec_sql(
            conn,
            "INSERT INTO pydbc_compliance_test VALUES (?, ?)",
            params=(1, "hello"),
        )

        # 3. INSERT row 2 with :name named params
        #    The normalizer converts :id/:name to pymssql's %s / %(name)s style.
        #    Values are bound by scan-order index (1-based).
        _exec_sql(
            conn,
            "INSERT INTO pydbc_compliance_test VALUES (:id, :name)",
            params=(2, "world"),
        )

        # 4. SELECT and assert 2 rows returned
        rs = _query_sql(conn, "SELECT id, name FROM pydbc_compliance_test")
        rows = rs.get_rows()
        assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}: {rows!r}"

        # 5. DROP TABLE (cleanup)
        _exec_sql(conn, "DROP TABLE pydbc_compliance_test")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_drivers():
    """Clear DriverManager before each test and re-register MssqlDriver."""
    DriverManager.clear()
    DriverManager.register_driver(MssqlDriver())
    yield
    DriverManager.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_accepts_url():
    """MssqlDriver accepts pydbc:mssql: URLs and rejects other prefixes."""
    driver = MssqlDriver()
    assert driver.accepts_url("pydbc:mssql://localhost/test") is True
    assert driver.accepts_url("pydbc:pg://localhost/test") is False
    assert driver.accepts_url("pydbc:sqlite://localhost/test") is False


def test_compliance_suite(mssql_url):
    """Full compliance cycle: DDL, DML with ? params, DML with :name params, SELECT, DROP."""
    run_mssql_compliance_suite(MssqlDriver(), mssql_url)


def test_self_registers_on_import(mssql_url):
    """Module-level registration is effective: after clear + re-register, connections work."""
    DriverManager.clear()
    DriverManager.register_driver(MssqlDriver())
    conn = DriverManager.get_connection(mssql_url)
    assert type(conn).__name__ == "GenericDbApiConnection"
    conn.close()
