"""
pydbc_oracle — pydbc driver for Oracle Database.

Wraps oracledb (python-oracledb thin mode). Self-registers with
DriverManager on import.

Usage::

    import pydbc_oracle  # registers the driver
    from pydbc_core import DriverManager

    conn = DriverManager.get_connection(
        "pydbc:oracle://system:password@localhost:1521/FREEPDB1"
    )
"""

from __future__ import annotations

from urllib.parse import urlparse

import oracledb

from pydbc_core import DriverManager
from pydbc_core.generic_db_api_driver import GenericDbApiConnection, GenericDbApiDriver

__author__ = "Craig Parravicini"
__collaborators__ = ["Claude (Anthropic)"]

__all__: list[str] = ["OracleDriver"]


class OracleDriver(GenericDbApiDriver):
    """pydbc driver for Oracle Database via python-oracledb (thin mode).

    Overrides :meth:`connect` to parse ``pydbc:oracle://...`` URLs into
    an Oracle DSN string (``host:port/service_name``) and force the
    ``"numeric"`` paramstyle, since oracledb accepts ``:1``, ``:2``
    numeric placeholders and the ``ParamstyleNormalizer._to_named`` path
    raises for positional tuple params.

    Self-registers with :class:`~pydbc_core.driver_manager.DriverManager`
    on module import.  Inherits ``accepts_url`` from
    :class:`~pydbc_core.generic_db_api_driver.GenericDbApiDriver`.
    """

    URL_PREFIX = "pydbc:oracle:"

    def __init__(self) -> None:
        super().__init__(oracledb, self.URL_PREFIX)

    def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> GenericDbApiConnection:
        """Parse a ``pydbc:oracle://...`` URL and connect via python-oracledb.

        The URL is decomposed into ``user``, ``password``, and a DSN of the
        form ``host:port/service_name``.  python-oracledb thin mode accepts
        this DSN format directly.

        The connection is wrapped with paramstyle ``"numeric"`` (not
        ``oracledb.paramstyle`` which is ``"named"``).  The
        :class:`~pydbc_core.paramstyle_normalizer.ParamstyleNormalizer`
        ``_to_numeric`` path handles both ``?`` and ``:name`` inputs and
        produces ``:1``, ``:2`` placeholders that oracledb accepts.

        For example, ``pydbc:oracle://system:pw@localhost:1521/FREEPDB1``
        calls ``oracledb.connect(user='system', password='pw',
        dsn='localhost:1521/FREEPDB1')``.
        """
        parsed = urlparse(url[len(self.URL_PREFIX):])
        host = parsed.hostname
        port = parsed.port or 1521
        user = parsed.username
        password = parsed.password
        service_name = parsed.path.lstrip("/")
        dsn = f"{host}:{port}/{service_name}"

        native_conn = oracledb.connect(user=user, password=password, dsn=dsn)
        return GenericDbApiConnection(native_conn, oracledb, "numeric")


# Self-register on import so that ``import pydbc_oracle`` is sufficient to
# make the driver available via DriverManager.
DriverManager.register_driver(OracleDriver())
