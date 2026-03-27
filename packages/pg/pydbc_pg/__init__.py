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

import psycopg2

from pydbc_core import DriverManager
from pydbc_core.generic_db_api_driver import GenericDbApiConnection, GenericDbApiDriver

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

__all__: list[str] = ["PgDriver"]


class PgDriver(GenericDbApiDriver):
    """pydbc driver for PostgreSQL via psycopg2.

    Overrides :meth:`connect` to translate ``pydbc:pg://...`` URLs to the
    ``postgresql://...`` scheme that psycopg2 expects.

    Self-registers with :class:`~pydbc_core.driver_manager.DriverManager`
    on module import.  Inherits ``accepts_url`` from
    :class:`~pydbc_core.generic_db_api_driver.GenericDbApiDriver`.
    """

    URL_PREFIX = "pydbc:pg:"

    def __init__(self) -> None:
        super().__init__(psycopg2, self.URL_PREFIX)

    def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> GenericDbApiConnection:
        """Translate a ``pydbc:pg://...`` URL to ``postgresql://...`` and connect.

        For example, ``pydbc:pg://user:pw@localhost:5432/mydb`` becomes
        ``postgresql://user:pw@localhost:5432/mydb`` which psycopg2
        understands natively.
        """
        native_url = "postgresql:" + url[len(self.URL_PREFIX):]
        native_conn = psycopg2.connect(native_url)
        return GenericDbApiConnection(native_conn, psycopg2, psycopg2.paramstyle)


# Self-register on import so that ``import pydbc_pg`` is sufficient to
# make the driver available via DriverManager.
DriverManager.register_driver(PgDriver())
