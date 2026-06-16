"""Contract tests for merged-cell analysis helpers."""

from __future__ import annotations

from conftest import grid_from_rows

from xldetect.detectors.merged import is_banner_row, merged_in_region
from xldetect.grid import Grid


def test_merged_in_region_includes_overlapping_and_excludes_disjoint():
    merged = [
        (1, 1, 1, 3),   # banner across A1:C1 -- inside
        (5, 5, 6, 6),   # far away -- outside
        (2, 3, 2, 5),   # straddles the right edge -- still included
    ]
    got = merged_in_region(merged, min_row=1, max_row=3, min_col=1, max_col=3)
    assert (1, 1, 1, 3) in got
    assert (2, 3, 2, 5) in got
    assert (5, 5, 6, 6) not in got


def test_merged_in_region_empty():
    assert merged_in_region([], 1, 10, 1, 10) == []


def test_is_banner_row_true_for_full_width_merge():
    # Row 1 is a single merge A1:C1 filled with the title across the width.
    g = Grid(
        values={(1, 1): "Title", (1, 2): "Title", (1, 3): "Title"},
        merged=[(1, 1, 1, 3)],
    )
    assert is_banner_row(g, 1, 1, 3) is True


def test_is_banner_row_false_when_no_merge_spans_width():
    g = grid_from_rows([["a", "b", "c"]])
    assert is_banner_row(g, 1, 1, 3) is False


def test_is_banner_row_false_when_merge_does_not_span_full_width():
    # Merge covers only A1:B1, so it does not span the region width A:C.
    g = Grid(
        values={(1, 1): "T", (1, 2): "T", (1, 3): "extra"},
        merged=[(1, 1, 1, 2)],
    )
    assert is_banner_row(g, 1, 1, 3) is False


def test_is_banner_row_false_on_empty_row():
    g = Grid(values={(2, 1): "x"})
    assert is_banner_row(g, 1, 1, 3) is False
