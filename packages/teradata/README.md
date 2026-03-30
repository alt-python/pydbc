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
