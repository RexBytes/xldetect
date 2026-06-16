"""The :class:`Grid` abstraction and cell-value classification.

This module exists to decouple the detection heuristics from ``openpyxl``. The
detectors operate purely on a :class:`Grid` -- a sparse map of occupied cells,
their styles, and merged ranges -- so they can be unit-tested with hand-built
grids and never need a real ``.xlsx`` file. :mod:`xldetect.reader` is the only
place that knows how to turn an ``openpyxl`` worksheet into a :class:`Grid`.

Coordinates are 1-based ``(row, column)`` tuples to match Excel and ``openpyxl``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from numbers import Number

# Cell "kinds" -- a coarse classification used by header detection to decide
# whether a row looks like labels (text) sitting over a body of a different kind.
KIND_EMPTY = "empty"
KIND_TEXT = "text"
KIND_NUMBER = "number"
KIND_BOOL = "bool"
KIND_DATE = "date"


def cell_kind(value: object) -> str:
    """Classify a single cell value into one of the ``KIND_*`` constants.

    Returns:
        - ``KIND_EMPTY`` for ``None`` and strings that are empty or whitespace-only.
        - ``KIND_BOOL`` for :class:`bool` (checked *before* numbers, because
          ``bool`` is a subclass of ``int`` and would otherwise be miscounted).
        - ``KIND_NUMBER`` for any other :class:`numbers.Number` (int, float,
          :class:`~decimal.Decimal`, complex, ...).
        - ``KIND_DATE`` for :class:`datetime.date`, :class:`~datetime.datetime`,
          and :class:`~datetime.time` values.
        - ``KIND_TEXT`` for non-empty strings and any other object type.
    """
    if value is None:
        return KIND_EMPTY
    if isinstance(value, bool):
        return KIND_BOOL
    if isinstance(value, Number):
        return KIND_NUMBER
    if isinstance(value, (datetime, date, time)):
        return KIND_DATE
    if isinstance(value, str):
        return KIND_EMPTY if value.strip() == "" else KIND_TEXT
    return KIND_TEXT


@dataclass
class CellStyle:
    """Formatting cues used as evidence for header detection.

    Only the four cues that reliably distinguish header rows are captured; the
    full ``openpyxl`` style model is intentionally not mirrored here.
    """

    bold: bool = False
    filled: bool = False
    bordered: bool = False
    italic: bool = False

    def is_decorated(self) -> bool:
        """Return ``True`` if any of the four formatting cues is present."""
        return bool(self.bold or self.filled or self.bordered or self.italic)


@dataclass
class Grid:
    """Sparse view of one worksheet's used cells (1-based coordinates).

    Only *occupied* cells appear in ``values``; absent keys are blank. Cells
    inside a merged range are pre-filled with the range's top-left ("anchor")
    value by the reader, so a merged banner counts as occupied across its whole
    span. ``merged`` records the original merge rectangles for reporting.
    """

    values: dict[tuple[int, int], object] = field(default_factory=dict)
    styles: dict[tuple[int, int], CellStyle] = field(default_factory=dict)
    merged: list[tuple[int, int, int, int]] = field(default_factory=list)
    sheet: str = ""

    @property
    def occupied(self) -> set[tuple[int, int]]:
        """Set of ``(row, col)`` coordinates that hold content."""
        return set(self.values.keys())

    @property
    def has_styles(self) -> bool:
        """``True`` if any style information is recorded for this grid."""
        return bool(self.styles)

    def is_occupied(self, row: int, col: int) -> bool:
        """``True`` if ``(row, col)`` holds content."""
        return (row, col) in self.values

    def value_at(self, row: int, col: int) -> object:
        """Return the value at ``(row, col)`` or ``None`` if blank."""
        return self.values.get((row, col))

    def style_at(self, row: int, col: int) -> CellStyle:
        """Return the :class:`CellStyle` at ``(row, col)``, or a default (all-False) style."""
        return self.styles.get((row, col), CellStyle())

    @property
    def max_row(self) -> int:
        """Highest occupied row, or ``0`` for an empty grid."""
        return max((r for r, _ in self.values), default=0)

    @property
    def max_col(self) -> int:
        """Highest occupied column, or ``0`` for an empty grid."""
        return max((c for _, c in self.values), default=0)
