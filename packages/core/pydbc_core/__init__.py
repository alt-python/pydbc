"""
pydbc_core — Core abstraction hierarchy for pydbc.

Provides:
  Driver                 — ABC for database drivers
  DriverManager          — Registry and URL-based connection dispatcher
  Connection             — ABC for database connections (context manager)
  Statement              — ABC for ad-hoc SQL execution
  PreparedStatement      — ABC for parameterized SQL execution
  ResultSet              — Cursor-based and bulk row access
  DataSource             — Connection factory
  SingleConnectionDataSource — Reuses a single connection (for :memory: DBs)
  ParamstyleNormalizer   — Translates canonical ? / :name to driver-native paramstyle
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

__all__: list[str] = []
