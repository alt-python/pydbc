"""
pydbc_sqlite — pydbc driver for SQLite.

Wraps stdlib sqlite3 (qmark paramstyle). Self-registers with DriverManager
on import.

Usage::

    import pydbc_sqlite  # registers the driver
    from pydbc_core import DriverManager

    conn = DriverManager.get_connection("pydbc:sqlite::memory:")
"""

from __future__ import annotations

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

__all__: list[str] = []
