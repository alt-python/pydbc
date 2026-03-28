"""
tests/test_oracle_compliance.py — Compliance tests for pydbc-oracle.

Imports pydbc_oracle to trigger self-registration, then runs an
Oracle-compatible compliance suite.

Note:
  - Oracle does NOT support ``CREATE TABLE IF NOT EXISTS`` — plain
    ``CREATE TABLE`` is used.
  - Oracle DDL (CREATE TABLE / DROP TABLE) is auto-committed; DML
    (INSERT) is NOT — ``conn.commit()`` is called after INSERTs.
  - oracledb defaults to ``paramstyle='named'``; OracleDriver overrides
    this to ``'numeric'`` so ``:1``, ``:2`` placeholders are used.

Requires a running Oracle Free instance provided by the session-scoped
``oracle_url`` fixture in conftest.py (managed via Docker).
"""

from __future__ import annotations

import pytest

import pydbc_oracle  # noqa: F401 — triggers self-registration
from pydbc_oracle import OracleDriver
from pydbc_core import DriverManager
from pydbc_core.connection import Connection


# ---------------------------------------------------------------------------
# Local compliance suite (Oracle-compatible DDL — no IF NOT EXISTS)
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


def run_oracle_compliance_suite(driver: OracleDriver, url: str) -> None:
    """Run a complete create/insert/select/drop compliance cycle against Oracle.

    Uses plain ``CREATE TABLE`` (no ``IF NOT EXISTS``) and a table name
    distinct from the core/mssql suite names to avoid cross-test collisions.

    Oracle DDL (CREATE TABLE / DROP TABLE) implicitly commits; DML (INSERT)
    does not.  An explicit ``conn.commit()`` is called after the INSERTs so
    the rows are visible to the subsequent SELECT within the same connection
    (and not silently rolled back on ``conn.close()``).

    Args:
        driver: An :class:`OracleDriver` instance to test.
        url:    The pydbc URL to connect to (e.g. ``'pydbc:oracle://...'``).

    Raises:
        AssertionError: If any compliance check fails.
    """
    with driver.connect(url, None) as conn:
        # 1. DDL — create table (plain CREATE TABLE; auto-committed by Oracle)
        _exec_sql(
            conn,
            "CREATE TABLE pydbc_oracle_compliance (id NUMBER, name VARCHAR2(100))",
        )

        # 2. INSERT row 1 with ? positional params
        _exec_sql(
            conn,
            "INSERT INTO pydbc_oracle_compliance VALUES (?, ?)",
            params=(1, "hello"),
        )

        # 3. INSERT row 2 with :name named params
        #    The numeric normalizer converts both ? and :name to :1/:2.
        _exec_sql(
            conn,
            "INSERT INTO pydbc_oracle_compliance VALUES (:id, :name)",
            params=(2, "world"),
        )

        # 4. Commit DML — oracledb does NOT auto-commit on close (K024 analog).
        conn.commit()

        # 5. SELECT and assert 2 rows returned
        rs = _query_sql(conn, "SELECT id, name FROM pydbc_oracle_compliance")
        rows = rs.get_rows()
        assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}: {rows!r}"

        # 6. DROP TABLE (cleanup — Oracle auto-commits DDL)
        _exec_sql(conn, "DROP TABLE pydbc_oracle_compliance")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_drivers():
    """Clear DriverManager before each test and re-register OracleDriver."""
    DriverManager.clear()
    DriverManager.register_driver(OracleDriver())
    yield
    DriverManager.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_accepts_url():
    """OracleDriver accepts pydbc:oracle: URLs and rejects other prefixes."""
    driver = OracleDriver()
    assert driver.accepts_url("pydbc:oracle://localhost/FREEPDB1") is True
    assert driver.accepts_url("pydbc:oracle://localhost:1521/FREEPDB1") is True
    assert driver.accepts_url("pydbc:pg://localhost/test") is False
    assert driver.accepts_url("pydbc:sqlite://localhost/test") is False
    assert driver.accepts_url("pydbc:mssql://localhost/test") is False


def test_compliance_suite(oracle_url):
    """Full compliance cycle: DDL, DML with ? params, DML with :name params, SELECT, DROP."""
    run_oracle_compliance_suite(OracleDriver(), oracle_url)


def test_self_registers_on_import(oracle_url):
    """Module-level registration is effective: after clear + re-register, connections work."""
    DriverManager.clear()
    DriverManager.register_driver(OracleDriver())
    conn = DriverManager.get_connection(oracle_url)
    assert type(conn).__name__ == "GenericDbApiConnection"
    conn.close()
