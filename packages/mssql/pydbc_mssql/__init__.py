"""
pydbc_mssql — pydbc driver for Microsoft SQL Server.

Wraps pymssql (format paramstyle: %s / %(name)s). Self-registers with
DriverManager on import.

Usage::

    import pydbc_mssql  # registers the driver
    from pydbc_core import DriverManager

    conn = DriverManager.get_connection("pydbc:mssql://user:pw@localhost:1433/mydb")
"""

from __future__ import annotations

from urllib.parse import urlparse

import pymssql

from pydbc_core import DriverManager
from pydbc_core.generic_db_api_driver import GenericDbApiConnection, GenericDbApiDriver

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

__all__: list[str] = ["MssqlDriver"]


class MssqlDriver(GenericDbApiDriver):
    """pydbc driver for Microsoft SQL Server via pymssql.

    Overrides :meth:`connect` to parse ``pydbc:mssql://...`` URLs into
    keyword arguments, since pymssql does not accept URL strings directly.

    Self-registers with :class:`~pydbc_core.driver_manager.DriverManager`
    on module import.  Inherits ``accepts_url`` from
    :class:`~pydbc_core.generic_db_api_driver.GenericDbApiDriver`.
    """

    URL_PREFIX = "pydbc:mssql:"

    def __init__(self) -> None:
        super().__init__(pymssql, self.URL_PREFIX)

    def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> GenericDbApiConnection:
        """Parse a ``pydbc:mssql://...`` URL and connect via keyword arguments.

        pymssql does not accept URL strings, so the URL is decomposed into
        individual connection parameters before calling ``pymssql.connect()``.

        For example, ``pydbc:mssql://user:pw@localhost:1433/mydb`` is
        translated to ``pymssql.connect(server='localhost', port='1433',
        user='user', password='pw', database='mydb')``.

        Note: pymssql requires ``server`` (not ``host``) and ``port`` must be
        a **string**, not an int.
        """
        parsed = urlparse(url[len(self.URL_PREFIX):])
        host = parsed.hostname
        port = str(parsed.port or 1433)
        user = parsed.username
        password = parsed.password
        database = parsed.path.lstrip("/")

        native_conn = pymssql.connect(
            server=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )
        return GenericDbApiConnection(native_conn, pymssql, pymssql.paramstyle)


# Self-register on import so that ``import pydbc_mssql`` is sufficient to
# make the driver available via DriverManager.
DriverManager.register_driver(MssqlDriver())
