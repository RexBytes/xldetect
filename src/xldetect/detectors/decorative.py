"""Decorative top-row trimming.

This module exists to strip title bars and section labels that sit *above* a
table's real header, because those rows would otherwise be mistaken for the
header by :mod:`xldetect.detectors.headers`. Trimming is deliberately
conservative: it only removes leading rows that look like lone titles or merged
banners, it only trims from the top, and it never removes every row of a region.
Summary/total rows at the *bottom* of a region are not removed -- see
``LIMITATIONS.md`` for why distinguishing a summary row from a data row is left
to the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..grid import Grid
from .merged import is_banner_row
from .regions import RawRegion


@dataclass
class TrimResult:
    """Outcome of :func:`trim_decorative`."""

    region: RawRegion
    removed_rows: list[int] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _logical_count(grid: Grid, row: int, min_col: int, max_col: int) -> int:
    """Count distinct content cells in a row, counting each merge once.

    A merged range that is filled across several columns contributes a single
    logical cell rather than one per spanned column.
    """
    count = 0
    covered: set[int] = set()
    for c in range(min_col, max_col + 1):
        if c in covered or not grid.is_occupied(row, c):
            continue
        merge = None
        for mr0, mc0, mr1, mc1 in grid.merged:
            if mr0 <= row <= mr1 and mc0 <= c <= mc1:
                merge = (mr0, mc0, mr1, mc1)
                break
        if merge is not None:
            _, mc0, _, mc1 = merge
            covered.update(range(mc0, mc1 + 1))
        count += 1
    return count


def trim_decorative(grid: Grid, region: RawRegion) -> TrimResult:
    """Strip leading decorative rows (titles, banners) from a region.

    A leading row is removed when it is either a merged banner spanning the
    region width (see :func:`xldetect.detectors.merged.is_banner_row`) or a
    "lone title" -- a row with at most one logical cell while some lower row in
    the region has two or more. Trimming stops at the first tabular-looking row.
    If every row would be removed, the region is returned unchanged with a note,
    so a region is never trimmed out of existence.
    """
    widths = [
        _logical_count(grid, r, region.min_col, region.max_col)
        for r in range(region.min_row, region.max_row + 1)
    ]
    body_is_wide = any(w >= 2 for w in widths)

    removed: list[int] = []
    top = region.min_row
    while top < region.max_row:
        idx = top - region.min_row
        banner = is_banner_row(grid, top, region.min_col, region.max_col)
        lone_title = body_is_wide and widths[idx] <= 1
        if banner or lone_title:
            removed.append(top)
            top += 1
            continue
        break

    notes: list[str] = []
    if removed:
        notes.append(f"trimmed {len(removed)} decorative row(s) above the table")
    trimmed = RawRegion(top, region.max_row, region.min_col, region.max_col)
    return TrimResult(region=trimmed, removed_rows=removed, notes=notes)
