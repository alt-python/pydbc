# pydbc-mssql

pydbc driver for Microsoft SQL Server, wrapping [pymssql](https://pymssql.readthedocs.io/).

## Usage

```python
import pydbc_mssql  # registers the driver
from pydbc_core import DriverManager

conn = DriverManager.get_connection("pydbc:mssql://user:pw@localhost:1433/mydb")
cursor = conn.cursor()
cursor.execute("SELECT 1")
print(cursor.fetchone())
conn.close()
```

## URL format

```
pydbc:mssql://<user>:<password>@<host>:<port>/<database>
```

Default port: `1433`.
