"""
pydbc_core.driver_manager — DriverManager: class-level driver registry and
URL-based connection dispatcher.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydbc_core.connection import Connection
    from pydbc_core.driver import Driver


class DriverManager:
    """Class-level registry mapping pydbc URLs to registered :class:`Driver` instances.

    All methods are class methods so the registry is global for the process.
    Use :meth:`clear` in test fixtures to avoid state bleed.
    """

    _drivers: list[Driver] = []

    @classmethod
    def register_driver(cls, driver: Driver) -> None:
        """Append *driver* to the global driver list."""
        cls._drivers.append(driver)

    @classmethod
    def deregister_driver(cls, driver: Driver) -> None:
        """Remove *driver* from the global driver list (no-op if not present)."""
        try:
            cls._drivers.remove(driver)
        except ValueError:
            pass

    @classmethod
    def get_connection(
        cls,
        url: str,
        properties: dict | None = None,
    ) -> Connection:
        """Return a :class:`Connection` for *url* by dispatching to the first
        registered driver whose :meth:`~Driver.accepts_url` returns ``True``.

        Args:
            url:        A pydbc URL (e.g. ``pydbc:sqlite::memory:``).
            properties: Optional driver-specific connection properties.

        Raises:
            ValueError: If no registered driver accepts *url*.
        """
        for driver in cls._drivers:
            if driver.accepts_url(url):
                return driver.connect(url, properties)
        raise ValueError(f"No driver found for URL: {url}")

    @classmethod
    def get_drivers(cls) -> list[Driver]:
        """Return a shallow copy of the registered driver list."""
        return list(cls._drivers)

    @classmethod
    def clear(cls) -> None:
        """Remove all registered drivers (useful in test teardown)."""
        cls._drivers.clear()
