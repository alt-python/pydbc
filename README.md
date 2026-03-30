# pydbc

A uniform database access layer for Python — wraps DB-API 2.0 drivers behind a JDBC-style API with automatic paramstyle translation.

<!-- badges -->

---

## Why pydbc?

- **One API across all databases.** The same `DriverManager`, `Connection`, `Statement`, `PreparedStatement`, and `ResultSet` types work with SQLite, PostgreSQL, MySQL, SQL Server, and Oracle. Switch databases by changing the URL, not the code.
- **Automatic paramstyle translation.** Write `?` or `:name` SQL once. pydbc rewrites it to whatever the underlying driver expects (`%s`, `%(name)s`, `:1`, etc.) transparently.
- **DataSource helpers.** `SingleConnectionDataSource`, `PooledDataSource`, and `NamedParameterDataSource` handle connection lifecycle so you don't have to.
- **Not a new driver.** pydbc wraps the DB-API 2.0 drivers you already use (`sqlite3`, `psycopg2`, `PyMySQL`, `pymssql`, `oracledb`, `teradatasql`). It is an abstraction layer, not a replacement.

---

## Install

Install the driver package for the database you want to use. The core package (`alt-python-pydbc-core`) is pulled in automatically.

```bash
# SQLite (no extra infrastructure — ships with Python)
uv add alt-python-pydbc-sqlite

# PostgreSQL
uv add alt-python-pydbc-pg

# MySQL / MariaDB
uv add alt-python-pydbc-mysql

# SQL Server
uv add alt-python-pydbc-mssql

# Oracle
uv add alt-python-pydbc-oracle

# Teradata
uv add alt-python-pydbc-teradata
```

---

## Quick Example

```python
import pydbc_sqlite  # registers SqliteDriver with DriverManager
from pydbc_core import DriverManager

conn = DriverManager.get_connection("pydbc:sqlite::memory:")
stmt = conn.create_statement()
stmt.execute_update("CREATE TABLE t (n INTEGER)")
stmt.execute_update("INSERT INTO t VALUES (42)")
conn.commit()

rs = stmt.execute_query("SELECT n FROM t")
print(rs.rows)   # [(42,)]

conn.close()
```

Importing the driver package (`pydbc_sqlite`, `pydbc_pg`, etc.) is the only registration step required. The import itself is the side effect that registers the driver with `DriverManager`.

---

## Drivers

| Driver | URL format | Install package | Underlying library |
|--------|------------|-----------------|--------------------|
| SQLite | `pydbc:sqlite:<path-or-:memory:>` | `alt-python-pydbc-sqlite` | `sqlite3` (stdlib) |
| PostgreSQL | `pydbc:pg://user:pw@host:5432/dbname` | `alt-python-pydbc-pg` | `psycopg2` |
| MySQL / MariaDB | `pydbc:mysql://user:pw@host:3306/dbname` | `alt-python-pydbc-mysql` | `PyMySQL` |
| SQL Server | `pydbc:mssql://user:pw@host:1433/dbname` | `alt-python-pydbc-mssql` | `pymssql` |
| Oracle | `pydbc:oracle://user:pw@host:1521/service_name` | `alt-python-pydbc-oracle` | `oracledb` |
| Teradata | `pydbc:teradata://user:pw@host:1025/dbname` | `alt-python-pydbc-teradata` | `teradatasql` |

---

## DataSource Helpers

When you need more than a raw connection, pydbc ships three DataSource types:

**`NamedParameterDataSource`** — two-method convenience layer (`query` / `update`) that accepts `:name` SQL and a `dict`, managing connection open/close internally:

```python
from pydbc_core import NamedParameterDataSource

ds = NamedParameterDataSource("pydbc:sqlite:/tmp/myapp.db")
ds.update("INSERT INTO users (name) VALUES (:name)", {"name": "Alice"})
rs = ds.query("SELECT name FROM users WHERE name = :name", {"name": "Alice"})
while rs.next():
    print(rs.get_string("name"))
```

**`PooledDataSource`** — connection pool with configurable min/max size. Pooled connections are returned automatically when the `with` block exits:

```python
from pydbc_core import PooledDataSource

pool = PooledDataSource("pydbc:pg://user:pw@localhost/mydb", pool={"min": 2, "max": 10})
with pool.get_connection() as conn:
    stmt = conn.create_statement()
    rs = stmt.execute_query("SELECT count(*) FROM orders")
pool.destroy()
```

**`SingleConnectionDataSource`** — holds one connection for its entire lifetime; useful for tests and short scripts:

```python
from pydbc_core import SingleConnectionDataSource

ds = SingleConnectionDataSource("pydbc:sqlite::memory:")
conn = ds.get_connection()   # opens once
conn2 = ds.get_connection()  # same object
ds.destroy()
```

---

## Documentation

- [Getting Started](https://github.com/alt-python/pydbc/blob/main/docs/getting-started.md) — tutorial walkthrough covering all five API areas with runnable SQLite examples
- [API Reference](https://github.com/alt-python/pydbc/blob/main/docs/api-reference.md) — detailed docs for every class and method exported from `pydbc_core`

---

## Packages

| Package | PyPI name | What it provides |
|---------|-----------|-----------------|
| Core | `alt-python-pydbc-core` | Abstract base classes, `DriverManager`, `GenericDbApiDriver`, DataSource helpers, `ParamstyleNormalizer` |
| SQLite driver | `alt-python-pydbc-sqlite` | `SqliteDriver` — wraps `sqlite3`, `qmark` paramstyle |
| PostgreSQL driver | `alt-python-pydbc-pg` | `PgDriver` — wraps `psycopg2`, `pyformat` paramstyle |
| MySQL driver | `alt-python-pydbc-mysql` | `MysqlDriver` — wraps `PyMySQL`, `format` paramstyle |
| SQL Server driver | `alt-python-pydbc-mssql` | `MssqlDriver` — wraps `pymssql`, `pyformat` paramstyle |
| Oracle driver | `alt-python-pydbc-oracle` | `OracleDriver` — wraps `oracledb` (python-oracledb thin mode), `numeric` paramstyle |
| Teradata driver | `alt-python-pydbc-teradata` | `TeradataDriver` — wraps `teradatasql`, `qmark` paramstyle |

---

## License

MIT
