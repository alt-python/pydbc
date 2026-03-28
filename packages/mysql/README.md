# alt-python-pydbc-mysql

pydbc driver for MySQL — wraps [PyMySQL](https://pymysql.readthedocs.io/) with the pydbc unified DB access abstraction.

---

## Installation

```bash
uv add alt-python-pydbc-mysql
```

> **Note:** The `cryptography` package is installed automatically as a runtime
> dependency. It is required for MySQL 8.0's default `caching_sha2_password`
> authentication plugin — without it connections will fail. You do not need to
> install it separately.

---

## URL format

```
pydbc:mysql://[user[:password]@]host[:port]/database
```

The port defaults to `3306` if omitted.

---

## Usage

```python
import pydbc_mysql  # registers MysqlDriver with DriverManager
from pydbc_core import DriverManager

conn = DriverManager.get_connection("pydbc:mysql://user:password@localhost:3306/mydb")
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

PyMySQL uses `format` (`%s`) placeholders internally. pydbc accepts both `?`
(positional) and `:name` (named) syntax and translates automatically — you never
need to know which style the underlying driver uses.

---

## Documentation

- [Getting started tutorial](https://github.com/alt-python/pydbc/blob/main/docs/getting-started.md)
- [Core API reference](https://github.com/alt-python/pydbc/blob/main/docs/api-reference.md)

---

## License

MIT
