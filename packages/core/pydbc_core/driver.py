"""
pydbc_core.driver — Driver ABC.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydbc_core.connection import Connection


class Driver(ABC):
    """Abstract base class for pydbc database drivers."""

    @abstractmethod
    def accepts_url(self, url: str) -> bool:
        """Return True if this driver handles the given pydbc URL."""

    @abstractmethod
    def connect(self, url: str, properties: dict | None = None) -> Connection:
        """Open and return a Connection for the given URL.

        Args:
            url: A pydbc URL (e.g. ``pydbc:sqlite:memory:``).
            properties: Optional driver-specific connection properties.
        """
