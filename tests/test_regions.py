"""Contract tests for region segmentation, including threshold pinning."""

from __future__ import annotations

import pytest

from xldetect.detectors.regions import RawRegion, _split_runs, detect_regions


def test_empty_input_returns_no_regions():
    assert detect_regions(set()) == []


def test_single_cell_is_one_region():
    regions = detect_regions({(3, 4)})
    # cell at row 3, col 4 -> RawRegion(min_row, max_row, min_col, max_col)
    assert regions == [RawRegion(3, 3, 4, 4)]


def test_single_contiguous_block_is_one_region():
    cells = {(r, c) for r in range(1, 4) for c in range(1, 3)}
    assert detect_regions(cells) == [RawRegion(1, 3, 1, 2)]


def test_two_stacked_tables_split_on_default_single_blank_row():
    # rows 1-2 then a blank row 3 then rows 4-5
    cells = {(1, 1), (2, 1), (4, 1), (5, 1)}
    regions = detect_regions(cells)
    assert regions == [RawRegion(1, 2, 1, 1), RawRegion(4, 5, 1, 1)]


def test_single_blank_row_does_not_split_when_threshold_is_two():
    # THRESHOLD PIN: one blank row (gap of 1) must NOT split when min_blank_rows=2.
    cells = {(1, 1), (2, 1), (4, 1), (5, 1)}
    regions = detect_regions(cells, min_blank_rows=2)
    assert regions == [RawRegion(1, 5, 1, 1)]


def test_two_blank_rows_split_when_threshold_is_two():
    # THRESHOLD PIN: gap of 2 blank rows (rows 3,4 blank) splits at min_blank_rows=2.
    cells = {(1, 1), (2, 1), (5, 1), (6, 1)}
    regions = detect_regions(cells, min_blank_rows=2)
    assert regions == [RawRegion(1, 2, 1, 1), RawRegion(5, 6, 1, 1)]


def test_side_by_side_tables_split_on_blank_column():
    # cols 1-2 and cols 4-5 across rows 1-2; col 3 blank
    cells = {(1, 1), (1, 2), (2, 1), (2, 2), (1, 4), (1, 5), (2, 4), (2, 5)}
    regions = detect_regions(cells)
    assert regions == [RawRegion(1, 2, 1, 2), RawRegion(1, 2, 4, 5)]


def test_side_by_side_tables_keep_independent_row_extents():
    # left table rows 1-3, right table rows 1-1 only; bounds must tighten per region
    cells = {(1, 1), (2, 1), (3, 1), (1, 3)}
    regions = detect_regions(cells)
    assert regions == [RawRegion(1, 3, 1, 1), RawRegion(1, 1, 3, 3)]


def test_recursive_split_row_gap_inside_a_column_band():
    # A column band that itself contains a vertical gap must split further.
    # Left col1 rows 1-4 (continuous); right col3 rows 1-1 and 4-4 (gap rows 2-3).
    cells = {(1, 1), (2, 1), (3, 1), (4, 1), (1, 3), (4, 3)}
    regions = detect_regions(cells)
    assert RawRegion(1, 4, 1, 1) in regions
    assert RawRegion(1, 1, 3, 3) in regions
    assert RawRegion(4, 4, 3, 3) in regions
    assert len(regions) == 3


def test_regions_are_sorted_by_row_then_col():
    cells = {(5, 5), (1, 1)}
    regions = detect_regions(cells)
    assert regions == [RawRegion(1, 1, 1, 1), RawRegion(5, 5, 5, 5)]


def test_min_blank_below_one_raises():
    with pytest.raises(ValueError):
        detect_regions({(1, 1), (3, 1)}, min_blank_rows=0)


def test_min_blank_validated_even_on_empty_input():
    # Validation must not be data-dependent: a bad arg is rejected whether or not
    # the sheet has content.
    with pytest.raises(ValueError):
        detect_regions(set(), min_blank_rows=0)
    with pytest.raises(ValueError):
        detect_regions(set(), min_blank_cols=0)


def test_split_runs_basic():
    assert _split_runs([1, 2, 3], 1) == [(1, 3)]
    assert _split_runs([1, 3], 1) == [(1, 1), (3, 3)]
    assert _split_runs([1, 2, 4, 5], 1) == [(1, 2), (4, 5)]
    assert _split_runs([], 1) == []
