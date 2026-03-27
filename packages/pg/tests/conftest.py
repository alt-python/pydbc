"""
tests/conftest.py — Session-scoped postgres_url fixture for pydbc-pg tests.

Starts a PostgreSQL 16 Alpine container via Docker on port 15432 (avoids
conflict with any system PostgreSQL on 5432), waits for readiness, yields
the pydbc URL, then tears down the container.

The entire fixture body is wrapped in try/finally so teardown always runs
even if startup or the test session fails.

Skips gracefully if Docker is not available on the test host.
"""

from __future__ import annotations

import shutil
import subprocess
import time

import pytest

CONTAINER_NAME = "pydbc_pg_test"
HOST_PORT = 15432
POSTGRES_PASSWORD = "pydbc"
POSTGRES_USER = "postgres"
POSTGRES_DB = "postgres"
IMAGE = "postgres:16-alpine"
MAX_READY_POLLS = 30
POLL_INTERVAL = 1  # seconds


@pytest.fixture(scope="session")
def postgres_url():
    """Start a temporary PostgreSQL container and yield a pydbc connection URL.

    Skips the test session if Docker is not available.
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
                "-e", f"POSTGRES_PASSWORD={POSTGRES_PASSWORD}",
                "-p", f"{HOST_PORT}:5432",
                IMAGE,
            ],
            capture_output=True,
            check=True,
        )

        # Poll pg_isready until the server accepts connections.
        ready = False
        for _ in range(MAX_READY_POLLS):
            result = subprocess.run(
                [
                    "docker", "exec", CONTAINER_NAME,
                    "pg_isready", "-U", POSTGRES_USER,
                ],
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                ready = True
                break
            time.sleep(POLL_INTERVAL)

        if not ready:
            raise RuntimeError(
                f"PostgreSQL container {CONTAINER_NAME!r} did not become ready "
                f"after {MAX_READY_POLLS} polls."
            )

        yield (
            f"pydbc:pg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
            f"@localhost:{HOST_PORT}/{POSTGRES_DB}"
        )

    finally:
        subprocess.run(
            ["docker", "rm", "-f", CONTAINER_NAME],
            capture_output=True,
            check=False,
        )
