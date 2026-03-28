# Writing Custom pydbc Drivers

A task-oriented guide for authors who need to add support for a new database
(or a new flavour of an existing one) by implementing a pydbc driver.

> **Prerequisites:** Read [getting-started.md](getting-started.md) first to
> understand how `DriverManager`, `Connection`, `Statement`, and `ResultSet`
> fit together from a user's perspective.  The full API contract is in
> [api-reference.md](api-reference.md#genericdbapidriver).

---

## Introduction

A **pydbc driver** is a small class that knows two things:

1. Which pydbc URLs it owns (e.g. `pydbc:sqlite:`, `pydbc:pg:`).
2. How to open a raw DB-API 2.0 connection for a given URL.

Everything else — statement execution, parameter-style translation, result-set
wrapping, prepared-statement state, context-manager support — is handled by
`pydbc_core`.  In most cases a driver is fewer than fifteen lines of code.

**When do you need a custom driver?**  When you want to use a DB-API 2.0
module that pydbc doesn't already ship a driver for.  The five built-in
drivers cover SQLite, PostgreSQL (psycopg2), MySQL (PyMySQL), SQL Server
(pymssql), and Oracle (oracledb).  For any other database — CockroachDB, DuckDB, Snowflake,
etc. — write a driver following this guide.

---

## The `GenericDbApiDriver` Subclass

`GenericDbApiDriver` is the base class for every built-in driver and the
recommended base for custom ones.  It wraps any PEP 249-compliant module and
handles all execution plumbing automatically.

```python
from pydbc_core.generic_db_api_driver import GenericDbApiDriver

class MyDriver(GenericDbApiDriver):
    URL_PREFIX = "pydbc:mydb:"

    def __init__(self) -> None:
        super().__init__(mydb_module, self.URL_PREFIX)
```

Three things to know:

| Item | Description |
|------|-------------|
| `URL_PREFIX` | The URL scheme this driver owns.  `DriverManager` checks `accepts_url()` (inherited; returns `url.startswith(URL_PREFIX)`) in registration order. |
| `super().__init__(module, url_prefix)` | Pass the DB-API 2.0 module object and the same prefix.  The base class stores the module and its `paramstyle` for use at execution time. |
| No `connect()` override | If the underlying module accepts a plain DSN after the prefix is stripped, the inherited `connect()` is sufficient.  See the next section. |

---

## URL Translation Patterns

`GenericDbApiDriver.connect()` strips `URL_PREFIX` from the URL and passes
the remainder directly to `module.connect()`.  Whether that works depends on
what the underlying module expects.

### Pattern 1 — Passthrough (no override needed)

Use this when the module accepts the raw DSN string that follows your prefix.

**Example:** SQLite.  `pydbc:sqlite::memory:` → strips `pydbc:sqlite:` →
passes `:memory:` to `sqlite3.connect()`.  sqlite3 accepts any path or the
special `:memory:` token, so no override is required.

```python
import sqlite3
from pydbc_core.generic_db_api_driver import GenericDbApiDriver

class SqliteDriver(GenericDbApiDriver):
    URL_PREFIX = "pydbc:sqlite:"

    def __init__(self) -> None:
        super().__init__(sqlite3, self.URL_PREFIX)
```

### Pattern 2 — URL scheme rewrite

Use this when the module accepts a URL string but needs a different scheme
prefix.

**Example:** psycopg2 expects `postgresql://...` but pydbc uses `pydbc:pg:`.
Override `connect()` to prepend `postgresql:` before the `//host...` portion.

```python
import psycopg2
from pydbc_core.generic_db_api_driver import GenericDbApiConnection, GenericDbApiDriver

class PgDriver(GenericDbApiDriver):
    URL_PREFIX = "pydbc:pg:"

    def __init__(self) -> None:
        super().__init__(psycopg2, self.URL_PREFIX)

    def connect(self, url: str, properties: dict | None = None) -> GenericDbApiConnection:
        # "pydbc:pg://user:pw@host/db" → "postgresql://user:pw@host/db"
        native_url = "postgresql:" + url[len(self.URL_PREFIX):]
        native_conn = psycopg2.connect(native_url)
        return GenericDbApiConnection(native_conn, psycopg2, psycopg2.paramstyle)
```

> **Import note:** `GenericDbApiConnection` must be imported from
> `pydbc_core.generic_db_api_driver`, not from `pydbc_core` directly — it is
> an implementation detail, not a public export.

### Pattern 3 — URL parse to kwargs

Use this when the module does not accept URL strings at all and requires
explicit keyword arguments.

**Example:** PyMySQL's `connect()` only accepts kwargs (`host`, `port`, `user`,
`password`, `database`).  Parse the URL with `urllib.parse.urlparse`, then
pass each component as a keyword argument.

```python
from urllib.parse import urlparse
import pymysql
from pydbc_core.generic_db_api_driver import GenericDbApiConnection, GenericDbApiDriver

class MysqlDriver(GenericDbApiDriver):
    URL_PREFIX = "pydbc:mysql:"

    def __init__(self) -> None:
        super().__init__(pymysql, self.URL_PREFIX)

    def connect(self, url: str, properties: dict | None = None) -> GenericDbApiConnection:
        parsed = urlparse(url[len(self.URL_PREFIX):])
        native_conn = pymysql.connect(
            host=parsed.hostname,
            port=parsed.port or 3306,   # port must be int
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip("/"),
        )
        return GenericDbApiConnection(native_conn, pymysql, pymysql.paramstyle)
```

> **pymssql note:** pymssql uses `server=` (not `host=`) and requires `port`
> as a *string*, not an int.  Always consult your module's `connect()` signature
> before choosing kwargs names and types.

> **oracledb note:** `oracledb.connect()` uses `user=`, `password=`, and
> `dsn='host:port/service_name'`.  Pass `'numeric'` explicitly as the
> paramstyle — pydbc forces numeric (`:1`, `:2`) for Oracle rather than
> oracledb's native named style.  The pydbc URL format is
> `pydbc:oracle://user:pw@host:1521/service_name`.

---

## Self-Registration Pattern

Register your driver at module level so that a bare `import mydriver` is
sufficient to make it available via `DriverManager`:

```python
from pydbc_core import DriverManager

DriverManager.register_driver(MyDriver())
```

Users then write:

```python
import mydriver                         # registers the driver as a side effect
from pydbc_core import DriverManager

conn = DriverManager.get_connection("pydbc:mydb://host/dbname")
```

`DriverManager` tries each registered driver's `accepts_url()` in
registration order.  The first driver that returns `True` handles the
connection.  If your URL prefix is unique (as it should be), registration
order does not matter.

---

## Worked Example

This self-contained script defines `DemoDriver`, registers it, and runs a
round-trip DDL → INSERT → SELECT against an in-memory SQLite database.

```python
import sqlite3

from pydbc_core import DriverManager
from pydbc_core.generic_db_api_driver import GenericDbApiDriver


class DemoDriver(GenericDbApiDriver):
    """Minimal driver wrapping sqlite3 under the pydbc:demo: prefix."""

    URL_PREFIX = "pydbc:demo:"

    def __init__(self) -> None:
        super().__init__(sqlite3, self.URL_PREFIX)


DriverManager.register_driver(DemoDriver())

conn = DriverManager.get_connection("pydbc:demo::memory:")

stmt = conn.create_statement()
stmt.execute_update(
    "CREATE TABLE greetings (id INTEGER PRIMARY KEY, message TEXT NOT NULL)"
)

pstmt = conn.prepare_statement(
    "INSERT INTO greetings (id, message) VALUES (?, ?)"
)
pstmt.set_int(1, 1)
pstmt.set_string(2, "hello pydbc")
pstmt.execute_update()
conn.commit()

rs = conn.create_statement().execute_query(
    "SELECT message FROM greetings WHERE id = 1"
)
rs.next()
print(f"DemoDriver works: {rs.get_string(1)}")

conn.close()
DriverManager.clear()
```

The runnable version lives at [`docs/examples/driver_guide_demo.py`](examples/driver_guide_demo.py).
Run it with:

```bash
uv run python docs/examples/driver_guide_demo.py
# DemoDriver works: hello pydbc
```

---

## Testing Your Driver

### Isolation

`DriverManager` is a process-global registry.  Tests that register a driver
must clean up in teardown to avoid leaking state into other tests:

```python
import pytest
from pydbc_core import DriverManager

@pytest.fixture(autouse=True)
def _register_and_clear():
    DriverManager.register_driver(MyDriver())
    yield
    DriverManager.clear()
```

### Reusing the Compliance Suite

`packages/core/tests/test_compliance.py` exports `run_compliance_suite(conn_url, params)`
which runs a standard battery of DDL + DML + SELECT + DROP tests against any
registered driver.  Import and call it from your own test module to verify
DB-API 2.0 compliance without duplicating test logic:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "packages", "core", "tests"))
from test_compliance import run_compliance_suite

def test_my_driver_compliance(my_db_url):
    run_compliance_suite(my_db_url, {})
```

> **Note:** `CREATE TABLE IF NOT EXISTS` is used inside `run_compliance_suite`.
> If your target database does not support this syntax (e.g. SQL Server), write
> a local compliance runner using plain `CREATE TABLE` instead.

---

## Cross-references

- [api-reference.md — GenericDbApiDriver](api-reference.md#genericdbapidriver) — full method-level API
- [api-reference.md — DriverManager](api-reference.md#drivermanager) — `register_driver`, `get_connection`, `clear`
- [getting-started.md](getting-started.md) — user-facing tutorial; shows what your driver's callers will write
