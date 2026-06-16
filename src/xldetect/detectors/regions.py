"""Rectangular data-region segmentation.

This module exists to answer "where are the tables?" using only structural cues
-- no content understanding. A worksheet is decomposed into disjoint rectangular
regions by repeatedly splitting the set of occupied cells along any run of fully
blank rows or columns that is at least ``min_blank_rows`` / ``min_blank_cols``
wide. The split alternates axes recursively until no region can be split on
either axis, which correctly separates stacked tables, side-by-side tables, and
L-shaped arrangements into clean rectangles.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawRegion:
    """A rectangular region as 1-based inclusive bounds, before header analysis."""

    min_row: int
    max_row: int
    min_col: int
    max_col: int

    @property
    def n_rows(self) -> int:
        return self.max_row - self.min_row + 1

    @property
    def n_cols(self) -> int:
        return self.max_col - self.min_col + 1


def _split_runs(indices: list[int], min_blank: int) -> list[tuple[int, int]]:
    """Group a sorted list of unique ints into ``[start, end]`` inclusive runs.

    A new run begins whenever the blank gap between two consecutive present
    indices is at least ``min_blank`` (the gap between ``a`` and ``b`` with
    ``a < b`` is ``b - a - 1`` blanks). ``min_blank`` must be >= 1.
    """
    if min_blank < 1:
        raise ValueError(f"min_blank must be >= 1 (got {min_blank}).")
    if not indices:
        return []
    runs: list[tuple[int, int]] = []
    start = prev = indices[0]
    for idx in indices[1:]:
        if (idx - prev - 1) >= min_blank:
            runs.append((start, prev))
            start = idx
        prev = idx
    runs.append((start, prev))
    return runs


def _segment(
    cells: set[tuple[int, int]], min_blank_rows: int, min_blank_cols: int
) -> list[set[tuple[int, int]]]:
    """Recursively split a cell set into atomic (unsplittable) cell sets."""
    rows = sorted({r for r, _ in cells})
    row_runs = _split_runs(rows, min_blank_rows)
    if len(row_runs) > 1:
        out: list[set[tuple[int, int]]] = []
        for a, b in row_runs:
            out += _segment(
                {(r, c) for (r, c) in cells if a <= r <= b}, min_blank_rows, min_blank_cols
            )
        return out

    cols = sorted({c for _, c in cells})
    col_runs = _split_runs(cols, min_blank_cols)
    if len(col_runs) > 1:
        out = []
        for a, b in col_runs:
            out += _segment(
                {(r, c) for (r, c) in cells if a <= c <= b}, min_blank_rows, min_blank_cols
            )
        return out

    return [cells]


def detect_regions(
    occupied: set[tuple[int, int]],
    *,
    min_blank_rows: int = 1,
    min_blank_cols: int = 1,
) -> list[RawRegion]:
    """Decompose a set of occupied ``(row, col)`` cells into rectangular regions.

    Args:
        occupied: Set of 1-based ``(row, col)`` coordinates that hold content.
        min_blank_rows: Number of consecutive fully blank rows that separates two
            regions vertically. Default ``1`` (a single blank row splits).
        min_blank_cols: Number of consecutive fully blank columns that separates
            two regions horizontally. Default ``1``.

    Returns:
        A list of :class:`RawRegion`, sorted by ``(min_row, min_col)``. Each
        region's bounds are tightened to its own occupied cells, so regions are
        disjoint and every occupied cell belongs to exactly one region. Returns
        an empty list for empty input.
    """
    if not occupied:
        return []
    atoms = _segment(set(occupied), min_blank_rows, min_blank_cols)
    regions = []
    for atom in atoms:
        rs = [r for r, _ in atom]
        cs = [c for _, c in atom]
        regions.append(RawRegion(min(rs), max(rs), min(cs), max(cs)))
    regions.sort(key=lambda r: (r.min_row, r.min_col))
    return regions
