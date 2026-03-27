"""
pydbc_core.connection_pool — ConnectionPool ABC.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydbc_core.connection import Connection


class ConnectionPool(ABC):
    """Abstract base class for connection pool implementations."""

    @abstractmethod
    def acquire(self) -> Connection:
        """Acquire a connection from the pool, blocking if none are available."""

    @abstractmethod
    def release(self, conn: Connection) -> None:
        """Return *conn* to the pool."""

    @abstractmethod
    def destroy(self) -> None:
        """Close all connections managed by this pool and release resources."""

    @property
    @abstractmethod
    def num_used(self) -> int:
        """Number of connections currently checked out by callers."""

    @property
    @abstractmethod
    def num_free(self) -> int:
        """Number of connections idle in the pool, available for immediate use."""

    @property
    @abstractmethod
    def num_pending(self) -> int:
        """Number of callers currently blocked waiting for a connection."""
