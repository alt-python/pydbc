"""
tests/test_pg_compliance.py — Compliance tests for pydbc-pg.

Imports pydbc_pg to trigger self-registration, then reuses the shared
compliance suite from packages/core/tests/test_compliance.py.

Requires a running PostgreSQL instance provided by the session-scoped
``postgres_url`` fixture in conftest.py (managed via Docker).
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

import pydbc_pg  # noqa: F401 — triggers self-registration
from pydbc_pg import PgDriver
from pydbc_core import DriverManager
from test_compliance import run_compliance_suite


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_drivers():
    """Clear DriverManager before each test and re-register PgDriver."""
    DriverManager.clear()
    DriverManager.register_driver(PgDriver())
    yield
    DriverManager.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_accepts_url():
    """PgDriver accepts pydbc:pg: URLs and rejects other prefixes."""
    driver = PgDriver()
    assert driver.accepts_url("pydbc:pg://localhost/test") is True
    assert driver.accepts_url("pydbc:sqlite::memory:") is False


def test_compliance_suite(postgres_url):
    """Full compliance cycle: DDL, DML with ? params, DML with :name params, SELECT, DROP."""
    run_compliance_suite(PgDriver(), postgres_url)


def test_self_registers_on_import(postgres_url):
    """Module-level registration is effective: after clear + re-register, connections work."""
    DriverManager.clear()
    DriverManager.register_driver(PgDriver())
    conn = DriverManager.get_connection(postgres_url)
    assert type(conn).__name__ == "GenericDbApiConnection"
    conn.close()
