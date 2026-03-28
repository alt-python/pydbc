"""
tests/conftest.py — Session-scoped oracle_url fixture for pydbc-oracle tests.

Starts a gvenzl/oracle-free:slim-faststart container via Docker on port 11521
(avoids conflict with any system Oracle on 1521), waits for readiness by
polling oracledb.connect() directly, and yields the pydbc URL.  FREEPDB1 is
pre-provisioned in gvenzl/oracle-free so no additional database creation is
needed after the server is ready.

The entire fixture body is wrapped in try/finally so teardown always runs
even if startup or the test session fails.

Skips gracefully if Docker is not available on the test host.

Oracle Free starts slower than MSSQL; MAX_READY_POLLS=45 with a 2-second
interval gives a 90-second readiness budget.
"""

from __future__ import annotations

import shutil
import subprocess
import time

import oracledb
import pytest

CONTAINER_NAME = "pydbc_oracle_test"
HOST_PORT = 11521
ORACLE_PASSWORD = "Pydbc1234!"
IMAGE = "gvenzl/oracle-free:slim-faststart"
MAX_READY_POLLS = 45
POLL_INTERVAL = 2  # seconds


@pytest.fixture(scope="session")
def oracle_url():
    """Start a temporary Oracle Free container and yield a pydbc URL.

    Skips the test session if Docker is not available.

    Readiness is determined by repeatedly attempting ``oracledb.connect()``
    against FREEPDB1 — the pluggable database is pre-provisioned in the
    gvenzl/oracle-free image.

    After the server is ready, the URL is yielded directly — no additional
    database creation is needed (FREEPDB1 already exists).
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

        # Start a fresh Oracle Free container.
        subprocess.run(
            [
                "docker", "run", "-d",
                "--name", CONTAINER_NAME,
                "-e", f"ORACLE_PASSWORD={ORACLE_PASSWORD}",
                "-p", f"{HOST_PORT}:1521",
                IMAGE,
            ],
            capture_output=True,
            check=True,
        )

        # Poll oracledb.connect() until FREEPDB1 accepts connections.
        ready = False
        for _ in range(MAX_READY_POLLS):
            try:
                conn = oracledb.connect(
                    user="system",
                    password=ORACLE_PASSWORD,
                    dsn=f"localhost:{HOST_PORT}/FREEPDB1",
                )
                conn.close()
                ready = True
                break
            except Exception:  # noqa: BLE001
                time.sleep(POLL_INTERVAL)

        if not ready:
            raise RuntimeError(
                f"Oracle container {CONTAINER_NAME!r} did not become ready "
                f"after {MAX_READY_POLLS} polls "
                f"({MAX_READY_POLLS * POLL_INTERVAL}s)."
            )

        yield (
            f"pydbc:oracle://system:{ORACLE_PASSWORD}@localhost:{HOST_PORT}/FREEPDB1"
        )

    finally:
        subprocess.run(
            ["docker", "rm", "-f", CONTAINER_NAME],
            capture_output=True,
            check=False,
        )
