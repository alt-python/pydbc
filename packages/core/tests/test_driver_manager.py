"""
tests/test_driver_manager.py — Unit tests for DriverManager.

All tests use the `clean_manager` fixture to guarantee a clean driver
registry before *and* after each test so no state bleeds between runs.
"""

from __future__ import annotations

import pytest

from pydbc_core import DriverManager
from pydbc_core.connection import Connection
from pydbc_core.driver import Driver
from pydbc_core.statement import Statement
from pydbc_core.prepared_statement import PreparedStatement
from pydbc_core.result_set import ResultSet


# ---------------------------------------------------------------------------
# Minimal concrete stubs for testing
# ---------------------------------------------------------------------------


class DummyConnection(Connection):
    """Stub connection that does nothing."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._closed = False

    def create_statement(self) -> Statement:
        raise NotImplementedError

    def prepare_statement(self, sql: str) -> PreparedStatement:
        raise NotImplementedError

    def set_auto_commit(self, auto_commit: bool) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        self._closed = True

    def is_closed(self) -> bool:
        return self._closed


class DummyDriver(Driver):
    """Stub driver that accepts URLs starting with 'pydbc:dummy:'."""

    PREFIX = "pydbc:dummy:"

    def __init__(self) -> None:
        self.connect_calls: list[str] = []

    def accepts_url(self, url: str) -> bool:
        return url.startswith(self.PREFIX)

    def connect(self, url: str, properties: dict | None = None) -> Connection:
        self.connect_calls.append(url)
        return DummyConnection(url)


class NeverAcceptsDriver(Driver):
    """Stub driver that never accepts any URL."""

    def accepts_url(self, url: str) -> bool:
        return False

    def connect(self, url: str, properties: dict | None = None) -> Connection:
        raise AssertionError("connect() should never be called on NeverAcceptsDriver")


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_manager():
    """Clear DriverManager registry before and after every test."""
    DriverManager.clear()
    yield
    DriverManager.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRegisterAndGetDrivers:
    def test_register_adds_driver(self):
        driver = DummyDriver()
        DriverManager.register_driver(driver)
        assert driver in DriverManager.get_drivers()

    def test_get_drivers_returns_copy(self):
        driver = DummyDriver()
        DriverManager.register_driver(driver)
        drivers = DriverManager.get_drivers()
        drivers.clear()
        # Mutating the returned list must not affect the registry.
        assert driver in DriverManager.get_drivers()

    def test_register_multiple_drivers(self):
        d1, d2 = DummyDriver(), DummyDriver()
        DriverManager.register_driver(d1)
        DriverManager.register_driver(d2)
        assert len(DriverManager.get_drivers()) == 2


class TestDeregisterDriver:
    def test_deregister_removes_driver(self):
        driver = DummyDriver()
        DriverManager.register_driver(driver)
        DriverManager.deregister_driver(driver)
        assert driver not in DriverManager.get_drivers()

    def test_deregister_nonexistent_is_noop(self):
        driver = DummyDriver()
        # Should not raise even though driver was never registered.
        DriverManager.deregister_driver(driver)


class TestGetConnection:
    def test_get_connection_dispatches_to_accepting_driver(self):
        driver = DummyDriver()
        DriverManager.register_driver(driver)
        url = "pydbc:dummy:test_db"
        conn = DriverManager.get_connection(url)
        assert isinstance(conn, DummyConnection)
        assert driver.connect_calls == [url]

    def test_get_connection_uses_first_accepting_driver(self):
        d1 = DummyDriver()
        d2 = DummyDriver()
        DriverManager.register_driver(d1)
        DriverManager.register_driver(d2)
        DriverManager.get_connection("pydbc:dummy:x")
        assert d1.connect_calls == ["pydbc:dummy:x"]
        assert d2.connect_calls == []

    def test_get_connection_skips_non_accepting_drivers(self):
        never = NeverAcceptsDriver()
        dummy = DummyDriver()
        DriverManager.register_driver(never)
        DriverManager.register_driver(dummy)
        conn = DriverManager.get_connection("pydbc:dummy:db")
        assert isinstance(conn, DummyConnection)

    def test_get_connection_raises_value_error_for_unknown_url(self):
        url = "pydbc:notexist:foo"
        with pytest.raises(ValueError) as exc_info:
            DriverManager.get_connection(url)
        assert url in str(exc_info.value)

    def test_get_connection_error_message_contains_url(self):
        url = "pydbc:notexist:foo"
        with pytest.raises(ValueError, match="pydbc:notexist:foo"):
            DriverManager.get_connection(url)

    def test_get_connection_with_properties(self):
        driver = DummyDriver()
        DriverManager.register_driver(driver)
        # Properties are passed through without error.
        conn = DriverManager.get_connection(
            "pydbc:dummy:db", {"user": "alice", "password": "secret"}
        )
        assert isinstance(conn, DummyConnection)


class TestClear:
    def test_clear_empties_driver_list(self):
        DriverManager.register_driver(DummyDriver())
        DriverManager.clear()
        assert DriverManager.get_drivers() == []

    def test_clear_then_get_connection_raises(self):
        driver = DummyDriver()
        DriverManager.register_driver(driver)
        DriverManager.clear()
        with pytest.raises(ValueError):
            DriverManager.get_connection("pydbc:dummy:db")
