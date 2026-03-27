"""
pydbc_core.data_source — DataSource: URL-based connection factory backed by
:class:`~pydbc_core.driver_manager.DriverManager`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydbc_core.driver_manager import DriverManager

if TYPE_CHECKING:
    from pydbc_core.connection import Connection


class DataSource:
    """Connection factory that resolves connections through :class:`DriverManager`.

    Example::

        ds = DataSource('pydbc:sqlite::memory:')
        conn = ds.get_connection()
    """

    def __init__(
        self,
        url: str,
        username: str | None = None,
        password: str | None = None,
        **properties,
    ) -> None:
        self._url = url
        self._username = username
        self._password = password
        self._properties: dict = dict(properties)

    def get_connection(self) -> Connection:
        """Return a new :class:`~pydbc_core.connection.Connection` from the
        driver that accepts :attr:`url`.

        ``username`` and ``password`` are merged into the properties dict
        (as keys ``"user"`` and ``"password"``) when set.
        """
        props = dict(self._properties)
        if self._username is not None:
            props["user"] = self._username
        if self._password is not None:
            props["password"] = self._password
        return DriverManager.get_connection(self._url, props or None)

    def get_url(self) -> str:
        """Return the pydbc URL this data source connects to."""
        return self._url
