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

import sqlite3

from pydbc_core import DriverManager
from pydbc_core.generic_db_api_driver import GenericDbApiDriver

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

__all__: list[str] = ["SqliteDriver"]


class SqliteDriver(GenericDbApiDriver):
    """pydbc driver for SQLite via stdlib sqlite3.

    Self-registers with :class:`~pydbc_core.driver_manager.DriverManager`
    on module import.  Inherits ``accepts_url`` and ``connect`` from
    :class:`~pydbc_core.generic_db_api_driver.GenericDbApiDriver`.
    """

    URL_PREFIX = "pydbc:sqlite:"

    def __init__(self) -> None:
        super().__init__(sqlite3, self.URL_PREFIX)


# Self-register on import so that ``import pydbc_sqlite`` is sufficient to
# make the driver available via DriverManager.
DriverManager.register_driver(SqliteDriver())
