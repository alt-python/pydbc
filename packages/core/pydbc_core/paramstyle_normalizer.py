"""
pydbc_core.paramstyle_normalizer — Translate canonical SQL params to any
DB-API 2 paramstyle.

Canonical input conventions
----------------------------
* Positional params  →  ``?`` placeholders  +  tuple/list of values
* Named params       →  ``:name`` placeholders  +  dict of values
* No params          →  ``None``  (treated as empty tuple)

Supported target_paramstyle values
------------------------------------
``qmark``    ``?`` placeholders, tuple  (standard sqlite3)
``format``   ``%s`` placeholders, tuple
``pyformat`` ``%(name)s`` placeholders, dict  (psycopg2 named)
``named``    ``:name`` placeholders, dict  (cx_Oracle named)
``numeric``  ``:1`` ``:2`` … placeholders, tuple  (cx_Oracle numeric)

The named-param regex uses a negative lookbehind ``(?<!:)`` so that
PostgreSQL cast syntax ``created_at::date`` is *never* matched as a
parameter.  This property is exercised by the test suite.
"""

from __future__ import annotations

import re

# Regex that matches :name but NOT ::name (PostgreSQL cast notation).
_NAMED_PARAM_RE = re.compile(r"(?<!:):([a-zA-Z_]\w*)")


class ParamstyleNormalizer:
    """Utility for translating parameterised SQL to a target DB-API paramstyle."""

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @staticmethod
    def normalize(
        sql: str,
        params: tuple | list | dict | None,
        target_paramstyle: str,
    ) -> tuple[str, tuple | dict]:
        """Return *(normalised_sql, normalised_params)* ready for the driver.

        Args:
            sql:               SQL string using canonical ``?`` or ``:name``
                               placeholders.
            params:            Values as a tuple/list (positional) or dict
                               (named).  ``None`` is treated as an empty tuple.
            target_paramstyle: One of ``qmark``, ``format``, ``pyformat``,
                               ``named``, ``numeric``.

        Raises:
            ValueError: If *target_paramstyle* is not recognised.
        """
        if params is None:
            params = ()

        dispatch = {
            "qmark": ParamstyleNormalizer._to_qmark,
            "format": ParamstyleNormalizer._to_format,
            "pyformat": ParamstyleNormalizer._to_pyformat,
            "named": ParamstyleNormalizer._to_named,
            "numeric": ParamstyleNormalizer._to_numeric,
        }

        handler = dispatch.get(target_paramstyle)
        if handler is None:
            raise ValueError(
                f"Unknown target_paramstyle {target_paramstyle!r}. "
                f"Expected one of: {', '.join(dispatch)}"
            )

        return handler(sql, params)

    # ------------------------------------------------------------------ #
    # Private helpers — positional input (tuple / list)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _positional_to_qmark(sql: str, params: tuple | list) -> tuple[str, tuple]:
        """Passthrough — canonical input already uses ``?``."""
        return sql, tuple(params)

    @staticmethod
    def _positional_to_format(sql: str, params: tuple | list) -> tuple[str, tuple]:
        """Convert ``?`` → ``%s``."""
        return sql.replace("?", "%s"), tuple(params)

    @staticmethod
    def _positional_to_pyformat(sql: str, params: tuple | list) -> tuple[str, tuple]:
        """Convert ``?`` → ``%s`` (pyformat uses %s for positional)."""
        return sql.replace("?", "%s"), tuple(params)

    @staticmethod
    def _positional_to_numeric(sql: str, params: tuple | list) -> tuple[str, tuple]:
        """Convert ``?`` → ``:1``, ``:2``, … ."""
        counter = [0]

        def _replacer(_match: re.Match) -> str:
            counter[0] += 1
            return f":{counter[0]}"

        out_sql = re.sub(r"\?", _replacer, sql)
        return out_sql, tuple(params)

    # ------------------------------------------------------------------ #
    # Private helpers — named input (dict)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _named_to_positional(
        sql: str,
        params: dict,
        placeholder: str,
    ) -> tuple[str, tuple]:
        """Generic named→positional conversion.

        Scans *sql* for ``:name`` tokens (in order, with repetition),
        builds the output tuple preserving that order, and replaces each
        ``:name`` occurrence with *placeholder*.
        """
        names = _NAMED_PARAM_RE.findall(sql)
        values = tuple(params[n] for n in names)
        out_sql = _NAMED_PARAM_RE.sub(placeholder, sql)
        return out_sql, values

    @staticmethod
    def _named_to_pyformat(sql: str, params: dict) -> tuple[str, dict]:
        """``:name`` → ``%(name)s``, params dict passthrough."""
        out_sql = _NAMED_PARAM_RE.sub(r"%(\1)s", sql)
        return out_sql, params

    @staticmethod
    def _named_to_numeric(sql: str, params: dict) -> tuple[str, tuple]:
        """Convert ``:name`` → ``:1``, ``:2``, … in scan order."""
        names = _NAMED_PARAM_RE.findall(sql)
        values = tuple(params[n] for n in names)

        counter = [0]

        def _replacer(_match: re.Match) -> str:
            counter[0] += 1
            return f":{counter[0]}"

        out_sql = _NAMED_PARAM_RE.sub(_replacer, sql)
        return out_sql, values

    # ------------------------------------------------------------------ #
    # Target-paramstyle dispatch methods
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_qmark(sql: str, params: tuple | list | dict) -> tuple[str, tuple]:
        if isinstance(params, dict):
            return ParamstyleNormalizer._named_to_positional(sql, params, "?")
        return ParamstyleNormalizer._positional_to_qmark(sql, params)

    @staticmethod
    def _to_format(sql: str, params: tuple | list | dict) -> tuple[str, tuple]:
        if isinstance(params, dict):
            return ParamstyleNormalizer._named_to_positional(sql, params, "%s")
        return ParamstyleNormalizer._positional_to_format(sql, params)

    @staticmethod
    def _to_pyformat(sql: str, params: tuple | list | dict) -> tuple[str, tuple | dict]:
        if isinstance(params, dict):
            return ParamstyleNormalizer._named_to_pyformat(sql, params)
        return ParamstyleNormalizer._positional_to_pyformat(sql, params)

    @staticmethod
    def _to_named(sql: str, params: tuple | list | dict) -> tuple[str, dict]:
        if isinstance(params, dict):
            # Passthrough — already ``:name`` + dict.
            return sql, params
        # Positional → named is not a canonical operation; raise clearly.
        raise ValueError(
            "Cannot convert positional params (tuple/list) to 'named' paramstyle. "
            "Supply a dict with :name placeholders instead."
        )

    @staticmethod
    def _to_numeric(sql: str, params: tuple | list | dict) -> tuple[str, tuple]:
        if isinstance(params, dict):
            return ParamstyleNormalizer._named_to_numeric(sql, params)
        return ParamstyleNormalizer._positional_to_numeric(sql, params)
