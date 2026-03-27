"""
Unit tests for pydbc_core.result_set.ResultSet.
"""

from __future__ import annotations

import pytest

from pydbc_core.result_set import ResultSet


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

def _make_rs() -> ResultSet:
    """Return a three-row ResultSet for standard tests."""
    rows = [
        {"id": 1, "name": "alice", "score": 9.5},
        {"id": 2, "name": "bob",   "score": 7.0},
        {"id": 3, "name": "carol", "score": 8.25},
    ]
    return ResultSet(rows, ["id", "name", "score"])


# ------------------------------------------------------------------ #
# (a) Cursor advance with next()
# ------------------------------------------------------------------ #

def test_next_advances_cursor():
    rs = _make_rs()
    assert rs.next() is True
    assert rs.next() is True
    assert rs.next() is True
    assert rs.next() is False  # past last row


def test_next_returns_false_immediately_on_empty():
    rs = ResultSet([], [])
    assert rs.next() is False


# ------------------------------------------------------------------ #
# (b) Getters by 1-based int index
# ------------------------------------------------------------------ #

def test_get_object_by_int_index():
    rs = _make_rs()
    rs.next()
    assert rs.get_object(1) == 1
    assert rs.get_object(2) == "alice"
    assert rs.get_object(3) == 9.5


def test_get_string_by_int_index():
    rs = _make_rs()
    rs.next()
    assert rs.get_string(1) == "1"
    assert rs.get_string(2) == "alice"


def test_get_int_by_int_index():
    rs = _make_rs()
    rs.next()
    assert rs.get_int(1) == 1


def test_get_float_by_int_index():
    rs = _make_rs()
    rs.next()
    assert rs.get_float(3) == pytest.approx(9.5)


# ------------------------------------------------------------------ #
# (c) Getters by column name string
# ------------------------------------------------------------------ #

def test_get_object_by_column_name():
    rs = _make_rs()
    rs.next()
    assert rs.get_object("id") == 1
    assert rs.get_object("name") == "alice"


def test_get_string_by_column_name():
    rs = _make_rs()
    rs.next()
    assert rs.get_string("name") == "alice"


def test_get_int_by_column_name():
    rs = _make_rs()
    rs.next()
    assert rs.get_int("id") == 1


def test_get_float_by_column_name():
    rs = _make_rs()
    rs.next()
    assert rs.get_float("score") == pytest.approx(9.5)


# ------------------------------------------------------------------ #
# (d) get_row() at current cursor
# ------------------------------------------------------------------ #

def test_get_row_returns_current_row():
    rs = _make_rs()
    rs.next()  # row 0
    assert rs.get_row() == {"id": 1, "name": "alice", "score": 9.5}
    rs.next()  # row 1
    assert rs.get_row() == {"id": 2, "name": "bob", "score": 7.0}


def test_get_row_before_next_raises():
    rs = _make_rs()
    with pytest.raises(RuntimeError):
        rs.get_row()


# ------------------------------------------------------------------ #
# (e) get_rows() returns all rows
# ------------------------------------------------------------------ #

def test_get_rows_returns_all():
    rs = _make_rs()
    rows = rs.get_rows()
    assert len(rows) == 3
    assert rows[0]["name"] == "alice"
    assert rows[2]["name"] == "carol"


def test_get_rows_does_not_affect_cursor():
    rs = _make_rs()
    rs.next()
    rs.get_rows()          # should not move cursor
    assert rs.get_row() == {"id": 1, "name": "alice", "score": 9.5}


def test_get_rows_empty():
    rs = ResultSet([], [])
    assert rs.get_rows() == []


# ------------------------------------------------------------------ #
# (f) get_row_count() and get_column_names()
# ------------------------------------------------------------------ #

def test_get_row_count():
    rs = _make_rs()
    assert rs.get_row_count() == 3


def test_get_column_names():
    rs = _make_rs()
    assert rs.get_column_names() == ["id", "name", "score"]


# ------------------------------------------------------------------ #
# (g) is_closed() lifecycle
# ------------------------------------------------------------------ #

def test_is_closed_initially_false():
    rs = _make_rs()
    assert rs.is_closed() is False


def test_is_closed_after_close():
    rs = _make_rs()
    rs.close()
    assert rs.is_closed() is True


# ------------------------------------------------------------------ #
# (h) Accessing rows after close() raises RuntimeError
# ------------------------------------------------------------------ #

def test_next_after_close_raises():
    rs = _make_rs()
    rs.close()
    with pytest.raises(RuntimeError, match="ResultSet is closed"):
        rs.next()


def test_get_object_after_close_raises():
    rs = _make_rs()
    rs.next()
    rs.close()
    with pytest.raises(RuntimeError, match="ResultSet is closed"):
        rs.get_object(1)


def test_get_rows_after_close_raises():
    rs = _make_rs()
    rs.close()
    with pytest.raises(RuntimeError, match="ResultSet is closed"):
        rs.get_rows()


def test_get_row_count_after_close_raises():
    rs = _make_rs()
    rs.close()
    with pytest.raises(RuntimeError, match="ResultSet is closed"):
        rs.get_row_count()


def test_get_column_names_after_close_raises():
    rs = _make_rs()
    rs.close()
    with pytest.raises(RuntimeError, match="ResultSet is closed"):
        rs.get_column_names()


# ------------------------------------------------------------------ #
# (i) Empty ResultSet
# ------------------------------------------------------------------ #

def test_empty_next_returns_false():
    rs = ResultSet([], [])
    assert rs.next() is False


def test_empty_get_rows():
    rs = ResultSet([], [])
    assert rs.get_rows() == []


def test_empty_get_row_count():
    rs = ResultSet([], [])
    assert rs.get_row_count() == 0


def test_empty_column_names():
    rs = ResultSet([], [])
    assert rs.get_column_names() == []


# ------------------------------------------------------------------ #
# (j) Context manager closes the ResultSet
# ------------------------------------------------------------------ #

def test_context_manager_closes_on_exit():
    rs = _make_rs()
    with rs:
        assert rs.is_closed() is False
    assert rs.is_closed() is True


def test_context_manager_closes_on_exception():
    rs = _make_rs()
    with pytest.raises(ValueError):
        with rs:
            raise ValueError("boom")
    assert rs.is_closed() is True


# ------------------------------------------------------------------ #
# Negative tests — out-of-range column index
# ------------------------------------------------------------------ #

def test_out_of_range_int_index_raises():
    rs = _make_rs()
    rs.next()
    with pytest.raises(IndexError):
        rs.get_object(99)


def test_zero_index_raises():
    rs = _make_rs()
    rs.next()
    with pytest.raises(IndexError):
        rs.get_object(0)


def test_negative_index_raises():
    rs = _make_rs()
    rs.next()
    with pytest.raises(IndexError):
        rs.get_object(-1)


# ------------------------------------------------------------------ #
# Negative tests — NULL values
# ------------------------------------------------------------------ #

def test_get_string_null_returns_none():
    rs = ResultSet([{"val": None}], ["val"])
    rs.next()
    assert rs.get_string("val") is None


def test_get_int_null_returns_none():
    rs = ResultSet([{"val": None}], ["val"])
    rs.next()
    assert rs.get_int("val") is None


def test_get_float_null_returns_none():
    rs = ResultSet([{"val": None}], ["val"])
    rs.next()
    assert rs.get_float("val") is None
