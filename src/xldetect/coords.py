"""Spreadsheet coordinate helpers.

This module exists so the rest of the package can convert between 1-based
``(row, column)`` integer coordinates and Excel A1 notation without importing
``openpyxl`` everywhere. Keeping these conversions in one tiny, dependency-free
module makes them trivial to unit-test and reuse from result objects that should
not pull in the whole reader stack.
"""

from __future__ import annotations


def column_letter(index: int) -> str:
    """Return the Excel column letters for a 1-based column ``index``.

    ``1`` -> ``"A"``, ``26`` -> ``"Z"``, ``27`` -> ``"AA"``, ``702`` -> ``"ZZ"``,
    ``703`` -> ``"AAA"``. Raises :class:`ValueError` for indices below 1.
    """
    if index < 1:
        raise ValueError(f"Column index must be >= 1 (got {index}).")
    letters = ""
    n = index
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def column_index(letters: str) -> int:
    """Return the 1-based column index for Excel column ``letters``.

    Inverse of :func:`column_letter`. ``"A"`` -> ``1``, ``"AA"`` -> ``27``.
    Raises :class:`ValueError` for empty or non-alphabetic input.
    """
    s = letters.strip().upper()
    if not s or not s.isalpha():
        raise ValueError(f"Invalid column letters: {letters!r}")
    n = 0
    for ch in s:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def a1(row: int, col: int) -> str:
    """Return the A1 reference for a 1-based ``(row, col)`` pair, e.g. ``"B3"``."""
    if row < 1 or col < 1:
        raise ValueError(f"Row and column must be >= 1 (got row={row}, col={col}).")
    return f"{column_letter(col)}{row}"


def a1_range(min_row: int, min_col: int, max_row: int, max_col: int) -> str:
    """Return the A1 range string for a rectangle, e.g. ``"B3:F20"``.

    A single-cell rectangle (``min == max`` on both axes) still renders as a
    range (``"B3:B3"``) so the output shape is uniform for downstream parsers.
    """
    return f"{a1(min_row, min_col)}:{a1(max_row, max_col)}"
