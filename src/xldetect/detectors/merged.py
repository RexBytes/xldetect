"""Merged-cell analysis helpers.

This module exists to interpret merged ranges structurally: which merges fall
inside a region, and whether a given row is dominated by a single horizontal
merge (a "banner" -- the classic decorative title bar). The reader is
responsible for *filling* merged areas with their anchor value; these helpers
only inspect the recorded merge rectangles.
"""

from __future__ import annotations

from ..grid import Grid

# A merge rectangle is a 1-based inclusive tuple: (min_row, min_col, max_row, max_col).
MergeRect = tuple[int, int, int, int]


def merged_in_region(
    merged: list[MergeRect], min_row: int, max_row: int, min_col: int, max_col: int
) -> list[MergeRect]:
    """Return the merge rectangles that intersect the given region bounds.

    A merge is included if it overlaps the region at all, even partially, so a
    region never silently drops a merge that straddles its edge.
    """
    out = []
    for m in merged:
        mr0, mc0, mr1, mc1 = m
        if mr1 < min_row or mr0 > max_row or mc1 < min_col or mc0 > max_col:
            continue
        out.append(m)
    return out


def is_banner_row(grid: Grid, row: int, min_col: int, max_col: int) -> bool:
    """Return ``True`` if ``row`` is dominated by a single horizontal merge.

    A banner row is one where a single merged range spans (at least) the full
    ``[min_col, max_col]`` width -- the signature of a decorative title/section
    bar. Because such a merge covers the entire region width, every column in the
    row is part of it, so there is no separate "outside the merge" content to
    check. Returns ``False`` when no merge spans the full width.
    """
    for mr0, mc0, mr1, mc1 in grid.merged:
        if mr0 <= row <= mr1 and mc0 <= min_col and mc1 >= max_col:
            return True
    return False
