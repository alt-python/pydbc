"""
pydbc_pg — pydbc driver for PostgreSQL.

Wraps psycopg2 (pyformat paramstyle: %s / %(name)s). Self-registers with
DriverManager on import.

Usage::

    import pydbc_pg  # registers the driver
    from pydbc_core import DriverManager

    conn = DriverManager.get_connection("pydbc:pg://localhost/mydb")
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

__all__: list[str] = []
