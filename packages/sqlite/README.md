# alt-python-pydbc-sqlite

pydbc driver for SQLite via the Python standard-library `sqlite3` module. Zero external dependencies.

---

## Installation

```bash
uv add alt-python-pydbc-sqlite
```

---

## URL formats

| Format | Description |
|---|---|
| `pydbc:sqlite::memory:` | In-memory database (isolated per connection) |
| `pydbc:sqlite:./path/to/db` | File-backed database |
| `pydbc:sqlite:/absolute/path/to/db` | File-backed database (absolute path) |

---

## Usage

```python
import pydbc_sqlite  # registers SQLiteDriver with DriverManager
from pydbc_core import DriverManager

conn = DriverManager.get_connection("pydbc:sqlite::memory:")
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
ps.execute_update(("Bob", "bob@example.com"))
conn.commit()
```

---

## Paramstyle note

`sqlite3` uses `qmark` (`?`) placeholders internally. pydbc accepts both `?`
(positional) and `:name` (named) syntax and translates automatically — you never
need to know which style the underlying driver uses.

---

## Documentation

- [Getting started tutorial](https://github.com/alt-python/pydbc/blob/main/docs/getting-started.md)
- [Core API reference](https://github.com/alt-python/pydbc/blob/main/docs/api-reference.md)

---

## License

MIT
