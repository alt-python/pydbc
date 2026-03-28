# alt-python-pydbc-mssql

pydbc driver for Microsoft SQL Server via [pymssql](https://pymssql.readthedocs.io/).

---

## Installation

```bash
uv add alt-python-pydbc-mssql
```

---

## URL format

```
pydbc:mssql://user:password@host:port/database
```

The port defaults to `1433` if omitted.

---

## Usage

```python
import pydbc_mssql  # registers MssqlDriver with DriverManager
from pydbc_core import DriverManager

conn = DriverManager.get_connection("pydbc:mssql://user:pw@localhost:1433/mydb")
stmt = conn.create_statement()
rs = stmt.execute_query("SELECT 1 AS n")
print(rs.rows)   # [(1,)]
conn.close()
```

### Parameterised queries

```python
# Positional parameters
stmt = conn.create_statement()
rs = stmt.execute_query("SELECT * FROM users WHERE id = ?", (42,))

# Named parameters
rs = stmt.execute_query("SELECT * FROM users WHERE id = :id", {"id": 42})
```

### Prepared statements

```python
ps = conn.prepare_statement("INSERT INTO users (name, email) VALUES (?, ?)")
ps.execute_update(("Alice", "alice@example.com"))
conn.commit()
```

---

## Paramstyle note

pymssql uses `pyformat` (`%s` / `%(name)s`) placeholders internally. pydbc accepts
both `?` (positional) and `:name` (named) syntax and translates automatically — you
never need to know which style the underlying driver uses.

---

## Documentation

- [Getting started tutorial](docs/getting-started.md)
- [Core API reference](docs/api-reference.md)

---

## License

MIT
