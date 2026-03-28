# Getting Started with pydbc

A learning-oriented tutorial that walks you through the five key pydbc API areas using SQLite. By the end you will have connected to a database, executed parameterised SQL, navigated result sets, used the convenience data-source helpers, and managed a connection pool — all with runnable code you can adapt immediately.

> **Background:** If you want to understand *why* pydbc exists and how it relates to Python's DB-API 2.0 ecosystem, read [assessment.md](assessment.md) first.

---

## Introduction

pydbc is a thin, uniform abstraction layer over Python's many DB-API 2.0 drivers. It gives you:

- A **JDBC-inspired API** (`DriverManager`, `Connection`, `Statement`, `PreparedStatement`, `ResultSet`) that is consistent regardless of which database you talk to.
- **Transparent parameter-style translation** — write `?` or `:name` SQL once; pydbc rewrites it to whatever the underlying driver expects.
- **Higher-level helpers** — `NamedParameterDataSource`, `PooledDataSource`, and `SingleConnectionDataSource` — that handle connection lifecycle so you don't have to.

This tutorial uses **SQLite exclusively**. SQLite ships with Python and requires no server, so every example here runs without any infrastructure.

---

## Installation

Install the SQLite driver package. It pulls in `alt-python-pydbc-core` automatically:

```bash
uv add alt-python-pydbc-sqlite
# or
pip install alt-python-pydbc-sqlite
```

The core package (`alt-python-pydbc-core`) is a required dependency and will be installed alongside the driver.

> **Self-registration:** Importing `pydbc_sqlite` is enough to register the driver with `DriverManager`. You do not need to call any registration function yourself — the import is the side effect.

```python
import pydbc_sqlite  # noqa: F401 — registers the SQLite driver on import
from pydbc_core import DriverManager
```

---

## Connect and Execute SQL

Use `DriverManager.get_connection()` with a pydbc URL to open a connection. The URL scheme is `pydbc:<driver>:<native-dsn>`. For SQLite in-memory:

```python
import pydbc_sqlite  # noqa: F401
from pydbc_core import DriverManager

conn = DriverManager.get_connection("pydbc:sqlite::memory:")

# Create a table with an ad-hoc Statement.
stmt = conn.create_statement()
stmt.execute_update(
    "CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
)
```

`create_statement()` returns a `Statement` you can use for one-off SQL that takes no parameters.

### Parameterised Queries

Use `prepare_statement()` for SQL with parameters. pydbc uses `?` positional markers — it rewrites them to the driver's native paramstyle transparently (so the same SQL works across drivers):

```python
insert_sql = "INSERT INTO employees (id, name) VALUES (?, ?)"

pstmt = conn.prepare_statement(insert_sql)
pstmt.set_int(1, 1)
pstmt.set_string(2, "Alice")
pstmt.execute_update()

pstmt.clear_parameters()
pstmt.set_int(1, 2)
pstmt.set_string(2, "Bob")
pstmt.execute_update()

conn.commit()
```

The workflow is:
1. Call `prepare_statement(sql)` once.
2. Bind parameters with typed setters (`set_int`, `set_string`, `set_float`, `set_boolean`, …). Column indices are 1-based.
3. Call `execute_update()`.
4. Call `clear_parameters()` and repeat for the next row.
5. Call `conn.commit()` when you are done. In SQLite's legacy mode, mutations are rolled back if the connection closes without a commit.

**Output from the demo script:**

```
=== Step 1: Direct connection via DriverManager ===
  Table created and 2 rows inserted via DriverManager.get_connection()
```

---

## Reading Results

Query with `execute_query()` on a `Statement` or `PreparedStatement`. It returns a `ResultSet`:

```python
query_stmt = conn.create_statement()
rs = query_stmt.execute_query("SELECT id, name FROM employees ORDER BY id")

# Forward-only cursor navigation.
while rs.next():
    print(f"id={rs.get_int(1)}  name={rs.get_string(2)}")

# Bulk access — returns all rows as a list of dicts.
all_rows = rs.get_rows()
```

`ResultSet` supports two access patterns:

| Pattern | API | Returns |
|---|---|---|
| Cursor / forward | `rs.next()` then typed getters | one value at a time |
| Bulk | `rs.get_rows()` | `list[dict]` — column name → value |

Column indices in typed getters are 1-based (matching JDBC convention).

**Output from the demo script:**

```
=== Step 2: ResultSet navigation ===
  Cursor iteration:
    id=1  name=Alice
    id=2  name=Bob
  get_rows() returned 2 row(s): [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]
```

---

## NamedParameterDataSource

`NamedParameterDataSource` wraps a connection URL and gives you two methods — `update()` for mutations and `query()` for reads — that accept `:name` SQL and a `dict` of parameters. It handles opening, using, and closing the connection for you.

```python
import tempfile
from pydbc_core import NamedParameterDataSource

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
    print(rs.get_rows())

    rs_all = ds.query("SELECT id, name FROM contacts ORDER BY id", {})
    print(rs_all.get_rows())
```

> **Important — use a file-backed URL, not `:memory:`.**
>
> Each call to `ds.update()` or `ds.query()` opens a *fresh* connection. With `pydbc:sqlite::memory:`, each connection gets a completely separate in-memory database, so tables created in one call are invisible to the next. Use a file path (as shown above) so all calls share the same on-disk database.

**Output from the demo script:**

```
=== Step 3: NamedParameterDataSource ===
  Query for name='Carol': [{'id': 1, 'name': 'Carol'}]
  All contacts: [{'id': 1, 'name': 'Carol'}, {'id': 2, 'name': 'Dave'}]
```

---

## PooledDataSource

`PooledDataSource` maintains a pool of reusable connections. Configure minimum and maximum pool size at construction time:

```python
from pydbc_core import PooledDataSource

pool_ds = PooledDataSource("pydbc:sqlite::memory:", pool={"min": 1, "max": 3})
```

Acquire a connection with a context manager — it is automatically returned to the pool when the `with` block exits:

```python
with pool_ds.get_connection() as pool_conn:
    pool_stmt = pool_conn.create_statement()
    pool_stmt.execute_update(
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL)"
    )
    ins = pool_conn.prepare_statement("INSERT INTO tasks (id, title) VALUES (?, ?)")
    for task_id, title in [(1, "Write tests"), (2, "Review PR"), (3, "Deploy")]:
        ins.set_int(1, task_id)
        ins.set_string(2, title)
        ins.execute_update()
    pool_conn.commit()

    sel = pool_conn.create_statement()
    rs = sel.execute_query("SELECT id, title FROM tasks ORDER BY id")
    while rs.next():
        print(f"{rs.get_int(1)}: {rs.get_string(2)}")

# Connection is back in the pool here.
print(
    f"Pool stats — free: {pool_ds._pool.num_free}, "
    f"used: {pool_ds._pool.num_used}, "
    f"pending: {pool_ds._pool.num_pending}"
)

pool_ds.destroy()
```

Call `pool_ds.destroy()` when you are done with the pool (typically at application shutdown) to close all underlying connections.

**Output from the demo script:**

```
=== Step 4: PooledDataSource ===
  Tasks via pooled connection:
    1: Write tests
    2: Review PR
    3: Deploy
  Pool stats after release — free: 1, used: 0, pending: 0
  Pool destroyed.
```

---

## SingleConnectionDataSource

`SingleConnectionDataSource` holds one connection for its entire lifetime and returns the same connection on every `get_connection()` call. It is useful for small scripts and tests where you want datasource-style access without pooling overhead:

```python
from pydbc_core import SingleConnectionDataSource

sc_ds = SingleConnectionDataSource("pydbc:sqlite::memory:")

sc_conn = sc_ds.get_connection()
sc_stmt = sc_conn.create_statement()
sc_stmt.execute_update(
    "CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL)"
)
ins_note = sc_conn.prepare_statement("INSERT INTO notes (id, body) VALUES (?, ?)")
ins_note.set_int(1, 1)
ins_note.set_string(2, "pydbc makes database access Pythonic.")
ins_note.execute_update()
ins_note.clear_parameters()
ins_note.set_int(1, 2)
ins_note.set_string(2, "One abstraction, many databases.")
ins_note.execute_update()
sc_conn.commit()

# get_connection() returns the SAME connection — in-memory tables are still there.
sc_conn2 = sc_ds.get_connection()
sel_note = sc_conn2.create_statement()
rs_notes = sel_note.execute_query("SELECT id, body FROM notes ORDER BY id")
while rs_notes.next():
    print(f"[{rs_notes.get_int(1)}] {rs_notes.get_string(2)}")

sc_ds.destroy()
```

**Output from the demo script:**

```
=== Step 5: SingleConnectionDataSource ===
  Notes via SingleConnectionDataSource:
    [1] pydbc makes database access Pythonic.
    [2] One abstraction, many databases.
  SingleConnectionDataSource destroyed.
```

---

## Next Steps

- **API Reference** — detailed docs for every class and method are coming in the next documentation slice.
- **Driver Guide** — connecting to PostgreSQL, MySQL, and SQL Server, plus writing your own driver, is covered in the driver guide (coming soon).
- **Run the full demo yourself:**

  ```bash
  uv run python docs/examples/getting_started_demo.py
  ```
