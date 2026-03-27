"""
pydbc_core.single_connection_data_source — SingleConnectionDataSource:
a DataSource that reuses a single underlying connection (ideal for
in-memory databases such as ``sqlite3 :memory:``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydbc_core.data_source import DataSource
from pydbc_core.driver_manager import DriverManager

if TYPE_CHECKING:
    from pydbc_core.connection import Connection


class SingleConnectionDataSource(DataSource):
    """A :class:`~pydbc_core.data_source.DataSource` that vends the same
    :class:`~pydbc_core.connection.Connection` on every call to
    :meth:`get_connection`.

    Useful for sharing an in-memory SQLite database across an entire test
    suite without losing state between statements.

    **Lifecycle:**

    * :meth:`get_connection` — lazily opens the connection on first call
      (or re-opens if the cached connection is closed).
    * :meth:`close` — intentional no-op so callers cannot accidentally
      discard the shared connection.
    * :meth:`destroy` — actually closes the underlying connection and
      releases resources; call this in teardown.
    """

    def __init__(
        self,
        url: str,
        username: str | None = None,
        password: str | None = None,
        **properties,
    ) -> None:
        super().__init__(url, username, password, **properties)
        self._connection: Connection | None = None

    def get_connection(self) -> Connection:
        """Return the cached connection, opening it if necessary."""
        if self._connection is None or self._connection.is_closed():
            props = dict(self._properties)
            if self._username is not None:
                props["user"] = self._username
            if self._password is not None:
                props["password"] = self._password
            self._connection = DriverManager.get_connection(self._url, props or None)
        return self._connection

    def close(self) -> None:  # type: ignore[override]
        """No-op — deliberately does *not* close the underlying connection.

        Call :meth:`destroy` to actually release resources.
        """

    def destroy(self) -> None:
        """Close and discard the cached connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
