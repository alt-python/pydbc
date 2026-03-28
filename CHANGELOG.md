# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added

#### M001 — Core

- `pydbc_core` package: ABCs for Driver, Connection, Statement, PreparedStatement, ResultSet, DataSource, ConnectionPool
- `DriverManager` with URL-based dispatch; drivers self-register on import
- `GenericDbApiDriver` — wraps any PEP 249 DB-API 2.0 compliant module
- `ParamstyleNormalizer` — translates `?` / `:name` SQL to any DB-API 2.0 paramstyle at execution time
- `SingleConnectionDataSource` — simple DataSource wrapping a single connection URL
- Context manager support on all resource types (`__enter__` / `__exit__`)
- `alt-python-pydbc-sqlite` driver wrapping stdlib `sqlite3` (qmark paramstyle); URL: `pydbc:sqlite:./path`
- `alt-python-pydbc-pg` driver wrapping `psycopg2` (pyformat paramstyle); URL: `pydbc:pg://host:port/dbname`

#### M002 — Additional drivers

- `alt-python-pydbc-mysql` driver wrapping `PyMySQL` (pyformat paramstyle); URL: `pydbc:mysql://host:port/dbname`
- `alt-python-pydbc-mssql` driver wrapping `pymssql` (pyformat paramstyle); URL: `pydbc:mssql://host:port/dbname`

#### M003 — Pooling and convenience

- `SimpleConnectionPool` — thread-safe bounded connection pool backed by `queue.Queue`
- `PooledDataSource` — DataSource backed by a pool; `with ds.get_connection() as conn:` returns connection to pool on exit
- `NamedParameterDataSource` — accepts `:paramName` SQL + dict; mirrors Spring's `NamedParameterJdbcTemplate`

#### M004 — Documentation

- `docs/assessment.md` — Python DB access landscape analysis and pydbc design rationale
- `docs/getting-started.md` — end-to-end tutorial
- `docs/api-reference.md` — full API reference for all `pydbc_core` exports
- `docs/driver-guide.md` — guide for writing custom drivers
- Per-package README files

#### M005 — Oracle driver

- `alt-python-pydbc-oracle` driver wrapping `oracledb` (python-oracledb, thin mode, numeric paramstyle); URL: `pydbc:oracle://user:pw@host:1521/service_name`

[Unreleased]: https://keepachangelog.com/en/1.1.0/
[0.1.0]: https://keepachangelog.com/en/1.1.0/
