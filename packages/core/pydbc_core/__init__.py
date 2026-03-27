"""
pydbc_core — Core abstraction hierarchy for pydbc.

Provides:
  Driver                        — ABC for database drivers
  DriverManager                 — Registry and URL-based connection dispatcher
  Connection                    — ABC for database connections (context manager)
  Statement                     — ABC for ad-hoc SQL execution
  PreparedStatement             — ABC for parameterized SQL execution
  ResultSet                     — Cursor-based and bulk row access
  DataSource                    — Connection factory
  SingleConnectionDataSource    — Reuses a single connection (for :memory: DBs)
  ParamstyleNormalizer          — Translates canonical ? / :name to driver-native paramstyle
  GenericDbApiDriver            — Wraps any PEP 249 module in the pydbc hierarchy
  ConnectionPool                — ABC for connection pool implementations
  SimpleConnectionPool          — Thread-safe bounded pool backed by queue.Queue
  PooledDataSource              — DataSource that vends pooled connections
  NamedParameterDataSource      — DataSource with :paramName SQL template methods
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

from pydbc_core.connection import Connection
from pydbc_core.connection_pool import ConnectionPool
from pydbc_core.data_source import DataSource
from pydbc_core.driver import Driver
from pydbc_core.driver_manager import DriverManager
from pydbc_core.generic_db_api_driver import GenericDbApiDriver
from pydbc_core.named_parameter_data_source import NamedParameterDataSource
from pydbc_core.paramstyle_normalizer import ParamstyleNormalizer
from pydbc_core.pooled_data_source import PooledDataSource
from pydbc_core.prepared_statement import PreparedStatement
from pydbc_core.result_set import ResultSet
from pydbc_core.simple_connection_pool import SimpleConnectionPool
from pydbc_core.single_connection_data_source import SingleConnectionDataSource
from pydbc_core.statement import Statement

__all__ = [
    "Driver",
    "Connection",
    "Statement",
    "PreparedStatement",
    "ResultSet",
    "DriverManager",
    "DataSource",
    "SingleConnectionDataSource",
    "ParamstyleNormalizer",
    "GenericDbApiDriver",
    "ConnectionPool",
    "SimpleConnectionPool",
    "PooledDataSource",
    "NamedParameterDataSource",
]
