"""
tests/conftest.py — Session-scoped mysql_url fixture for pydbc-mysql tests.

Starts a MySQL 8.0 container via Docker on port 13306 (avoids conflict with
any system MySQL on 3306), waits for readiness, yields the pydbc URL, then
tears down the container.

The entire fixture body is wrapped in try/finally so teardown always runs
even if startup or the test session fails.

Skips gracefully if Docker is not available on the test host.

MySQL starts slower than Postgres, so MAX_READY_POLLS is 30 with a 2-second
interval (60 seconds total budget).
"""

from __future__ import annotations

import shutil
import subprocess
import time

import pytest

CONTAINER_NAME = "pydbc_mysql_test"
HOST_PORT = 13306
MYSQL_ROOT_PASSWORD = "pydbc"
MYSQL_DATABASE = "pydbc_test"
IMAGE = "mysql:8.0"
MAX_READY_POLLS = 30
POLL_INTERVAL = 2  # seconds — MySQL initialises slowly


@pytest.fixture(scope="session")
def mysql_url():
    """Start a temporary MySQL container and yield a pydbc connection URL.

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
                "-e", f"MYSQL_ROOT_PASSWORD={MYSQL_ROOT_PASSWORD}",
                "-e", f"MYSQL_DATABASE={MYSQL_DATABASE}",
                "-p", f"{HOST_PORT}:3306",
                IMAGE,
            ],
            capture_output=True,
            check=True,
        )

        # Poll mysqladmin ping until the server accepts connections.
        ready = False
        for _ in range(MAX_READY_POLLS):
            result = subprocess.run(
                [
                    "docker", "exec", CONTAINER_NAME,
                    "mysqladmin", "ping",
                    "-uroot", f"-p{MYSQL_ROOT_PASSWORD}",
                    "--silent",
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
                f"MySQL container {CONTAINER_NAME!r} did not become ready "
                f"after {MAX_READY_POLLS} polls."
            )

        yield (
            f"pydbc:mysql://root:{MYSQL_ROOT_PASSWORD}"
            f"@localhost:{HOST_PORT}/{MYSQL_DATABASE}"
        )

    finally:
        subprocess.run(
            ["docker", "rm", "-f", CONTAINER_NAME],
            capture_output=True,
            check=False,
        )
