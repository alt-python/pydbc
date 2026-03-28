# alt-python-pydbc-oracle

pydbc driver for Oracle Database via [python-oracledb](https://python-oracledb.readthedocs.io/) (thin mode).

---

## Installation

```bash
uv add alt-python-pydbc-oracle
```

---

## URL format

```
pydbc:oracle://user:password@host:port/service_name
```

The port defaults to `1521` if omitted.

---

## Usage

```python
import pydbc_oracle  # registers OracleDriver with DriverManager
from pydbc_core import DriverManager

conn = DriverManager.get_connection(
    "pydbc:oracle://system:password@localhost:1521/FREEPDB1"
)
stmt = conn.create_statement()
rs = stmt.execute_query("SELECT 1 FROM dual")
print(rs.rows)
conn.close()
```

### Parameterised queries

```python
# Positional parameters (translated to :1, :2 numerics)
ps = conn.prepare_statement("SELECT * FROM users WHERE id = ?")
ps.set_int(1, 42)
rs = ps.execute_query()

# Named parameters (translated to :1, :2 numerics)
ps = conn.prepare_statement("SELECT * FROM users WHERE id = :id")
ps.set_int(1, 42)
rs = ps.execute_query()
```

---

## Paramstyle note

python-oracledb uses `named` paramstyle internally (`:name` placeholders), but pydbc
forces `numeric` (`:1`, `:2`) for this driver because the `ParamstyleNormalizer`
handles both `?` and `:name` inputs and produces numeric output that oracledb accepts.

---

## Documentation

- [Getting started tutorial](https://github.com/alt-python/pydbc/blob/main/docs/getting-started.md)
- [Core API reference](https://github.com/alt-python/pydbc/blob/main/docs/api-reference.md)

---

## License

MIT
