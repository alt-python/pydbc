# Python Database Access: A Landscape Assessment and the Case for pydbc

## The Python DB Access Landscape

Python has a rich ecosystem of database drivers. For relational databases, the most widely used are:

- **stdlib `sqlite3`** — built-in, zero-dependency SQLite driver; the reference implementation for PEP 249
- **psycopg2** — the dominant PostgreSQL adapter; mature, fast, widely deployed
- **psycopg3 (psycopg)** — the modern successor to psycopg2; cleaner API, native async support, growing adoption
- **mysql-connector-python** — MySQL's official Python connector
- **PyMySQL** — pure-Python MySQL/MariaDB adapter; popular for environments where the C extension is unavailable
- **pyodbc** — ODBC bridge; primary path to SQL Server and other ODBC-capable databases
- **pymssql** — C-extension SQL Server driver; simpler than pyodbc but narrower scope

Above the driver layer, there are higher-level abstractions:

- **SQLAlchemy Core** — a comprehensive SQL toolkit and expression language; DB-API 2.0 sits underneath, but SQLAlchemy interposes its own dialect layer, connection pool, and metadata system
- **SQLAlchemy ORM** — full object-relational mapper built on Core
- **Records** — a thin wrapper over SQLAlchemy Core for "just run SQL" use cases; opinionated about row access style

## PEP 249 and Its Gaps

PEP 249 (DB-API 2.0) is Python's database API specification. It defines a standard interface that all compliant drivers implement: `connect()`, cursor objects with `execute()`, `fetchone()`, `fetchmany()`, `fetchall()`, transaction control via `commit()` and `rollback()`, and a set of exception types.

This is genuinely useful. Any code written against the PEP 249 interface can switch databases by swapping the driver import. In practice, however, PEP 249 leaves several critical gaps:

**No dispatch mechanism.** PEP 249 says nothing about how to obtain a driver for a given database URL. Every application must import the specific driver module directly — `import psycopg2`, `import sqlite3` — which hard-codes the database choice at the import level. There is no equivalent of JDBC's `DriverManager.getConnection("jdbc:postgresql://...")`.

**No abstract base classes.** PEP 249 is a specification document, not a type hierarchy. There are no ABCs to program against. Code that wants to accept "any DB-API 2.0 connection" must use duck typing or define its own protocol, with no standard interface to target.

**No standard URL scheme.** Each driver has its own connection string format. `sqlite3.connect(":memory:")`, `psycopg2.connect("host=localhost dbname=mydb")`, `pyodbc.connect("DSN=mydb")` — there is no unified address format.

**No paramstyle standard.** This is the most practically painful gap.

## The Paramstyle Problem

PEP 249 defines a `paramstyle` module attribute that each driver must set, but it does not mandate which style to use. The five defined styles are:

| Style | Placeholder syntax | Driver examples |
|---|---|---|
| `qmark` | `?` | sqlite3, pyodbc |
| `numeric` | `:1`, `:2` | cx_Oracle |
| `named` | `:name` | cx_Oracle, sqlite3 (also supports this) |
| `format` | `%s` | psycopg2 (alternate) |
| `pyformat` | `%s`, `%(name)s` | psycopg2, mysql-connector, PyMySQL |

This means that SQL written for SQLite (`WHERE id = ?`) does not run on PostgreSQL without changing every parameter placeholder to `%s`. SQL written for PostgreSQL does not run on SQLite. Code that abstracts over both databases must either maintain duplicate SQL strings or perform its own translation.

The fragmentation is not theoretical. Applications that need to support multiple databases — for testing (SQLite in-memory) and production (PostgreSQL), or for multi-tenant SaaS where different customers use different databases — must solve this problem themselves, repeatedly, with no standard answer.

## What Exists

**SQLAlchemy** solves paramstyle fragmentation through its own dialect system, but it also brings a complete SQL expression language, a metadata layer, and (optionally) a full ORM. For applications that want to write raw SQL and execute it against any database, SQLAlchemy's abstraction surface is disproportionate. It is the right tool for many projects; it is not a thin facade.

**Records** (by Kenneth Reitz) wraps SQLAlchemy Core to provide a simple "just run SQL" interface. It reduces boilerplate but inherits SQLAlchemy's weight and does not expose an ABC hierarchy or URL dispatch layer distinct from SQLAlchemy's.

**Plain DB-API 2.0** is genuinely portable — but only if every caller handles paramstyle differences themselves and hard-codes driver imports. There is no dispatch, no abstraction hierarchy, and no normalization.

## What's Missing

The Python ecosystem has no lightweight library that provides what JDBC gives Java:

1. **URL-based driver dispatch** — `DriverManager.get_connection("pydbc:sqlite::memory:")` routes to the correct driver without the caller knowing which module to import
2. **A programmatic ABC hierarchy** — `Connection`, `Statement`, `PreparedStatement`, `ResultSet` as real types to program against and mock in tests
3. **Paramstyle normalization** — write `?` (positional) or `:name` (named) once; the library translates to the driver's native style at execution time
4. **Context manager support across all resource types** — `with ds.get_connection() as conn:` closes reliably; same pattern for statements and result sets

## The pydbc Design

pydbc fills this gap by adding a JDBC-style dispatch and unification layer on top of existing PEP 249 compliant drivers. The key design decisions:

**Wrap DB-API 2.0, not native drivers.** Python has PEP 249 where JavaScript has nothing. A single `GenericDbApiDriver` can wrap any compliant driver by reading `module.paramstyle` and routing through the normalizer. This is different from jsdbc (the JavaScript counterpart), which wraps native drivers directly because JavaScript has no equivalent standard.

**Canonical paramstyle.** Users write `?` for positional parameters and `:name` for named parameters. The `ParamstyleNormalizer` in `pydbc_core` translates to the driver's native style at execution time — `qmark` (sqlite3, pyodbc) requires no translation; `pyformat` (psycopg2, mysql-connector) maps `?` → `%s` and `:name` → `%(name)s`; `named` (cx_Oracle) maps `?` → `:1` style. This normalization lives in core, not in each driver, so driver packages contain zero translation code.

**Driver self-registration on import.** `import pydbc_sqlite` registers the SQLite driver with `DriverManager` as a module-level side effect. No configuration file, no explicit registration call. This mirrors jsdbc ADR-003 and Python's own `codec` and `logging.handlers` registration patterns.

**Context managers on all resource types.** `Connection`, `Statement`, `PreparedStatement`, and `ResultSet` all implement `__enter__`/`__exit__`. `with ds.get_connection() as conn:` is the idiomatic usage pattern and prevents connection leaks. Explicit `close()` is also supported.

## The JavaScript Counterpart

pydbc is a port of [@alt-javascript/jsdbc](https://github.com/alt-javascript/jsdbc) to Python. jsdbc provides the same DriverManager dispatch and ABC hierarchy for JavaScript/Node.js. The key difference in design: jsdbc wraps native drivers (better-sqlite3, pg, mysql2) directly because JavaScript has no PEP 249 equivalent; pydbc wraps DB-API 2.0 drivers because the spec exists and is widely implemented. The external API and architecture are otherwise equivalent.

## psycopg2 vs psycopg3

psycopg2 is the initial target for `pydbc_pg`. It has the larger install base, is stable, and uses `pyformat` paramstyle. psycopg3 (the `psycopg` package) also uses `pyformat` and has a broadly compatible API at the connection and cursor level, with the addition of native async support. The pydbc-pg driver is designed so that switching the underlying driver from psycopg2 to psycopg3 requires only changes to the driver's `connect()` implementation — the normalization and ABC layers are unaffected. psycopg3 compatibility is a planned future enhancement documented here for completeness.

For development and testing, `psycopg2-binary` (which bundles libpq) is the appropriate install. Production deployments should prefer the non-binary `psycopg2` wheel built against the system libpq for better performance and compatibility.
