"""
pydbc_core.result_set — ResultSet concrete class.
"""

from __future__ import annotations


class ResultSet:
    """Cursor-based result set returned by query execution.

    Rows are stored as dicts keyed by column name.  Navigation is
    forward-only: call :meth:`next` to advance the cursor, then
    retrieve values with ``get_object`` / ``get_string`` / ``get_int``
    / ``get_float``.

    All data-access methods raise :exc:`RuntimeError` after the
    ResultSet is closed.
    """

    def __init__(self, rows: list[dict], column_names: list[str]) -> None:
        self._rows: list[dict] = rows
        self._column_names: list[str] = column_names
        self._index: int = -1
        self._closed: bool = False

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #

    def next(self) -> bool:
        """Advance the cursor.

        Returns True if the new position is within bounds; False when
        the cursor moves past the last row.
        """
        self._check_open()
        self._index += 1
        return self._index < len(self._rows)

    # ------------------------------------------------------------------ #
    # Value accessors
    # ------------------------------------------------------------------ #

    def _resolve_col(self, col: int | str) -> str:
        """Return the column name for *col* (int is 1-based)."""
        if isinstance(col, int):
            zero_based = col - 1
            if zero_based < 0 or zero_based >= len(self._column_names):
                raise IndexError(
                    f"Column index {col} is out of range "
                    f"(1..{len(self._column_names)})"
                )
            return self._column_names[zero_based]
        return col  # already a name

    def _current_row(self) -> dict:
        """Return the row at the current cursor position."""
        self._check_open()
        if self._index < 0 or self._index >= len(self._rows):
            raise RuntimeError(
                "Cursor is not positioned on a valid row. Call next() first."
            )
        return self._rows[self._index]

    def get_object(self, col: int | str):
        """Return the raw value for *col* in the current row."""
        row = self._current_row()
        col_name = self._resolve_col(col)
        return row[col_name]

    def get_string(self, col: int | str) -> str | None:
        """Return the value for *col* cast to str (None if NULL)."""
        val = self.get_object(col)
        return None if val is None else str(val)

    def get_int(self, col: int | str) -> int | None:
        """Return the value for *col* cast to int (None if NULL)."""
        val = self.get_object(col)
        return None if val is None else int(val)

    def get_float(self, col: int | str) -> float | None:
        """Return the value for *col* cast to float (None if NULL)."""
        val = self.get_object(col)
        return None if val is None else float(val)

    def get_row(self) -> dict:
        """Return the current row as a dict."""
        return self._current_row()

    # ------------------------------------------------------------------ #
    # Bulk / metadata
    # ------------------------------------------------------------------ #

    def get_rows(self) -> list[dict]:
        """Return all rows (does not affect cursor position)."""
        self._check_open()
        return list(self._rows)

    def get_column_names(self) -> list[str]:
        """Return the ordered list of column names."""
        self._check_open()
        return list(self._column_names)

    def get_row_count(self) -> int:
        """Return the total number of rows."""
        self._check_open()
        return len(self._rows)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Close the ResultSet and release row data."""
        self._closed = True

    def is_closed(self) -> bool:
        """Return True if the ResultSet has been closed."""
        return self._closed

    def _check_open(self) -> None:
        if self._closed:
            raise RuntimeError("ResultSet is closed")

    # ------------------------------------------------------------------ #
    # Context manager
    # ------------------------------------------------------------------ #

    def __enter__(self) -> ResultSet:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
