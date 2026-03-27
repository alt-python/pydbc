"""
pydbc_core.named_parameter_data_source — NamedParameterDataSource: a DataSource
subclass with template methods that accept :paramName SQL and a dict of values.

The connection lifecycle is managed internally: both :meth:`query` and
:meth:`update` open a connection, execute the statement, and close the
connection before returning.  ResultSet data is safe to use after the
connection closes because :class:`~pydbc_core.result_set.ResultSet` stores
rows eagerly in memory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydbc_core.data_source import DataSource
from pydbc_core.paramstyle_normalizer import ParamstyleNormalizer

if TYPE_CHECKING:
    from pydbc_core.result_set import ResultSet


class NamedParameterDataSource(DataSource):
    """DataSource that executes named-parameter SQL using :paramName syntax.

    Example::

        ds = NamedParameterDataSource('pydbc:sqlite::memory:')
        rs = ds.query('SELECT name FROM users WHERE id = :id', {'id': 1})
        while rs.next():
            print(rs.get_string('name'))

        count = ds.update(
            'INSERT INTO users (name) VALUES (:name)',
            {'name': 'Alice'},
        )
    """

    def query(self, sql: str, params: dict) -> ResultSet:
        """Execute a SELECT *sql* with named *params* and return a ResultSet.

        The connection is opened, the query executed, and the connection
        closed before this method returns.  The returned ResultSet is fully
        materialised in memory and remains usable indefinitely.

        Args:
            sql:    SQL string using ``:name`` placeholders.
            params: Parameter dict mapping placeholder names to values.
                    Pass an empty dict ``{}`` for parameter-free SQL.

        Returns:
            A :class:`~pydbc_core.result_set.ResultSet` containing all rows.
        """
        qmark_sql, values = ParamstyleNormalizer.normalize(sql, params, "qmark")
        with self.get_connection() as conn:
            pstmt = conn.prepare_statement(qmark_sql)
            for i, v in enumerate(values, 1):
                pstmt.set_parameter(i, v)
            return pstmt.execute_query()

    def update(self, sql: str, params: dict) -> int:
        """Execute an INSERT/UPDATE/DELETE *sql* with named *params*.

        The transaction is committed before the connection is closed so that
        changes are visible to subsequent calls.

        Args:
            sql:    SQL string using ``:name`` placeholders.
            params: Parameter dict mapping placeholder names to values.
                    Pass an empty dict ``{}`` for parameter-free SQL.

        Returns:
            Number of rows affected.
        """
        qmark_sql, values = ParamstyleNormalizer.normalize(sql, params, "qmark")
        with self.get_connection() as conn:
            pstmt = conn.prepare_statement(qmark_sql)
            for i, v in enumerate(values, 1):
                pstmt.set_parameter(i, v)
            row_count = pstmt.execute_update()
            conn.commit()
            return row_count
