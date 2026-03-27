"""
pydbc_core.pooled_data_source — PooledDataSource: a :class:`DataSource` that
vends pooled connections through :class:`SimpleConnectionPool`.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from pydbc_core.data_source import DataSource
from pydbc_core.driver_manager import DriverManager
from pydbc_core.simple_connection_pool import SimpleConnectionPool

if TYPE_CHECKING:
    from pydbc_core.connection import Connection
    from pydbc_core.connection_pool import ConnectionPool


class _PooledConnection:
    """Proxy that returns its underlying connection to the pool on :meth:`close`.

    Uses composition rather than inheritance so it is compatible with any
    :class:`~pydbc_core.connection.Connection` implementation.

    The proxy is a valid context manager::

        with data_source.get_connection() as conn:
            stmt = conn.create_statement()
            ...
        # connection returned to pool here
    """

    def __init__(self, real_conn: Any, pool: ConnectionPool) -> None:
        self._real = real_conn
        self._pool = pool
        self._released = False

    # ------------------------------------------------------------------
    # Connection method delegation
    # ------------------------------------------------------------------

    def create_statement(self):  # type: ignore[override]
        return self._real.create_statement()

    def prepare_statement(self, sql: str):  # type: ignore[override]
        return self._real.prepare_statement(sql)

    def set_auto_commit(self, v: bool) -> None:
        self._real.set_auto_commit(v)

    def commit(self) -> None:
        self._real.commit()

    def rollback(self) -> None:
        self._real.rollback()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Return the underlying connection to the pool (idempotent)."""
        if not self._released:
            self._released = True
            self._pool.release(self._real)

    def is_closed(self) -> bool:
        """Return ``True`` if this proxy has already been closed."""
        return self._released

    def __enter__(self) -> _PooledConnection:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class PooledDataSource(DataSource):
    """A :class:`~pydbc_core.data_source.DataSource` backed by a connection pool.

    Example (simple)::

        ds = PooledDataSource('pydbc:sqlite::memory:', pool={'max': 5})
        with ds.get_connection() as conn:
            ...
        ds.destroy()

    Example (custom pool)::

        my_pool = SimpleConnectionPool(factory, {'min': 2, 'max': 10})
        ds = PooledDataSource('pydbc:sqlite::memory:', connection_pool=my_pool)

    Args:
        url: A pydbc URL (e.g. ``pydbc:sqlite::memory:``).
        pool: Pool option dict forwarded to :class:`SimpleConnectionPool`
            (``min``, ``max``, ``acquire_timeout``).  Ignored when
            *connection_pool* is provided.
        connection_pool: An existing :class:`~pydbc_core.connection_pool.ConnectionPool`
            to use instead of creating a new :class:`SimpleConnectionPool`.
        **kwargs: Additional keyword arguments forwarded to
            :class:`~pydbc_core.data_source.DataSource` (e.g. ``username``,
            ``password``).
    """

    def __init__(
        self,
        url: str,
        pool: dict[str, Any] | None = None,
        connection_pool: ConnectionPool | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(url, **kwargs)

        if connection_pool is not None:
            self._pool: ConnectionPool = connection_pool
        else:
            opts = pool or {}

            def _create() -> Connection:
                props: dict[str, str] = dict(self._properties)
                if self._username:
                    props["user"] = self._username
                if self._password:
                    props["password"] = self._password
                return DriverManager.get_connection(self._url, props or None)

            factory: dict[str, Any] = {
                "create": _create,
                "destroy": lambda c: c.close(),
            }
            self._pool = SimpleConnectionPool(factory, opts)

    def get_connection(self) -> _PooledConnection:
        """Acquire a pooled connection.

        Returns a :class:`_PooledConnection` proxy.  Use it as a context
        manager to ensure the underlying connection is returned to the pool
        when the block exits.

        Raises:
            queue.Empty: if the pool is exhausted and no connection becomes
                available within the configured ``acquire_timeout``.
        """
        real = self._pool.acquire()
        return _PooledConnection(real, self._pool)

    def destroy(self) -> None:
        """Drain and close all idle connections in the pool."""
        self._pool.destroy()
