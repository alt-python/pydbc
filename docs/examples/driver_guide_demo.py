"""
pydbc driver guide — worked example
=====================================

Demonstrates how to write a custom pydbc driver by implementing ``DemoDriver``,
a minimal wrapper around stdlib ``sqlite3``.  Run it with::

    uv run python docs/examples/driver_guide_demo.py

It exits 0 and prints a confirmation line.  No external packages or running
database server are required — everything uses SQLite in ``:memory:`` mode.
"""

from __future__ import annotations

import sqlite3

from pydbc_core import DriverManager
from pydbc_core.generic_db_api_driver import GenericDbApiDriver

# ---------------------------------------------------------------------------
# Step 1 — Define the driver
# ---------------------------------------------------------------------------

class DemoDriver(GenericDbApiDriver):
    """A minimal pydbc driver that wraps stdlib sqlite3.

    ``URL_PREFIX`` is the URL scheme this driver owns.
    ``DriverManager`` calls ``accepts_url()`` (inherited from
    ``GenericDbApiDriver``) which returns ``True`` for any URL that starts
    with this prefix.

    No ``connect()`` override is needed here: the default implementation
    strips ``URL_PREFIX`` from the URL and passes the remainder directly to
    ``sqlite3.connect()``.  For ``pydbc:demo::memory:`` that remainder is
    ``:memory:``, which sqlite3 understands natively.
    """

    URL_PREFIX = "pydbc:demo:"

    def __init__(self) -> None:
        super().__init__(sqlite3, self.URL_PREFIX)


# ---------------------------------------------------------------------------
# Step 2 — Register the driver (one line; import is enough in production)
# ---------------------------------------------------------------------------

DriverManager.register_driver(DemoDriver())

# ---------------------------------------------------------------------------
# Step 3 — Open a connection and exercise the driver
# ---------------------------------------------------------------------------

# The remainder after stripping "pydbc:demo:" is ":memory:" — a valid sqlite3 DSN.
conn = DriverManager.get_connection("pydbc:demo::memory:")

# DDL via ad-hoc Statement
stmt = conn.create_statement()
stmt.execute_update(
    "CREATE TABLE greetings (id INTEGER PRIMARY KEY, message TEXT NOT NULL)"
)

# DML via PreparedStatement (positional ? params — sqlite3 uses qmark style)
pstmt = conn.prepare_statement(
    "INSERT INTO greetings (id, message) VALUES (?, ?)"
)
pstmt.set_int(1, 1)
pstmt.set_string(2, "hello pydbc")
pstmt.execute_update()
conn.commit()

# SELECT via ResultSet
rs = conn.create_statement().execute_query(
    "SELECT message FROM greetings WHERE id = 1"
)
rs.next()
message = rs.get_string(1)

print(f"DemoDriver works: {message}")

# ---------------------------------------------------------------------------
# Step 4 — Clean up
# ---------------------------------------------------------------------------

conn.close()
DriverManager.clear()
