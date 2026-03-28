"""
pydbc getting-started demo
==========================

A self-contained script that exercises all five key pydbc API areas using
SQLite exclusively.  Run it with::

    uv run python docs/examples/getting_started_demo.py

It exits 0 and prints labelled output for each step.  Any file-backed SQLite
databases are created inside a temporary directory that is cleaned up on exit.
"""

from __future__ import annotations

import tempfile

# Importing pydbc_sqlite self-registers the SQLite driver with DriverManager.
import pydbc_sqlite  # noqa: F401
from pydbc_core import (
    DriverManager,
    NamedParameterDataSource,
    PooledDataSource,
    SingleConnectionDataSource,
)


# ---------------------------------------------------------------------------
# Step 1 — Direct connection via DriverManager
# ---------------------------------------------------------------------------

print("=== Step 1: Direct connection via DriverManager ===")

conn = DriverManager.get_connection("pydbc:sqlite::memory:")

# Create a table using an ad-hoc Statement.
stmt = conn.create_statement()
stmt.execute_update(
    "CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
)

# Insert two rows using a PreparedStatement (positional ? params).
insert_sql = "INSERT INTO employees (id, name) VALUES (?, ?)"

pstmt = conn.prepare_statement(insert_sql)
pstmt.set_int(1, 1)
pstmt.set_string(2, "Alice")
pstmt.execute_update()

pstmt.clear_parameters()
pstmt.set_int(1, 2)
pstmt.set_string(2, "Bob")
pstmt.execute_update()

# Commit before the connection is reused in Step 2 (K024).
conn.commit()
print("  Table created and 2 rows inserted via DriverManager.get_connection()")

# ---------------------------------------------------------------------------
# Step 2 — ResultSet navigation
# ---------------------------------------------------------------------------

print("=== Step 2: ResultSet navigation ===")

query_stmt = conn.create_statement()
rs = query_stmt.execute_query("SELECT id, name FROM employees ORDER BY id")

# Cursor-based forward navigation.
print("  Cursor iteration:")
while rs.next():
    print(f"    id={rs.get_int(1)}  name={rs.get_string(2)}")

# Bulk access (cursor position unaffected).
all_rows = rs.get_rows()
print(f"  get_rows() returned {len(all_rows)} row(s): {all_rows}")

conn.close()

# ---------------------------------------------------------------------------
# Step 3 — NamedParameterDataSource
# ---------------------------------------------------------------------------

print("=== Step 3: NamedParameterDataSource ===")

# File-backed SQLite is required here (K025) — each get_connection() call
# opens a fresh connection, and :memory: would give each call its own DB.
with tempfile.TemporaryDirectory() as tmp_dir:
    npds_url = f"pydbc:sqlite:{tmp_dir}/npds.db"
    ds = NamedParameterDataSource(npds_url)

    ds.update("CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT NOT NULL)", {})
    ds.update(
        "INSERT INTO contacts (id, name) VALUES (:id, :name)",
        {"id": 1, "name": "Carol"},
    )
    ds.update(
        "INSERT INTO contacts (id, name) VALUES (:id, :name)",
        {"id": 2, "name": "Dave"},
    )

    rs = ds.query("SELECT id, name FROM contacts WHERE name = :name", {"name": "Carol"})
    print(f"  Query for name='Carol': {rs.get_rows()}")

    rs_all = ds.query("SELECT id, name FROM contacts ORDER BY id", {})
    print(f"  All contacts: {rs_all.get_rows()}")

# tmp_dir and its contents are cleaned up here.

# ---------------------------------------------------------------------------
# Step 4 — PooledDataSource
# ---------------------------------------------------------------------------

print("=== Step 4: PooledDataSource ===")

# :memory: is fine here — we do all work inside a single connection context.
pool_url = "pydbc:sqlite::memory:"
pool_ds = PooledDataSource(pool_url, pool={"min": 1, "max": 3})

with pool_ds.get_connection() as pool_conn:
    pool_stmt = pool_conn.create_statement()
    pool_stmt.execute_update(
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL)"
    )
    ins = pool_conn.prepare_statement(
        "INSERT INTO tasks (id, title) VALUES (?, ?)"
    )
    for task_id, title in [(1, "Write tests"), (2, "Review PR"), (3, "Deploy")]:
        ins.set_int(1, task_id)
        ins.set_string(2, title)
        ins.execute_update()
    pool_conn.commit()

    sel = pool_conn.create_statement()
    rs = sel.execute_query("SELECT id, title FROM tasks ORDER BY id")
    print("  Tasks via pooled connection:")
    while rs.next():
        print(f"    {rs.get_int(1)}: {rs.get_string(2)}")

# The connection is returned to the pool when the `with` block exits.
print(
    f"  Pool stats after release — free: {pool_ds._pool.num_free}, "
    f"used: {pool_ds._pool.num_used}, "
    f"pending: {pool_ds._pool.num_pending}"
)

pool_ds.destroy()
print("  Pool destroyed.")

# ---------------------------------------------------------------------------
# Step 5 — SingleConnectionDataSource
# ---------------------------------------------------------------------------

print("=== Step 5: SingleConnectionDataSource ===")

# :memory: works perfectly here — every get_connection() call returns the
# same underlying connection, so in-memory state persists across calls.
sc_url = "pydbc:sqlite::memory:"
sc_ds = SingleConnectionDataSource(sc_url)

sc_conn = sc_ds.get_connection()
sc_stmt = sc_conn.create_statement()
sc_stmt.execute_update(
    "CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL)"
)

ins_note = sc_conn.prepare_statement(
    "INSERT INTO notes (id, body) VALUES (?, ?)"
)
ins_note.set_int(1, 1)
ins_note.set_string(2, "pydbc makes database access Pythonic.")
ins_note.execute_update()
ins_note.clear_parameters()
ins_note.set_int(1, 2)
ins_note.set_string(2, "One abstraction, many databases.")
ins_note.execute_update()
sc_conn.commit()

# get_connection() returns the same connection — notes are still visible.
sc_conn2 = sc_ds.get_connection()
sel_note = sc_conn2.create_statement()
rs_notes = sel_note.execute_query("SELECT id, body FROM notes ORDER BY id")
print("  Notes via SingleConnectionDataSource:")
while rs_notes.next():
    print(f"    [{rs_notes.get_int(1)}] {rs_notes.get_string(2)}")

sc_ds.destroy()
print("  SingleConnectionDataSource destroyed.")

print()
print("All steps complete.")
