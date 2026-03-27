"""
pydbc_core.prepared_statement — PreparedStatement ABC.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from pydbc_core.statement import Statement

if TYPE_CHECKING:
    from pydbc_core.result_set import ResultSet


class PreparedStatement(Statement):
    """Abstract base class for parameterized SQL execution.

    Extends Statement with parameter-binding methods (1-based indexing)
    and no-argument execute_query / execute_update overrides.
    """

    @abstractmethod
    def set_parameter(self, index: int, value) -> None:
        """Bind *value* to the parameter at 1-based *index*."""

    @abstractmethod
    def set_string(self, index: int, value: str) -> None:
        """Bind a string *value* to the parameter at 1-based *index*."""

    @abstractmethod
    def set_int(self, index: int, value: int) -> None:
        """Bind an int *value* to the parameter at 1-based *index*."""

    @abstractmethod
    def set_float(self, index: int, value: float) -> None:
        """Bind a float *value* to the parameter at 1-based *index*."""

    @abstractmethod
    def set_null(self, index: int) -> None:
        """Bind NULL / None to the parameter at 1-based *index*."""

    @abstractmethod
    def clear_parameters(self) -> None:
        """Clear all bound parameters."""

    @abstractmethod
    def execute_query(self) -> ResultSet:  # type: ignore[override]
        """Execute the prepared query and return a ResultSet."""

    @abstractmethod
    def execute_update(self) -> int:  # type: ignore[override]
        """Execute the prepared update and return the affected row count."""
