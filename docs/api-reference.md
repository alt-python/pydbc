# pydbc Core API Reference

This document covers every name exported from `pydbc_core.__all__` (14 total).
For a narrative tutorial with runnable examples, see [getting-started.md](getting-started.md).

---

## Contents

**Abstract base classes**

- [Driver](#driver) — declares the two-method contract every driver must implement
- [Connection](#connection) — transaction control and statement factory
- [Statement](#statement) — ad-hoc SQL execution
- [PreparedStatement](#preparedstatement) — parameterised SQL execution
- [ResultSet](#resultset) — forward-only cursor and bulk row access
- [DataSource](#datasource) — URL-based connection factory
- [ConnectionPool](#connectionpool) — bounded connection pool contract

**Concrete implementations**

- [DriverManager](#drivermanager) — process-global driver registry
- [GenericDbApiDriver](#genericdbapidriver) — PEP 249 adapter
- [SingleConnectionDataSource](#singleconnectiondatasource) — single shared connection
- [SimpleConnectionPool](#simpleconnectionpool) — thread-safe bounded pool
- [PooledDataSource](#pooleddatasource) — DataSource backed by a pool
- [NamedParameterDataSource](#namedparameterdatasource) — named-param convenience layer

**Utilities**

- [ParamstyleNormalizer](#paramstylenormalizer) — translates canonical SQL params to any DB-API paramstyle

---

## Driver

**Module:** `pydbc_core.driver`

Abstract base class that every database driver must implement. A driver is a
stateless factory: it inspects a URL and, if it accepts it, opens a connection.

```python
from pydbc_core import Driver
```

### Constructor

`Driver` is an ABC — it is not instantiated directly. Implement it in a subclass.

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `accepts_url` | `(url: str) -> bool` | `bool` | Return `True` if this driver handles the given pydbc URL. |
| `connect` | `(url: str, properties: dict \| None = None) -> Connection` | `Connection` | Open and return a `Connection` for the given URL. |

#### `accepts_url(url)`

Return `True` if this driver handles the given pydbc URL. `DriverManager` calls
this method in registration order to dispatch `get_connection()` calls.

**Args:**

- `url` — A pydbc URL string (e.g. `"pydbc:sqlite::memory:"`).

#### `connect(url, properties=None)`

Open and return a `Connection` for the given URL. Called by `DriverManager.get_connection()`
after `accepts_url()` returns `True`.

**Args:**

- `url` — A pydbc URL string.
- `properties` — Optional dict of driver-specific connection properties (e.g. `"user"`, `"password"`).

---

## Connection

**Module:** `pydbc_core.connection`

Abstract base class for a database connection. Provides transaction control
and factory methods for `Statement` and `PreparedStatement`. Implements the
context manager protocol — `close()` is called automatically when used with
`with`.

See [getting-started.md](getting-started.md#connect-and-execute-sql) for a
tutorial walkthrough.

```python
from pydbc_core import Connection
```

### Constructor

`Connection` is an ABC — it is not instantiated directly. Obtain connections
through `DriverManager.get_connection()` or a `DataSource`.

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `create_statement` | `() -> Statement` | `Statement` | Create and return an ad-hoc `Statement`. |
| `prepare_statement` | `(sql: str) -> PreparedStatement` | `PreparedStatement` | Create a `PreparedStatement` for the given SQL. |
| `set_auto_commit` | `(auto_commit: bool) -> None` | `None` | Enable or disable auto-commit mode. |
| `commit` | `() -> None` | `None` | Commit the current transaction. |
| `rollback` | `() -> None` | `None` | Roll back the current transaction. |
| `close` | `() -> None` | `None` | Close the connection and release resources. |
| `is_closed` | `() -> bool` | `bool` | Return `True` if the connection has been closed. |
| `__enter__` | `() -> Connection` | `Connection` | Return `self` for use as a context manager. |
| `__exit__` | `(exc_type, exc_val, exc_tb) -> None` | `None` | Call `close()` on block exit. |

#### `create_statement()`

Return a new `Statement` suitable for one-off SQL that takes no parameters.

#### `prepare_statement(sql)`

Return a new `PreparedStatement` for the given SQL template. The SQL may use
canonical `?` or `:name` placeholders — see `ParamstyleNormalizer` for how
they are translated to the underlying driver's paramstyle.

**Args:**

- `sql` — SQL string with `?` or `:name` parameter placeholders.

#### `commit()`

Commit the current transaction. In SQLite's legacy (non-autocommit) mode,
uncommitted changes are silently rolled back when the connection is closed —
always call `commit()` after mutations.

#### `rollback()`

Roll back the current transaction, discarding all uncommitted changes.

#### `set_auto_commit(auto_commit)`

Enable or disable auto-commit mode on the underlying native connection.

**Args:**

- `auto_commit` — `True` to enable auto-commit; `False` to disable.

---

## Statement

**Module:** `pydbc_core.statement`

Abstract base class for ad-hoc SQL execution. Obtain a `Statement` from
`Connection.create_statement()`. Use `PreparedStatement` instead when the SQL
has parameters.

Implements the context manager protocol — `close()` is called automatically
when used with `with`.

```python
from pydbc_core import Statement
```

### Constructor

`Statement` is an ABC — obtain instances via `Connection.create_statement()`.

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `execute_query` | `(sql: str) -> ResultSet` | `ResultSet` | Execute a SELECT and return a `ResultSet`. |
| `execute_update` | `(sql: str) -> int` | `int` | Execute a DML/DDL statement and return affected row count. |
| `execute` | `(sql: str) -> bool` | `bool` | Execute SQL; returns `True` if the result is a `ResultSet`. |
| `close` | `() -> None` | `None` | Close the statement and release resources. |
| `is_closed` | `() -> bool` | `bool` | Return `True` if the statement has been closed. |
| `__enter__` | `() -> Statement` | `Statement` | Return `self`. |
| `__exit__` | `(exc_type, exc_val, exc_tb) -> None` | `None` | Call `close()`. |

#### `execute_query(sql)`

Execute the SQL and return a fully materialised `ResultSet`. Use for `SELECT`
statements.

**Args:**

- `sql` — A SQL string with no parameters (use `PreparedStatement` for parameterised queries).

#### `execute_update(sql)`

Execute a DDL or DML statement (`CREATE TABLE`, `INSERT`, `UPDATE`, `DELETE`).

**Args:**

- `sql` — A SQL string with no parameters.

**Returns:** Number of rows affected (`cursor.rowcount`).

#### `execute(sql)`

General-purpose execution. Returns `True` if the statement produced a result
set (e.g. a `SELECT`), `False` otherwise.

---

## PreparedStatement

**Module:** `pydbc_core.prepared_statement`

Abstract base class for parameterised SQL execution. Extends `Statement` with
parameter-binding methods. Parameter indices are **1-based** (matching JDBC
convention).

Obtain a `PreparedStatement` via `Connection.prepare_statement(sql)`.

See [getting-started.md](getting-started.md#parameterised-queries) for a
complete worked example.

```python
from pydbc_core import PreparedStatement
```

### Constructor

`PreparedStatement` is an ABC — obtain instances via `Connection.prepare_statement(sql)`.

### Methods

**Parameter binding** (1-based indices):

| Method | Signature | Description |
|--------|-----------|-------------|
| `set_parameter` | `(index: int, value: Any) -> None` | Bind any value to the 1-based parameter index. |
| `set_string` | `(index: int, value: str) -> None` | Bind a string value. |
| `set_int` | `(index: int, value: int) -> None` | Bind an integer value. |
| `set_float` | `(index: int, value: float) -> None` | Bind a float value. |
| `set_null` | `(index: int) -> None` | Bind `NULL` / `None`. |
| `clear_parameters` | `() -> None` | Remove all bound parameters. |

**Execution** (no SQL argument — SQL is fixed at prepare time):

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `execute_query` | `() -> ResultSet` | `ResultSet` | Execute the prepared query and return a `ResultSet`. |
| `execute_update` | `() -> int` | `int` | Execute the prepared update and return the affected row count. |

**Inherited lifecycle** (from `Statement`):

| Method | Signature | Description |
|--------|-----------|-------------|
| `close` | `() -> None` | Close and release resources. |
| `is_closed` | `() -> bool` | Return `True` if closed. |

**Typical workflow:**

```python
pstmt = conn.prepare_statement("INSERT INTO t (id, name) VALUES (?, ?)")
pstmt.set_int(1, 1)
pstmt.set_string(2, "Alice")
pstmt.execute_update()

pstmt.clear_parameters()
pstmt.set_int(1, 2)
pstmt.set_string(2, "Bob")
pstmt.execute_update()

conn.commit()
```

---

## ResultSet

**Module:** `pydbc_core.result_set`

Cursor-based result set returned by query execution. Rows are stored as dicts
keyed by column name. Navigation is forward-only.

Column indices in all typed getters are **1-based**.

Implements the context manager protocol — `close()` is called automatically
when used with `with`.

See [getting-started.md](getting-started.md#reading-results) for the two
access patterns shown side by side.

```python
from pydbc_core import ResultSet
```

### Constructor

```python
ResultSet(rows: list[dict], column_names: list[str])
```

In normal usage you do not construct `ResultSet` directly — it is returned by
`Statement.execute_query()` and `PreparedStatement.execute_query()`.

| Arg | Type | Description |
|-----|------|-------------|
| `rows` | `list[dict]` | Row data as dicts keyed by column name. |
| `column_names` | `list[str]` | Ordered column name list. |

### Navigation

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `next` | `() -> bool` | `bool` | Advance the cursor. Returns `True` if within bounds, `False` past the last row. |

### Value accessors (1-based column index or column name)

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_object` | `(col: int \| str)` | `Any` | Return the raw value for the column. |
| `get_string` | `(col: int \| str)` | `str \| None` | Return the value cast to `str` (`None` if `NULL`). |
| `get_int` | `(col: int \| str)` | `int \| None` | Return the value cast to `int` (`None` if `NULL`). |
| `get_float` | `(col: int \| str)` | `float \| None` | Return the value cast to `float` (`None` if `NULL`). |
| `get_row` | `() -> dict` | `dict` | Return the current row as a dict. |

### Bulk / metadata

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_rows` | `() -> list[dict]` | `list[dict]` | Return all rows (does not affect cursor position). |
| `get_column_names` | `() -> list[str]` | `list[str]` | Return the ordered list of column names. |
| `get_row_count` | `() -> int` | `int` | Return the total number of rows. |

### Lifecycle

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `close` | `() -> None` | `None` | Close the `ResultSet` and release row data. |
| `is_closed` | `() -> bool` | `bool` | Return `True` if `close()` has been called. |

All access methods raise `RuntimeError` when called on a closed `ResultSet`.
`get_object` / `get_string` / `get_int` / `get_float` raise `RuntimeError`
if `next()` has not been called or the cursor is past the last row.

---

## DataSource

**Module:** `pydbc_core.data_source`

URL-based connection factory that resolves connections through `DriverManager`.
The base class for `SingleConnectionDataSource`, `PooledDataSource`, and
`NamedParameterDataSource`.

```python
from pydbc_core import DataSource
```

### Constructor

```python
DataSource(
    url: str,
    username: str | None = None,
    password: str | None = None,
    **properties,
)
```

| Arg | Type | Description |
|-----|------|-------------|
| `url` | `str` | A pydbc URL (e.g. `"pydbc:sqlite::memory:"`). |
| `username` | `str \| None` | Optional username, merged into properties as `"user"`. |
| `password` | `str \| None` | Optional password, merged into properties as `"password"`. |
| `**properties` | `Any` | Additional driver-specific connection properties. |

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_connection` | `() -> Connection` | `Connection` | Return a new connection from the driver that accepts `url`. |
| `get_url` | `() -> str` | `str` | Return the pydbc URL this data source connects to. |

#### `get_connection()`

Open and return a new `Connection`. Merges `username` and `password` into the
properties dict before dispatching to `DriverManager.get_connection()`.

---

## ConnectionPool

**Module:** `pydbc_core.connection_pool`

Abstract base class that defines the contract every connection pool must
implement. `SimpleConnectionPool` is the bundled implementation.

```python
from pydbc_core import ConnectionPool
```

### Constructor

`ConnectionPool` is an ABC — it is not instantiated directly.

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `acquire` | `() -> Connection` | `Connection` | Acquire a connection, blocking if none are available. |
| `release` | `(conn: Connection) -> None` | `None` | Return a connection to the pool. |
| `destroy` | `() -> None` | `None` | Close all managed connections and release resources. |

### Observability properties

| Property | Type | Description |
|----------|------|-------------|
| `num_used` | `int` | Connections currently checked out by callers. |
| `num_free` | `int` | Idle connections available for immediate use. |
| `num_pending` | `int` | Callers currently blocked waiting for a connection. |

---

## DriverManager

**Module:** `pydbc_core.driver_manager`

Process-global class-level registry mapping pydbc URLs to registered `Driver`
instances. All methods are class methods — there is no `DriverManager()` instance.

Driver packages self-register by calling `DriverManager.register_driver(MyDriver())`
at module import time. Importing the driver package is sufficient to register it —
no explicit registration call is needed in application code.

See [getting-started.md](getting-started.md#connect-and-execute-sql) for an
end-to-end example using `get_connection()`.

```python
from pydbc_core import DriverManager
```

### Class methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `register_driver` | `(driver: Driver) -> None` | `None` | Append a driver to the global registry. |
| `deregister_driver` | `(driver: Driver) -> None` | `None` | Remove a driver from the registry (no-op if absent). |
| `get_connection` | `(url: str, properties: dict \| None = None) -> Connection` | `Connection` | Open a connection by dispatching to the first driver whose `accepts_url()` returns `True`. |
| `get_drivers` | `() -> list[Driver]` | `list[Driver]` | Return a shallow copy of the registered driver list. |
| `clear` | `() -> None` | `None` | Remove all registered drivers. Use in test teardown. |

#### `register_driver(driver)`

Append *driver* to the end of the global driver list. Drivers are tried in
registration order by `get_connection()`.

**Args:**

- `driver` — An instance of a `Driver` subclass.

#### `get_connection(url, properties=None)`

Iterate the registered drivers in order; call `accepts_url(url)` on each.
Return the `Connection` from the first driver that accepts the URL.

**Args:**

- `url` — A pydbc URL (e.g. `"pydbc:sqlite::memory:"`).
- `properties` — Optional dict of driver-specific properties (credentials, timeouts, etc.).

**Raises:** `ValueError` if no registered driver accepts the URL.

#### `clear()`

Remove all registered drivers. Call this in test teardown fixtures to prevent
driver state from leaking between tests.

---

## GenericDbApiDriver

**Module:** `pydbc_core.generic_db_api_driver`

A `Driver` implementation that wraps any PEP 249-compliant module (e.g.
`sqlite3`, `psycopg2`, `PyMySQL`) in the full pydbc abstraction hierarchy.
This is the foundation of all bundled pydbc driver packages.

> **Internal detail:** `GenericDbApiDriver` also creates `GenericDbApiConnection`,
> `GenericDbApiStatement`, and `GenericDbApiPreparedStatement` instances internally.
> `GenericDbApiConnection` is not in `pydbc_core.__all__` and is considered an
> implementation detail. Driver packages that need to override connection behaviour
> can import it from `pydbc_core.generic_db_api_driver` directly.

```python
from pydbc_core import GenericDbApiDriver
import sqlite3

driver = GenericDbApiDriver(sqlite3, "pydbc:sqlite:")
DriverManager.register_driver(driver)
```

### Constructor

```python
GenericDbApiDriver(module, url_prefix: str)
```

| Arg | Type | Description |
|-----|------|-------------|
| `module` | PEP 249 module | A DB-API 2.0 compliant database module (e.g. `sqlite3`, `psycopg2`). |
| `url_prefix` | `str` | The URL prefix this driver handles (e.g. `"pydbc:sqlite:"`). |

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `accepts_url` | `(url: str) -> bool` | `bool` | Return `True` if `url` starts with `url_prefix`. |
| `connect` | `(url: str, properties: dict \| None = None) -> Connection` | `Connection` | Strip the URL prefix and call `module.connect()` with the remainder. |

#### `connect(url, properties=None)`

Strips `url_prefix` from `url` to obtain the native DSN (e.g. strips
`"pydbc:sqlite:"` from `"pydbc:sqlite::memory:"` to get `":memory:"`), then
calls `module.connect(native_dsn)` and wraps the result in a
`GenericDbApiConnection`.

> **Driver subclasses** that require a different URL translation (e.g. psycopg2
> needs the scheme `postgresql://` prepended, PyMySQL requires keyword arguments)
> override `connect()` to reconstruct the appropriate native DSN before calling
> the module.

---

## SingleConnectionDataSource

**Module:** `pydbc_core.single_connection_data_source`

A `DataSource` that vends the **same** connection on every `get_connection()`
call. The connection is opened lazily on the first call and reused thereafter.
Useful for sharing an in-memory SQLite database across an entire test suite
without losing state between statements.

See [getting-started.md](getting-started.md#singleconnectiondatasource) for a
worked example.

```python
from pydbc_core import SingleConnectionDataSource

ds = SingleConnectionDataSource("pydbc:sqlite::memory:")
conn = ds.get_connection()   # opens once
conn2 = ds.get_connection()  # same object
ds.destroy()
```

### Constructor

```python
SingleConnectionDataSource(
    url: str,
    username: str | None = None,
    password: str | None = None,
    **properties,
)
```

Inherits all arguments from `DataSource`.

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_connection` | `() -> Connection` | `Connection` | Return the cached connection, opening it if necessary. |
| `close` | `() -> None` | `None` | **No-op.** Does not close the underlying connection. |
| `destroy` | `() -> None` | `None` | Actually close and discard the cached connection. |

#### `get_connection()`

Return the cached connection. If it has never been opened, or if it was
previously closed, a new connection is opened and cached.

#### `close()`

Intentionally does nothing. Callers that normally call `conn.close()` will not
accidentally discard the shared connection. Call `destroy()` for cleanup.

#### `destroy()`

Close the cached connection and set the internal reference to `None`. Call
this in test teardown or application shutdown.

---

## SimpleConnectionPool

**Module:** `pydbc_core.simple_connection_pool`

Thread-safe bounded connection pool backed by `queue.Queue`. Implements
`ConnectionPool`. Connections are pre-warmed to `min` at construction and
grown on demand up to `max`.

See [getting-started.md](getting-started.md#pooleddatasource) for `PooledDataSource`
usage, which creates a `SimpleConnectionPool` internally.

```python
from pydbc_core import SimpleConnectionPool

pool = SimpleConnectionPool(
    factory={
        "create": lambda: DriverManager.get_connection("pydbc:sqlite::memory:"),
        "destroy": lambda c: c.close(),
    },
    options={"min": 1, "max": 5},
)
conn = pool.acquire()
try:
    ...
finally:
    pool.release(conn)
pool.destroy()
```

### Constructor

```python
SimpleConnectionPool(
    factory: dict[str, Callable],
    options: dict[str, Any] | None = None,
)
```

**`factory` dict keys:**

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `create` | `Callable[[], Connection]` | Yes | Opens and returns a new connection. |
| `destroy` | `Callable[[Connection], None]` | Yes | Closes a connection. |
| `validate` | `Callable[[Connection], bool]` | No | Returns `False` if the connection is stale; triggers replacement on `release()`. |

**`options` dict keys:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `min` | `int` | `0` | Connections to open at pool startup. |
| `max` | `int` | `10` | Maximum total connections (idle + in-use). |
| `acquire_timeout` | `float` | `30.0` | Seconds to wait before raising `queue.Empty` when the pool is exhausted. |

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `acquire` | `() -> Connection` | `Connection` | Acquire a connection, blocking up to `acquire_timeout` if the pool is exhausted. |
| `release` | `(conn: Connection) -> None` | `None` | Return a connection to the pool, optionally validating it first. |
| `destroy` | `() -> None` | `None` | Drain and close all idle connections. |

### Observability properties

| Property | Type | Description |
|----------|------|-------------|
| `num_used` | `int` | Connections currently checked out. |
| `num_free` | `int` | Idle connections available for immediate acquisition. |
| `num_pending` | `int` | Callers currently blocked in `acquire()`. |

#### `acquire()`

Try to get an idle connection from the queue immediately. If none are available
and `total < max`, create a new one. Otherwise block on the queue for up to
`acquire_timeout` seconds.

**Raises:** `queue.Empty` if no connection becomes available within the timeout.

#### `release(conn)`

Return *conn* to the pool. If a `validate` callable is registered and returns
`False`, the stale connection is destroyed and a fresh one is created before
being enqueued.

#### `destroy()`

Drain the pool queue and close every idle connection. Connections currently
checked out are **not** affected — callers are responsible for releasing them
before calling `destroy()`.

---

## PooledDataSource

**Module:** `pydbc_core.pooled_data_source`

A `DataSource` backed by a connection pool. Connections returned by
`get_connection()` are proxied objects that return themselves to the pool
when `close()` is called (or when a `with` block exits).

See [getting-started.md](getting-started.md#pooleddatasource) for a full example.

```python
from pydbc_core import PooledDataSource

ds = PooledDataSource("pydbc:sqlite::memory:", pool={"min": 1, "max": 5})
with ds.get_connection() as conn:
    stmt = conn.create_statement()
    ...
# connection returned to pool here
ds.destroy()
```

### Constructor

```python
PooledDataSource(
    url: str,
    pool: dict[str, Any] | None = None,
    connection_pool: ConnectionPool | None = None,
    **kwargs,
)
```

| Arg | Type | Description |
|-----|------|-------------|
| `url` | `str` | A pydbc URL. |
| `pool` | `dict \| None` | Pool options (`min`, `max`, `acquire_timeout`) forwarded to `SimpleConnectionPool`. Ignored if `connection_pool` is provided. |
| `connection_pool` | `ConnectionPool \| None` | An existing pool to use instead of creating a new `SimpleConnectionPool`. |
| `**kwargs` | `Any` | Additional arguments forwarded to `DataSource` (e.g. `username`, `password`). |

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_connection` | `() -> Connection` | `Connection` (proxy) | Acquire a pooled connection proxy. Returns it to the pool on `close()` or context exit. |
| `destroy` | `() -> None` | `None` | Drain and close all idle connections in the pool. |

#### `get_connection()`

Acquire a connection from the pool. Returns a proxy that delegates all
`Connection` methods to the underlying connection and returns it to the pool
when `close()` is called. Use as a context manager to guarantee return-to-pool
even on exceptions.

#### `destroy()`

Call `pool.destroy()` to drain and close all idle connections. Call this at
application shutdown. Connections still in use are not closed by `destroy()`.

---

## NamedParameterDataSource

**Module:** `pydbc_core.named_parameter_data_source`

A `DataSource` subclass with two convenience methods — `query()` and `update()`
— that accept `:paramName` SQL templates and a `dict` of values. Connection
lifecycle (open, use, close) is managed internally.

See [getting-started.md](getting-started.md#namedparameterdatasource) for a
complete example including the file-backed URL recommendation.

```python
from pydbc_core import NamedParameterDataSource

ds = NamedParameterDataSource("pydbc:sqlite:/tmp/myapp.db")
ds.update("INSERT INTO users (name) VALUES (:name)", {"name": "Alice"})
rs = ds.query("SELECT name FROM users WHERE name = :name", {"name": "Alice"})
while rs.next():
    print(rs.get_string("name"))
```

> **File-backed URL:** Each `query()` / `update()` call opens a fresh connection.
> With `pydbc:sqlite::memory:`, every connection gets a separate in-memory
> database — tables created in one call are invisible to the next. Use a
> file-backed URL (e.g. `pydbc:sqlite:/path/to/db.sqlite`) so all calls share
> the same on-disk database.

### Constructor

Inherits from `DataSource`:

```python
NamedParameterDataSource(
    url: str,
    username: str | None = None,
    password: str | None = None,
    **properties,
)
```

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `query` | `(sql: str, params: dict) -> ResultSet` | `ResultSet` | Execute a SELECT with named params; return a fully materialised `ResultSet`. |
| `update` | `(sql: str, params: dict) -> int` | `int` | Execute an INSERT/UPDATE/DELETE with named params; commit and return row count. |
| `get_connection` | `() -> Connection` | `Connection` | (Inherited) Return a new connection each call. |
| `get_url` | `() -> str` | `str` | (Inherited) Return the configured pydbc URL. |

#### `query(sql, params)`

Normalise `:name` placeholders to `?` via `ParamstyleNormalizer`, execute on
a fresh `PreparedStatement`, close the connection, and return the materialised
`ResultSet`. The returned `ResultSet` is fully in-memory and safe to use after
the connection closes.

**Args:**

- `sql` — SQL string with `:name` placeholders.
- `params` — `dict` mapping placeholder names to values. Pass `{}` for parameter-free SQL.

#### `update(sql, params)`

Like `query()`, but executes a mutation. Commits the transaction before
closing the connection so changes are visible to subsequent calls.

**Args:**

- `sql` — SQL string with `:name` placeholders.
- `params` — `dict` mapping placeholder names to values. Pass `{}` for parameter-free SQL.

**Returns:** Number of rows affected.

---

## ParamstyleNormalizer

**Module:** `pydbc_core.paramstyle_normalizer`

Utility class with a single static method that translates canonical SQL
parameter syntax to any of the five DB-API 2.0 paramstyles.

pydbc uses `?` for positional SQL and `:name` for named SQL as its canonical
input conventions. Drivers declare their native paramstyle via the PEP 249
`paramstyle` module attribute; `ParamstyleNormalizer.normalize()` bridges the
gap.

PostgreSQL cast syntax (`created_at::date`) is never mistaken for a `:name`
parameter — the normalizer uses a negative-lookbehind regex to skip `::`.

```python
from pydbc_core import ParamstyleNormalizer

sql, params = ParamstyleNormalizer.normalize(
    "SELECT * FROM users WHERE id = :id",
    {"id": 42},
    "qmark",
)
# sql   → "SELECT * FROM users WHERE id = ?"
# params → (42,)
```

### Constructor

`ParamstyleNormalizer` is a utility class — it is never instantiated. All
behaviour is accessed via the static `normalize()` method.

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `normalize` | `(sql, params, target_paramstyle) -> tuple[str, tuple \| dict]` | `(str, tuple \| dict)` | Translate *sql* and *params* to the target paramstyle. |

#### `normalize(sql, params, target_paramstyle)`

Translate *sql* and *params* to the paramstyle expected by the underlying driver.

**Args:**

| Arg | Type | Description |
|-----|------|-------------|
| `sql` | `str` | SQL with canonical `?` or `:name` placeholders. |
| `params` | `tuple \| list \| dict \| None` | Values as a tuple/list (positional) or dict (named). `None` is treated as an empty tuple. |
| `target_paramstyle` | `str` | One of `"qmark"`, `"format"`, `"pyformat"`, `"named"`, `"numeric"`. |

**Returns:** A `(normalised_sql, normalised_params)` tuple ready to pass
directly to `cursor.execute()`.

**Raises:** `ValueError` if `target_paramstyle` is not one of the five
recognised values, or if positional params are supplied with `target_paramstyle="named"`
(which has no canonical translation).

**Supported paramstyles:**

| `target_paramstyle` | Placeholder | Params type | Used by |
|---------------------|-------------|-------------|---------|
| `qmark` | `?` | `tuple` | sqlite3 |
| `format` | `%s` | `tuple` | MySQL (positional) |
| `pyformat` | `%(name)s` | `dict` | psycopg2 named |
| `named` | `:name` | `dict` | cx_Oracle named |
| `numeric` | `:1`, `:2`, … | `tuple` | cx_Oracle numeric |
