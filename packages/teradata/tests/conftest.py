"""
tests/conftest.py — Session-scoped teradata_url fixture for pydbc-teradata tests.

Reads connection details from environment variables.  If TERADATA_HOST is not
set the entire test session is skipped at collection time — no Docker, no
subprocess, env-var only (D011).

Environment variables:
    TERADATA_HOST      — required; hostname or IP of the Teradata server
    TERADATA_USER      — optional; default "dbc"
    TERADATA_PASSWORD  — optional; default "dbc"
    TERADATA_PORT      — optional; default "1025"
    TERADATA_DATABASE  — optional; omitted from URL when absent

The fixture is session-scoped so the URL is computed once per test run.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def teradata_url():
    """Yield a pydbc:teradata:// URL built from environment variables.

    Calls ``pytest.skip(allow_module_level=True)`` if ``TERADATA_HOST`` is
    not set, so that the compliance test is cleanly skipped rather than
    erroring with a missing-env-var message.
    """
    host = os.environ.get("TERADATA_HOST")
    if not host:
        pytest.skip("TERADATA_HOST not set", allow_module_level=True)

    user = os.environ.get("TERADATA_USER", "dbc")
    password = os.environ.get("TERADATA_PASSWORD", "dbc")
    port = os.environ.get("TERADATA_PORT", "1025")
    database = os.environ.get("TERADATA_DATABASE", "")

    db_part = f"/{database}" if database else ""
    yield f"pydbc:teradata://{user}:{password}@{host}:{port}{db_part}"
