"""
tests/test_mysql_compliance.py — Compliance tests for pydbc-mysql.

Imports pydbc_mysql to trigger self-registration, then reuses the shared
compliance suite from packages/core/tests/test_compliance.py.

Requires a running MySQL instance provided by the session-scoped
``mysql_url`` fixture in conftest.py (managed via Docker).
"""

from __future__ import annotations

import os
import sys

# Allow importing test_compliance from the core tests package.
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "packages", "core", "tests"
    ),
)

import pytest

import pydbc_mysql  # noqa: F401 — triggers self-registration
from pydbc_mysql import MysqlDriver
from pydbc_core import DriverManager
from test_compliance import run_compliance_suite


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_drivers():
    """Clear DriverManager before each test and re-register MysqlDriver."""
    DriverManager.clear()
    DriverManager.register_driver(MysqlDriver())
    yield
    DriverManager.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_accepts_url():
    """MysqlDriver accepts pydbc:mysql: URLs and rejects other prefixes."""
    driver = MysqlDriver()
    assert driver.accepts_url("pydbc:mysql://localhost/test") is True
    assert driver.accepts_url("pydbc:pg://localhost/test") is False


def test_compliance_suite(mysql_url):
    """Full compliance cycle: DDL, DML with ? params, DML with :name params, SELECT, DROP."""
    run_compliance_suite(MysqlDriver(), mysql_url)


def test_self_registers_on_import(mysql_url):
    """Module-level registration is effective: after clear + re-register, connections work."""
    DriverManager.clear()
    DriverManager.register_driver(MysqlDriver())
    conn = DriverManager.get_connection(mysql_url)
    assert type(conn).__name__ == "GenericDbApiConnection"
    conn.close()
