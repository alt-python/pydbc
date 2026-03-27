"""
pydbc_mysql — pydbc driver for MySQL.

Wraps PyMySQL (format paramstyle: %s / %(name)s). Self-registers with
DriverManager on import.

Usage::

    import pydbc_mysql  # registers the driver
    from pydbc_core import DriverManager

    conn = DriverManager.get_connection("pydbc:mysql://user:pw@localhost/mydb")
"""

from __future__ import annotations

from urllib.parse import urlparse

import pymysql

from pydbc_core import DriverManager
from pydbc_core.generic_db_api_driver import GenericDbApiConnection, GenericDbApiDriver

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

__all__: list[str] = ["MysqlDriver"]


class MysqlDriver(GenericDbApiDriver):
    """pydbc driver for MySQL via PyMySQL.

    Overrides :meth:`connect` to parse ``pydbc:mysql://...`` URLs into
    keyword arguments, since PyMySQL does not accept URL strings directly.

    Self-registers with :class:`~pydbc_core.driver_manager.DriverManager`
    on module import.  Inherits ``accepts_url`` from
    :class:`~pydbc_core.generic_db_api_driver.GenericDbApiDriver`.
    """

    URL_PREFIX = "pydbc:mysql:"

    def __init__(self) -> None:
        super().__init__(pymysql, self.URL_PREFIX)

    def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> GenericDbApiConnection:
        """Parse a ``pydbc:mysql://...`` URL and connect via keyword arguments.

        PyMySQL does not accept URL strings, so the URL is decomposed into
        individual connection parameters before calling ``pymysql.connect()``.

        For example, ``pydbc:mysql://user:pw@localhost:3306/mydb`` is
        translated to ``pymysql.connect(host='localhost', port=3306,
        user='user', password='pw', database='mydb')``.
        """
        parsed = urlparse(url[len(self.URL_PREFIX):])
        host = parsed.hostname
        port = parsed.port or 3306
        user = parsed.username
        password = parsed.password
        database = parsed.path.lstrip("/")

        native_conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )
        return GenericDbApiConnection(native_conn, pymysql, pymysql.paramstyle)


# Self-register on import so that ``import pydbc_mysql`` is sufficient to
# make the driver available via DriverManager.
DriverManager.register_driver(MysqlDriver())
