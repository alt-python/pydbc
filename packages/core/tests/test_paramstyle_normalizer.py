"""
Unit tests for pydbc_core.paramstyle_normalizer.ParamstyleNormalizer.

Each parametrized case is: (sql_in, params_in, target, expected_sql, expected_params).
"""

from __future__ import annotations

import pytest

from pydbc_core.paramstyle_normalizer import ParamstyleNormalizer

N = ParamstyleNormalizer.normalize


# ------------------------------------------------------------------ #
# Parametrized conversion table
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "sql_in, params_in, target, expected_sql, expected_params",
    [
        # ---- qmark → qmark passthrough ----------------------------------
        pytest.param(
            "SELECT * FROM t WHERE id = ?",
            (42,),
            "qmark",
            "SELECT * FROM t WHERE id = ?",
            (42,),
            id="qmark_to_qmark",
        ),
        # ---- named → qmark ----------------------------------------------
        pytest.param(
            "SELECT * FROM t WHERE name = :name",
            {"name": "alice"},
            "qmark",
            "SELECT * FROM t WHERE name = ?",
            ("alice",),
            id="named_to_qmark",
        ),
        # ---- qmark → pyformat -------------------------------------------
        pytest.param(
            "SELECT * FROM t WHERE id = ?",
            (1,),
            "pyformat",
            "SELECT * FROM t WHERE id = %s",
            (1,),
            id="qmark_to_pyformat",
        ),
        # ---- named → pyformat -------------------------------------------
        pytest.param(
            "SELECT * FROM t WHERE name = :name",
            {"name": "bob"},
            "pyformat",
            "SELECT * FROM t WHERE name = %(name)s",
            {"name": "bob"},
            id="named_to_pyformat",
        ),
        # ---- qmark → format ---------------------------------------------
        pytest.param(
            "SELECT * FROM t WHERE id = ?",
            (7,),
            "format",
            "SELECT * FROM t WHERE id = %s",
            (7,),
            id="qmark_to_format",
        ),
        # ---- named → format ---------------------------------------------
        pytest.param(
            "SELECT * FROM t WHERE name = :name",
            {"name": "carol"},
            "format",
            "SELECT * FROM t WHERE name = %s",
            ("carol",),
            id="named_to_format",
        ),
        # ---- named → named passthrough ----------------------------------
        pytest.param(
            "SELECT * FROM t WHERE name = :name",
            {"name": "dave"},
            "named",
            "SELECT * FROM t WHERE name = :name",
            {"name": "dave"},
            id="named_to_named",
        ),
        # ---- named → numeric --------------------------------------------
        pytest.param(
            "SELECT * FROM t WHERE name = :name",
            {"name": "eve"},
            "numeric",
            "SELECT * FROM t WHERE name = :1",
            ("eve",),
            id="named_to_numeric",
        ),
        # ---- repeated named params → value repeated twice ---------------
        pytest.param(
            "SELECT * FROM t WHERE a = :id OR b = :id",
            {"id": 99},
            "qmark",
            "SELECT * FROM t WHERE a = ? OR b = ?",
            (99, 99),
            id="repeated_named_params",
        ),
        # ---- ::date cast preserved (negative lookbehind) ----------------
        pytest.param(
            "SELECT created_at::date FROM t WHERE created_at > :start",
            {"start": "2024-01-01"},
            "qmark",
            "SELECT created_at::date FROM t WHERE created_at > ?",
            ("2024-01-01",),
            id="double_colon_cast_preserved",
        ),
        # ---- empty positional tuple -------------------------------------
        pytest.param(
            "SELECT 1",
            (),
            "qmark",
            "SELECT 1",
            (),
            id="empty_positional",
        ),
        # ---- empty named dict -------------------------------------------
        pytest.param(
            "SELECT 1",
            {},
            "named",
            "SELECT 1",
            {},
            id="empty_named",
        ),
        # ---- None params treated as empty tuple -------------------------
        pytest.param(
            "SELECT 1",
            None,
            "qmark",
            "SELECT 1",
            (),
            id="none_params",
        ),
    ],
)
def test_normalize(sql_in, params_in, target, expected_sql, expected_params):
    out_sql, out_params = N(sql_in, params_in, target)
    assert out_sql == expected_sql
    assert out_params == expected_params


# ------------------------------------------------------------------ #
# Negative tests
# ------------------------------------------------------------------ #

def test_unknown_paramstyle_raises():
    with pytest.raises(ValueError, match="Unknown target_paramstyle"):
        N("SELECT 1", (), "bogus")


def test_positional_to_named_raises():
    """Converting positional tuple to 'named' paramstyle is not supported."""
    with pytest.raises(ValueError):
        N("SELECT ?", (1,), "named")


# ------------------------------------------------------------------ #
# Additional edge cases
# ------------------------------------------------------------------ #

def test_multiple_named_params_in_order():
    """Multi-param named→qmark preserves scan order."""
    sql, params = N(
        "INSERT INTO t (a, b, c) VALUES (:a, :b, :c)",
        {"a": 1, "b": 2, "c": 3},
        "qmark",
    )
    assert sql == "INSERT INTO t (a, b, c) VALUES (?, ?, ?)"
    assert params == (1, 2, 3)


def test_named_to_numeric_multi_params():
    sql, params = N(
        "INSERT INTO t (a, b) VALUES (:a, :b)",
        {"a": "x", "b": "y"},
        "numeric",
    )
    assert sql == "INSERT INTO t (a, b) VALUES (:1, :2)"
    assert params == ("x", "y")


def test_double_colon_only_no_named_param():
    """SQL with only :: casts and no real params must not explode."""
    sql, params = N("SELECT val::text FROM t", {}, "named")
    assert sql == "SELECT val::text FROM t"
    assert params == {}


def test_qmark_to_numeric():
    sql, params = N("SELECT ? + ?", (3, 4), "numeric")
    assert sql == "SELECT :1 + :2"
    assert params == (3, 4)


def test_list_input_treated_as_positional():
    """list input should behave identically to tuple input."""
    sql, params = N("SELECT * FROM t WHERE id = ?", [55], "qmark")
    assert sql == "SELECT * FROM t WHERE id = ?"
    assert params == (55,)
