"""
pydbc_core.generic_db_api_driver — Wraps any PEP 249-compliant module in the
pydbc abstraction hierarchy.

Four concrete classes are provided:

* :class:`GenericDbApiDriver`           — implements :class:`~pydbc_core.driver.Driver`
* :class:`GenericDbApiConnection`       — implements :class:`~pydbc_core.connection.Connection`
* :class:`GenericDbApiStatement`        — implements :class:`~pydbc_core.statement.Statement`
* :class:`GenericDbApiPreparedStatement` — implements :class:`~pydbc_core.prepared_statement.PreparedStatement`

Usage::

    import sqlite3
    from pydbc_core import DriverManager, GenericDbApiDriver

    driver = GenericDbApiDriver(sqlite3, 'pydbc:sqlite:')
    DriverManager.register_driver(driver)
    conn = DriverManager.get_connection('pydbc:sqlite::memory:')
"""

from __future__ import annotations

from pydbc_core.connection import Connection
from pydbc_core.driver import Driver
from pydbc_core.paramstyle_normalizer import ParamstyleNormalizer
from pydbc_core.prepared_statement import PreparedStatement
from pydbc_core.result_set import ResultSet
from pydbc_core.statement import Statement


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


class GenericDbApiDriver(Driver):
    """A :class:`~pydbc_core.driver.Driver` that delegates to any PEP 249 module.

    Args:
        module:     A PEP 249-compliant database module (e.g. ``sqlite3``).
        url_prefix: The URL prefix this driver handles (e.g. ``'pydbc:sqlite:'``).
    """

    def __init__(self, module, url_prefix: str) -> None:
        self._module = module
        self._url_prefix = url_prefix

    def accepts_url(self, url: str) -> bool:
        """Return ``True`` if *url* starts with this driver's prefix."""
        return url.startswith(self._url_prefix)

    def connect(
        self,
        url: str,
        properties: dict | None = None,
    ) -> GenericDbApiConnection:
        """Strip the URL prefix, call ``module.connect``, and return a
        :class:`GenericDbApiConnection`.

        The native URL is the portion of *url* after :attr:`_url_prefix`.
        For example, ``'pydbc:sqlite::memory:'`` with prefix ``'pydbc:sqlite:'``
        yields native URL ``':memory:'``.
        """
        native_url = url[len(self._url_prefix):]
        native_conn = self._module.connect(native_url)
        return GenericDbApiConnection(
            native_conn,
            self._module,
            self._module.paramstyle,
        )


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


class GenericDbApiConnection(Connection):
    """A :class:`~pydbc_core.connection.Connection` wrapping a PEP 249 connection.

    Args:
        conn:       The native PEP 249 connection object.
        module:     The originating PEP 249 module (kept for future extensions).
        paramstyle: The driver's ``paramstyle`` string (e.g. ``'qmark'``).
    """

    def __init__(self, conn, module, paramstyle: str) -> None:
        self._conn = conn
        self._module = module
        self._paramstyle = paramstyle
        self._closed = False

    # -- public attribute accessed by Statement / PreparedStatement --------

    @property
    def paramstyle(self) -> str:
        """The PEP 249 paramstyle of the underlying driver."""
        return self._paramstyle

    # -- Connection interface ----------------------------------------------

    def create_statement(self) -> GenericDbApiStatement:
        """Return a new :class:`GenericDbApiStatement` for this connection."""
        return GenericDbApiStatement(self)

    def prepare_statement(self, sql: str) -> GenericDbApiPreparedStatement:
        """Return a new :class:`GenericDbApiPreparedStatement` for *sql*."""
        return GenericDbApiPreparedStatement(self, sql)

    def set_auto_commit(self, auto_commit: bool) -> None:
        """Set the native connection's ``autocommit`` attribute (Python 3.12+)."""
        self._conn.autocommit = auto_commit

    def commit(self) -> None:
        """Commit the current transaction."""
        self._conn.commit()

    def rollback(self) -> None:
        """Roll back the current transaction."""
        self._conn.rollback()

    def close(self) -> None:
        """Close the native connection."""
        if not self._closed:
            self._conn.close()
            self._closed = True

    def is_closed(self) -> bool:
        """Return ``True`` if :meth:`close` has been called."""
        return self._closed


# ---------------------------------------------------------------------------
# Statement
# ---------------------------------------------------------------------------


class GenericDbApiStatement(Statement):
    """An ad-hoc :class:`~pydbc_core.statement.Statement` backed by a fresh
    cursor per execution.

    Args:
        connection: The parent :class:`GenericDbApiConnection`.
    """

    def __init__(self, connection: GenericDbApiConnection) -> None:
        self._connection = connection
        self._closed = False

    def execute_query(self, sql: str) -> ResultSet:
        """Execute *sql* on a fresh cursor and return a :class:`~pydbc_core.result_set.ResultSet`.

        The SQL is normalised via :class:`~pydbc_core.paramstyle_normalizer.ParamstyleNormalizer`
        (no-param passthrough), then executed.  ``cursor.description`` is
        read *before* ``fetchall()`` — both calls operate on the same cursor.
        """
        norm_sql, norm_params = ParamstyleNormalizer.normalize(
            sql, (), self._connection.paramstyle
        )
        cursor = self._connection._conn.cursor()
        try:
            cursor.execute(norm_sql, norm_params)
            cols = (
                [d[0] for d in cursor.description]
                if cursor.description is not None
                else []
            )
            raw_rows = cursor.fetchall()
        finally:
            cursor.close()
        rows = [dict(zip(cols, row)) for row in raw_rows]
        return ResultSet(rows, cols)

    def execute_update(self, sql: str) -> int:
        """Execute *sql* on a fresh cursor and return the affected row count."""
        norm_sql, norm_params = ParamstyleNormalizer.normalize(
            sql, (), self._connection.paramstyle
        )
        cursor = self._connection._conn.cursor()
        try:
            cursor.execute(norm_sql, norm_params)
            return cursor.rowcount
        finally:
            cursor.close()

    def execute(self, sql: str) -> bool:
        """Execute *sql* and return ``True`` if the result is a ResultSet."""
        norm_sql, norm_params = ParamstyleNormalizer.normalize(
            sql, (), self._connection.paramstyle
        )
        cursor = self._connection._conn.cursor()
        try:
            cursor.execute(norm_sql, norm_params)
            return cursor.description is not None
        finally:
            cursor.close()

    def close(self) -> None:
        """Mark this statement as closed."""
        self._closed = True

    def is_closed(self) -> bool:
        """Return ``True`` if :meth:`close` has been called."""
        return self._closed


# ---------------------------------------------------------------------------
# PreparedStatement
# ---------------------------------------------------------------------------


class GenericDbApiPreparedStatement(PreparedStatement):
    """A parameterized :class:`~pydbc_core.prepared_statement.PreparedStatement`
    backed by a fresh cursor per execution.

    Parameters are stored in a 1-based index dict and converted to a tuple
    (in sorted index order) at execution time before being passed through
    :class:`~pydbc_core.paramstyle_normalizer.ParamstyleNormalizer`.

    Args:
        connection: The parent :class:`GenericDbApiConnection`.
        sql:        The SQL template using canonical ``?`` or ``:name``
                    placeholders.
    """

    def __init__(self, connection: GenericDbApiConnection, sql: str) -> None:
        self._connection = connection
        self._sql = sql
        self._params: dict[int, object] = {}
        self._closed = False

    # -- parameter binding -------------------------------------------------

    def set_parameter(self, index: int, value) -> None:
        """Bind *value* to 1-based parameter *index*."""
        self._params[index] = value

    def set_string(self, index: int, value: str) -> None:
        """Bind a string *value* to 1-based parameter *index*."""
        self.set_parameter(index, value)

    def set_int(self, index: int, value: int) -> None:
        """Bind an int *value* to 1-based parameter *index*."""
        self.set_parameter(index, value)

    def set_float(self, index: int, value: float) -> None:
        """Bind a float *value* to 1-based parameter *index*."""
        self.set_parameter(index, value)

    def set_null(self, index: int) -> None:
        """Bind ``None`` to 1-based parameter *index*."""
        self.set_parameter(index, None)

    def clear_parameters(self) -> None:
        """Remove all bound parameters."""
        self._params.clear()

    # -- internal helpers --------------------------------------------------

    def _get_parameter_list(self) -> tuple:
        """Return parameter values as an ordered tuple (sorted by 1-based index)."""
        return tuple(self._params[i] for i in sorted(self._params))

    # -- execute -----------------------------------------------------------

    def execute_query(self) -> ResultSet:  # type: ignore[override]
        """Execute the prepared query and return a :class:`~pydbc_core.result_set.ResultSet`.

        Parameters are normalised through
        :class:`~pydbc_core.paramstyle_normalizer.ParamstyleNormalizer` using
        the connection's paramstyle.  A fresh cursor is created for this call
        and closed in a ``finally`` block regardless of outcome.
        """
        norm_sql, norm_params = ParamstyleNormalizer.normalize(
            self._sql,
            self._get_parameter_list(),
            self._connection.paramstyle,
        )
        cursor = self._connection._conn.cursor()
        try:
            cursor.execute(norm_sql, norm_params)
            cols = (
                [d[0] for d in cursor.description]
                if cursor.description is not None
                else []
            )
            raw_rows = cursor.fetchall()
        finally:
            cursor.close()
        rows = [dict(zip(cols, row)) for row in raw_rows]
        return ResultSet(rows, cols)

    def execute_update(self) -> int:  # type: ignore[override]
        """Execute the prepared update and return the affected row count.

        A fresh cursor is created for this call and closed in a ``finally``
        block regardless of outcome.
        """
        norm_sql, norm_params = ParamstyleNormalizer.normalize(
            self._sql,
            self._get_parameter_list(),
            self._connection.paramstyle,
        )
        cursor = self._connection._conn.cursor()
        try:
            cursor.execute(norm_sql, norm_params)
            return cursor.rowcount
        finally:
            cursor.close()

    # -- Statement interface (required by ABC) ----------------------------

    def execute(self, sql: str) -> bool:  # type: ignore[override]
        """Not meaningful for PreparedStatement — raises NotImplementedError."""
        raise NotImplementedError(
            "Use execute_query() or execute_update() on a PreparedStatement."
        )

    def close(self) -> None:
        """Mark this prepared statement as closed."""
        self._closed = True

    def is_closed(self) -> bool:
        """Return ``True`` if :meth:`close` has been called."""
        return self._closed
