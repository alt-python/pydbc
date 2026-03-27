# alt-python-pydbc-mysql

pydbc driver for MySQL — wraps [PyMySQL](https://pymysql.readthedocs.io/) with the pydbc unified DB access abstraction.

## Usage

```python
import pydbc_mysql  # registers MysqlDriver with DriverManager
from pydbc_core import DriverManager

conn = DriverManager.get_connection("pydbc:mysql://user:password@localhost:3306/mydb")
stmt = conn.create_statement()
rs = stmt.execute_query("SELECT 1")
print(rs.rows)
conn.close()
```

## URL format

```
pydbc:mysql://[user[:password]@]host[:port]/database
```

The port defaults to `3306` if omitted.

## Installation

```
uv add alt-python-pydbc-mysql
```

## License

MIT
