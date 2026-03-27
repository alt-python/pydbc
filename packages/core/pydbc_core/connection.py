"""
pydbc_core.connection — Connection ABC.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydbc_core.statement import Statement
    from pydbc_core.prepared_statement import PreparedStatement


class Connection(ABC):
    """Abstract base class for pydbc database connections."""

    @abstractmethod
    def create_statement(self) -> Statement:
        """Create and return an ad-hoc Statement."""

    @abstractmethod
    def prepare_statement(self, sql: str) -> PreparedStatement:
        """Create and return a PreparedStatement for *sql*."""

    @abstractmethod
    def set_auto_commit(self, auto_commit: bool) -> None:
        """Enable or disable auto-commit mode."""

    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Roll back the current transaction."""

    @abstractmethod
    def close(self) -> None:
        """Close the connection and release resources."""

    @abstractmethod
    def is_closed(self) -> bool:
        """Return True if the connection has been closed."""

    def __enter__(self) -> Connection:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
