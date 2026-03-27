"""
tests/conftest.py — Session-scoped mssql_url fixture for pydbc-mssql tests.

Starts an Azure SQL Edge container via Docker on port 11433 (avoids conflict
with any system SQL Server on 1433), waits for readiness by polling
pymssql.connect() directly (the image has no sqlcmd), creates the test
database, yields the pydbc URL, then tears down the container.

The entire fixture body is wrapped in try/finally so teardown always runs
even if startup or the test session fails.

Skips gracefully if Docker is not available on the test host.

Azure SQL Edge takes ~20s to initialise; MAX_READY_POLLS=20 with a 2-second
interval gives a 40-second budget.
"""

from __future__ import annotations

import shutil
import subprocess
import time

import pymssql
import pytest

CONTAINER_NAME = "pydbc_mssql_test"
HOST_PORT = 11433
SA_PASSWORD = "Pydbc1234!"
IMAGE = "mcr.microsoft.com/azure-sql-edge:latest"
MAX_READY_POLLS = 20
POLL_INTERVAL = 2  # seconds


@pytest.fixture(scope="session")
def mssql_url():
    """Start a temporary Azure SQL Edge container and yield a pydbc URL.

    Skips the test session if Docker is not available.

    Readiness is determined by repeatedly attempting ``pymssql.connect()``
    against master — there is no ``sqlcmd`` in the azure-sql-edge image.

    After the server is ready, the ``pydbc_test`` database is created via a
    connection to ``master`` with ``autocommit=True``.
    """
    if shutil.which("docker") is None:
        pytest.skip("docker not available", allow_module_level=True)

    try:
        # Remove any stale container from a previous interrupted run.
        subprocess.run(
            ["docker", "rm", "-f", CONTAINER_NAME],
            capture_output=True,
            check=False,
        )

        # Start a fresh container.
        subprocess.run(
            [
                "docker", "run", "-d",
                "--name", CONTAINER_NAME,
                "-e", "ACCEPT_EULA=Y",
                "-e", f"MSSQL_SA_PASSWORD={SA_PASSWORD}",
                "-p", f"{HOST_PORT}:1433",
                IMAGE,
            ],
            capture_output=True,
            check=True,
        )

        # Poll pymssql.connect() until the server accepts connections.
        # azure-sql-edge has no sqlcmd, so we connect directly from Python.
        ready = False
        for _ in range(MAX_READY_POLLS):
            try:
                conn = pymssql.connect(
                    server="localhost",
                    port=str(HOST_PORT),
                    user="sa",
                    password=SA_PASSWORD,
                    database="master",
                )
                conn.close()
                ready = True
                break
            except Exception:  # noqa: BLE001
                time.sleep(POLL_INTERVAL)

        if not ready:
            raise RuntimeError(
                f"MSSQL container {CONTAINER_NAME!r} did not become ready "
                f"after {MAX_READY_POLLS} polls ({MAX_READY_POLLS * POLL_INTERVAL}s)."
            )

        # Create the test database.
        conn = pymssql.connect(
            server="localhost",
            port=str(HOST_PORT),
            user="sa",
            password=SA_PASSWORD,
            database="master",
            autocommit=True,
        )
        try:
            cursor = conn.cursor()
            cursor.execute("CREATE DATABASE pydbc_test")
        finally:
            conn.close()

        yield (
            f"pydbc:mssql://sa:{SA_PASSWORD}@localhost:{HOST_PORT}/pydbc_test"
        )

    finally:
        subprocess.run(
            ["docker", "rm", "-f", CONTAINER_NAME],
            capture_output=True,
            check=False,
        )
