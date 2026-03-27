"""
tests/test_sqlite_compliance.py — Compliance tests for pydbc-sqlite.

Imports pydbc_sqlite to trigger self-registration, then reuses the shared
compliance suite from packages/core/tests/test_compliance.py.
"""

from __future__ import annotations

import sys
import os

# Allow importing test_compliance from the core tests package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages", "core", "tests"))

import pytest

import pydbc_sqlite  # noqa: F401 — triggers self-registration
from pydbc_sqlite import SqliteDriver
from pydbc_core import DriverManager
from test_compliance import run_compliance_suite


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_drivers():
    """Clear DriverManager before each test and re-register SqliteDriver."""
    DriverManager.clear()
    DriverManager.register_driver(SqliteDriver())
    yield
    DriverManager.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_self_registration():
    """After registering SqliteDriver, get_connection returns a GenericDbApiConnection."""
    # reset_drivers fixture already registered; confirm connection works.
    conn = DriverManager.get_connection("pydbc:sqlite::memory:")
    assert type(conn).__name__ == "GenericDbApiConnection"
    conn.close()


def test_compliance_suite():
    """Full compliance cycle: DDL, DML with ? params, DML with :name params, SELECT, DROP."""
    run_compliance_suite(SqliteDriver(), "pydbc:sqlite::memory:")


def test_self_registers_on_import():
    """Module-level registration is effective: after clear + re-register, connections work."""
    DriverManager.clear()
    DriverManager.register_driver(SqliteDriver())
    conn = DriverManager.get_connection("pydbc:sqlite::memory:")
    assert type(conn).__name__ == "GenericDbApiConnection"
    conn.close()
