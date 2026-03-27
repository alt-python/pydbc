"""
pydbc_core.simple_connection_pool — SimpleConnectionPool: a thread-safe
bounded connection pool backed by :class:`queue.Queue`.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable, TYPE_CHECKING

from pydbc_core.connection_pool import ConnectionPool

if TYPE_CHECKING:
    from pydbc_core.connection import Connection


class SimpleConnectionPool(ConnectionPool):
    """Thread-safe bounded connection pool backed by :class:`queue.Queue`.

    Args:
        factory: A dict with:
            - ``create`` (``Callable[[], Connection]``): opens a new connection.
            - ``destroy`` (``Callable[[Connection], None]``): closes a connection.
            - ``validate`` (``Callable[[Connection], bool]``, optional):
              returns ``False`` if the connection is no longer usable.
        options: A dict with optional configuration keys:
            - ``min`` (int, default 0): connections to open at startup.
            - ``max`` (int, default 10): maximum pool size.
            - ``acquire_timeout`` (float, default 30.0): seconds to wait
              before raising :exc:`queue.Empty` when the pool is exhausted.

    The pool is bounded to ``max`` total connections (idle + in-use).
    Callers that call :meth:`acquire` while all connections are in use will
    block for up to ``acquire_timeout`` seconds before receiving
    :exc:`queue.Empty`.

    Runtime observability::

        pool.num_used    # connections checked out by callers
        pool.num_free    # idle connections available immediately
        pool.num_pending # callers blocked waiting for a slot
    """

    def __init__(
        self,
        factory: dict[str, Callable[..., Any]],
        options: dict[str, Any] | None = None,
    ) -> None:
        opts = options or {}
        self._factory = factory
        self._min: int = int(opts.get("min", 0))
        self._max: int = int(opts.get("max", 10))
        self._acquire_timeout: float = float(opts.get("acquire_timeout", 30.0))

        # Queue maxsize caps total connections ever held by the queue; we also
        # track the total number allocated so we can grow up to _max.
        self._q: queue.Queue[Any] = queue.Queue(maxsize=self._max)
        self._lock = threading.Lock()
        self._num_used: int = 0
        self._num_pending: int = 0
        self._total: int = 0  # connections currently allocated (free + used)

        # Pre-warm with min connections.
        for _ in range(self._min):
            conn = self._factory["create"]()
            self._q.put_nowait(conn)
            self._total += 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_connection(self) -> Any:
        """Create and register a new connection. Caller must hold ``_lock``."""
        conn = self._factory["create"]()
        self._total += 1
        return conn

    # ------------------------------------------------------------------
    # ConnectionPool interface
    # ------------------------------------------------------------------

    def acquire(self) -> Any:
        """Acquire a connection, blocking up to *acquire_timeout* seconds.

        Raises:
            queue.Empty: if no connection becomes available within the timeout.
        """
        with self._lock:
            self._num_pending += 1

        try:
            # Try to get an idle connection first.
            try:
                conn = self._q.get_nowait()
            except queue.Empty:
                # No idle connection.  Can we create a new one?
                with self._lock:
                    if self._total < self._max:
                        conn = self._create_connection()
                    else:
                        conn = None  # must block on the queue

                if conn is None:
                    # Pool is at capacity — block until one is returned.
                    conn = self._q.get(timeout=self._acquire_timeout)
        finally:
            with self._lock:
                self._num_pending -= 1

        with self._lock:
            self._num_used += 1

        return conn

    def release(self, conn: Any) -> None:
        """Return *conn* to the pool.

        If a ``validate`` callable is registered and it returns ``False`` for
        *conn*, the stale connection is destroyed and replaced with a fresh one
        before being returned to the pool.
        """
        validate = self._factory.get("validate")
        if validate is not None and not validate(conn):
            self._factory["destroy"](conn)
            with self._lock:
                self._total -= 1
            conn = self._factory["create"]()
            with self._lock:
                self._total += 1

        self._q.put(conn)

        with self._lock:
            self._num_used -= 1

    def destroy(self) -> None:
        """Drain the pool and close all idle connections.

        Only idle connections (those currently in the queue) are destroyed;
        connections that are still checked out are unaffected.  Callers are
        responsible for releasing in-use connections before calling
        :meth:`destroy`.
        """
        while True:
            try:
                conn = self._q.get_nowait()
                self._factory["destroy"](conn)
                with self._lock:
                    self._total -= 1
            except queue.Empty:
                break

        with self._lock:
            self._num_used = 0
            self._num_pending = 0

    # ------------------------------------------------------------------
    # Observability properties
    # ------------------------------------------------------------------

    @property
    def num_used(self) -> int:
        """Connections currently checked out by callers."""
        with self._lock:
            return self._num_used

    @property
    def num_free(self) -> int:
        """Idle connections available for immediate acquisition."""
        return self._q.qsize()

    @property
    def num_pending(self) -> int:
        """Callers currently blocked waiting for a connection."""
        with self._lock:
            return self._num_pending
