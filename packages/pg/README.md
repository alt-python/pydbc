# alt-python-pydbc-pg

pydbc driver for PostgreSQL via [psycopg2](https://www.psycopg.org/docs/).

---

## Installation

```bash
uv add alt-python-pydbc-pg
```

> **Note:** `psycopg2-binary` is installed automatically and works for development
> and CI. For production deployments, replace it with `psycopg2` (compiled against
> the system `libpq`). See the
> [psycopg2 installation docs](https://www.psycopg.org/docs/install.html) for details.

---

## URL format

```
pydbc:pg://user:password@host:port/dbname
```

The port defaults to `5432` if omitted.

---

## Usage

```python
import pydbc_pg  # registers PgDriver with DriverManager
from pydbc_core import DriverManager

conn = DriverManager.get_connection("pydbc:pg://alice:secret@localhost:5432/mydb")
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

psycopg2 uses `pyformat` (`%s` / `%(name)s`) placeholders internally. pydbc accepts
both `?` (positional) and `:name` (named) syntax and translates automatically — you
never need to know which style the underlying driver uses.

---

## Documentation

- [Getting started tutorial](https://github.com/alt-python/pydbc/blob/main/docs/getting-started.md)
- [Core API reference](https://github.com/alt-python/pydbc/blob/main/docs/api-reference.md)

---

## License

MIT
