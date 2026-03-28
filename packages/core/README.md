# alt-python-pydbc-core

Core abstraction layer for [pydbc](https://github.com/alt-python/pydbc) — the uniform database access library for Python.

This package provides the ABCs, registries, and generic helpers that all pydbc driver packages depend on. **You do not normally install this package directly.** Install the driver package for your database; `alt-python-pydbc-core` is pulled in automatically as a dependency.

```bash
# Install the driver for your database — core is a transitive dependency
uv add alt-python-pydbc-sqlite    # SQLite
uv add alt-python-pydbc-pg        # PostgreSQL
uv add alt-python-pydbc-mysql     # MySQL / MariaDB
uv add alt-python-pydbc-mssql     # SQL Server
```

---

## What this package provides

### ABCs (Abstract Base Classes)

| Class | Purpose |
|---|---|
| `Driver` | Abstract base for all pydbc drivers |
| `Connection` | Abstract connection handle |
| `Statement` | Execute arbitrary SQL |
| `PreparedStatement` | Execute pre-compiled SQL with bound parameters |
| `ResultSet` | Row access after a query |
| `DataSource` | Connection factory abstraction |
| `ConnectionPool` | Connection pool abstraction |

### DriverManager

Central registry that maps connection URLs to registered drivers. Driver packages
self-register at import time by calling `DriverManager.register_driver()`.

```python
import pydbc_sqlite  # registers SQLiteDriver
from pydbc_core import DriverManager

conn = DriverManager.get_connection("pydbc:sqlite::memory:")
stmt = conn.create_statement()
rs = stmt.execute_query("SELECT 42 AS n")
print(rs.rows)   # [(42,)]
conn.close()
```

### GenericDbApiDriver

A reusable base driver that wraps any DB-API 2.0 module. Driver packages typically
subclass this; it handles connection lifecycle, cursor management, and paramstyle
normalisation automatically.

### DataSource helpers

| Class | When to use |
|---|---|
| `SingleConnectionDataSource` | Tests and scripts that need one persistent connection |
| `PooledDataSource` | Servers and applications that need a connection pool |
| `NamedParameterDataSource` | Convenience wrapper with named-parameter query/update methods |

### ParamstyleNormalizer

Rewrites SQL written with `?` (positional) or `:name` (named) placeholders to
whatever the underlying DB-API 2.0 driver expects (`%s`, `%(name)s`, `:1`, etc.).
This means you write SQL once and it works against any driver.

---

## Documentation

- [Getting started tutorial](docs/getting-started.md)
- [Core API reference](docs/api-reference.md)

---

## License

MIT
