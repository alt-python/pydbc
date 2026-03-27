"""
pydbc_core.statement — Statement ABC.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydbc_core.result_set import ResultSet


class Statement(ABC):
    """Abstract base class for ad-hoc SQL execution."""

    @abstractmethod
    def execute_query(self, sql: str) -> ResultSet:
        """Execute *sql* and return a ResultSet."""

    @abstractmethod
    def execute_update(self, sql: str) -> int:
        """Execute *sql* and return the number of affected rows."""

    @abstractmethod
    def execute(self, sql: str) -> bool:
        """Execute *sql*. Returns True if the result is a ResultSet."""

    @abstractmethod
    def close(self) -> None:
        """Close the statement and release resources."""

    @abstractmethod
    def is_closed(self) -> bool:
        """Return True if the statement has been closed."""

    def __enter__(self) -> Statement:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
