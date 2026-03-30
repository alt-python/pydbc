"""
pydbc_teradata — pydbc driver for Teradata Database.

Wraps teradatasql. Self-registers with DriverManager on import.

Usage::

    import pydbc_teradata  # registers the driver
    from pydbc_core import DriverManager

    conn = DriverManager.get_connection(
        "pydbc:teradata://user:password@host:1025/database"
    )
"""

from __future__ import annotations

from urllib.parse import urlparse

import teradatasql

from pydbc_core import DriverManager
from pydbc_core.generic_db_api_driver import GenericDbApiConnection, GenericDbApiDriver

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

__all__: list[str] = ["TeradataDriver"]


class TeradataDriver(GenericDbApiDriver):
    """pydbc driver for Teradata Database via teradatasql.

    Overrides :meth:`connect` to parse ``pydbc:teradata://...`` URLs into
    keyword arguments for ``teradatasql.connect()``.  Unlike psycopg2,
    teradatasql does not accept a URL string — it requires keyword arguments
    (``host``, ``user``, ``password``, ``dbs_port``).

    The port must be passed as a string (``dbs_port``), not an int.  The
    ``database`` kwarg is omitted when the URL path is empty to avoid passing
    ``database=""`` which may cause an error.

    Uses ``"qmark"`` paramstyle — teradatasql natively uses ``?``
    placeholders, which the :class:`~pydbc_core.paramstyle_normalizer.ParamstyleNormalizer`
    passes through unchanged.

    Self-registers with :class:`~pydbc_core.driver_manager.DriverManager`
    on module import.  Inherits ``accepts_url`` from
    :class:`~pydbc_core.generic_db_api_driver.GenericDbApiDriver`.
    """

    URL_PREFIX = "pydbc:teradata:"

    def __init__(self) -> None:
        super().__init__(teradatasql, self.URL_PREFIX)

    def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> GenericDbApiConnection:
        """Parse a ``pydbc:teradata://...`` URL and connect via teradatasql.

        The URL is decomposed into ``host``, ``user``, ``password``,
        ``dbs_port``, and optionally ``database``.  teradatasql requires
        keyword arguments — it does not accept a URL string.

        ``dbs_port`` is always passed as a string (not int).  The
        ``database`` kwarg is omitted when the URL path is empty.

        For example, ``pydbc:teradata://user:pw@host:1025/mydb``
        calls ``teradatasql.connect(host='host', user='user',
        password='pw', dbs_port='1025', database='mydb')``.
        """
        parsed = urlparse(url[len(self.URL_PREFIX):])
        host = parsed.hostname
        user = parsed.username
        password = parsed.password
        port = str(parsed.port or 1025)
        database = parsed.path.lstrip("/")

        kwargs: dict = {
            "host": host,
            "user": user,
            "password": password,
            "dbs_port": port,
        }
        if database:
            kwargs["database"] = database

        native_conn = teradatasql.connect(**kwargs)
        return GenericDbApiConnection(native_conn, teradatasql, "qmark")


# Self-register on import so that ``import pydbc_teradata`` is sufficient to
# make the driver available via DriverManager.
DriverManager.register_driver(TeradataDriver())
