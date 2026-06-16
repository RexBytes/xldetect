"""Public result types returned by detection.

These dataclasses are the stable, typed surface that downstream code consumes
(autocomplete and type-checking instead of bare dicts). Every type provides a
``to_dict()`` returning only JSON-native values, so a whole
:class:`WorkbookReport` can be serialised with ``json.dumps`` without custom
encoders. All row/column numbers are 1-based and inclusive, matching Excel.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .coords import a1_range


def _jsonable(value: object) -> object:
    """Return ``value`` if JSON-native, else its ``str()`` form.

    Cell values can be datetimes, Decimals, etc. Serialising them as strings
    keeps ``to_dict()`` output ``json.dumps``-safe without losing readability.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


@dataclass
class MergedRegion:
    """A merged cell range with its anchor (top-left) value. 1-based inclusive."""

    min_row: int
    min_col: int
    max_row: int
    max_col: int
    value: object = None

    @property
    def range_a1(self) -> str:
        return a1_range(self.min_row, self.min_col, self.max_row, self.max_col)

    @property
    def n_rows(self) -> int:
        return self.max_row - self.min_row + 1

    @property
    def n_cols(self) -> int:
        return self.max_col - self.min_col + 1

    @property
    def is_multi_row(self) -> bool:
        return self.n_rows > 1

    @property
    def is_multi_col(self) -> bool:
        return self.n_cols > 1

    def to_dict(self) -> dict:
        return {
            "range": self.range_a1,
            "min_row": self.min_row,
            "min_col": self.min_col,
            "max_row": self.max_row,
            "max_col": self.max_col,
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "value": _jsonable(self.value),
        }


@dataclass
class Region:
    """A detected rectangular data region with header and confidence metadata."""

    sheet: str
    min_row: int
    max_row: int
    min_col: int
    max_col: int
    has_header: bool = False
    header_rows: list[int] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    data_start_row: int = 0
    n_data_rows: int = 0
    n_cols: int = 0
    confidence: float = 0.0
    merged_ranges: list[MergedRegion] = field(default_factory=list)
    decorative_rows: list[int] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def range_a1(self) -> str:
        return a1_range(self.min_row, self.min_col, self.max_row, self.max_col)

    @property
    def header_row(self) -> int | None:
        """Bottom-most header row -- the one a single-header consumer should use."""
        return max(self.header_rows) if self.header_rows else None

    def to_dict(self) -> dict:
        return {
            "sheet": self.sheet,
            "range": self.range_a1,
            "min_row": self.min_row,
            "max_row": self.max_row,
            "min_col": self.min_col,
            "max_col": self.max_col,
            "has_header": self.has_header,
            "header_row": self.header_row,
            "header_rows": list(self.header_rows),
            "headers": [_jsonable(h) for h in self.headers],
            "data_start_row": self.data_start_row,
            "n_data_rows": self.n_data_rows,
            "n_cols": self.n_cols,
            "confidence": self.confidence,
            "merged_ranges": [m.to_dict() for m in self.merged_ranges],
            "decorative_rows": list(self.decorative_rows),
            "notes": list(self.notes),
        }


@dataclass
class SheetReport:
    """All regions and merges found on one worksheet."""

    sheet: str
    max_row: int = 0
    max_col: int = 0
    regions: list[Region] = field(default_factory=list)
    decorative_regions: list[Region] = field(default_factory=list)
    merged_ranges: list[MergedRegion] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def n_regions(self) -> int:
        """Number of *tabular* regions (those with at least one data row)."""
        return len(self.regions)

    def to_dict(self) -> dict:
        return {
            "sheet": self.sheet,
            "max_row": self.max_row,
            "max_col": self.max_col,
            "n_regions": self.n_regions,
            "regions": [r.to_dict() for r in self.regions],
            "decorative_regions": [r.to_dict() for r in self.decorative_regions],
            "merged_ranges": [m.to_dict() for m in self.merged_ranges],
            "notes": list(self.notes),
        }


@dataclass
class WorkbookReport:
    """Top-level result for an inspected workbook."""

    path: str
    sheets: list[SheetReport] = field(default_factory=list)

    def iter_regions(self):
        """Yield every :class:`Region` across all sheets, in sheet order."""
        for sheet in self.sheets:
            yield from sheet.regions

    @property
    def n_regions(self) -> int:
        return sum(s.n_regions for s in self.sheets)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "n_sheets": len(self.sheets),
            "n_regions": self.n_regions,
            "sheets": [s.to_dict() for s in self.sheets],
        }
