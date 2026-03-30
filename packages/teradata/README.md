# alt-python-pydbc-teradata

pydbc driver for Teradata Database — wraps `teradatasql`.

## URL Format

```
pydbc:teradata://user:password@host:1025/database
```

- **Default port:** 1025
- **Paramstyle:** `qmark` — use `?` placeholders in SQL
- **Database:** optional — omit when connecting to the default database

## Usage

```python
import pydbc_teradata  # self-registers with DriverManager on import
from pydbc_core import DriverManager

conn = DriverManager.get_connection(
    "pydbc:teradata://user:password@host:1025/mydb"
)
```

## Full Example

```python
conn = DriverManager.get_connection(
    "pydbc:teradata://user:password@host:1025/mydb"
)
stmt = conn.create_statement()
stmt.execute_update("CREATE TABLE t (n INTEGER)")
stmt.execute_update("INSERT INTO t VALUES (?)", [42])
conn.commit()

rs = stmt.execute_query("SELECT n FROM t")
print(rs.rows)   # [(42,)]

conn.close()
```

Use `?` placeholders — Teradata driver uses qmark paramstyle.
