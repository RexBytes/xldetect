"""Contract tests for header detection: truth-table corners + threshold pin."""

from __future__ import annotations

from conftest import grid_from_rows

from xldetect.detectors.headers import detect_header, score_header_row
from xldetect.detectors.regions import RawRegion


def _region(rows):
    g = grid_from_rows(rows)
    return g, RawRegion(1, len(rows), 1, max(len(r) for r in rows))


# --- truth-table corners -----------------------------------------------------


def test_confirmed_true_text_header_over_numbers():
    g, r = _region([["Name", "Age"], ["Alice", 30], ["Bob", 25]])
    res = detect_header(g, r)
    assert res.has_header is True
    assert res.headers == ["Name", "Age"]
    assert res.header_rows == [1]


def test_confirmed_false_numeric_block():
    g, r = _region([[1, 2], [3, 4], [5, 6]])
    res = detect_header(g, r)
    assert res.has_header is False
    assert res.headers == []


def test_all_text_block_is_treated_as_header_documents_ambiguity():
    # A block of text over text cannot be distinguished from a true header
    # without content understanding; current contract: treat row 1 as header.
    g, r = _region([["alpha", "beta"], ["gamma", "delta"], ["x", "y"]])
    res = detect_header(g, r)
    assert res.has_header is True
    assert res.headers == ["alpha", "beta"]


def test_adversarial_false_sparse_numeric_row_not_header():
    # A lone numeric cell above numeric data: sparse AND no type distinction.
    g, r = _region([[None, 5, None], [1, 2, 3], [4, 5, 6]])
    res = detect_header(g, r)
    assert res.has_header is False


# --- threshold pinning -------------------------------------------------------


def test_threshold_boundary_is_inclusive_and_pinned():
    # Mixed body so the score lands strictly between 0 and 1.
    g, r = _region([["Name", "City"], ["Alice", 1], ["Bob", 2]])
    s = score_header_row(g, r, 1, 2)
    assert 0.0 < s < 1.0
    # >= comparison: exactly at the score still counts as a header.
    assert detect_header(g, r, threshold=s).has_header is True
    assert detect_header(g, r, threshold=s - 0.01).has_header is True
    assert detect_header(g, r, threshold=s + 0.01).has_header is False


def test_threshold_out_of_range_raises():
    g, r = _region([["a", "b"], [1, 2]])
    import pytest

    with pytest.raises(ValueError):
        detect_header(g, r, threshold=1.5)
    with pytest.raises(ValueError):
        detect_header(g, r, threshold=-0.1)


# --- style cue redistribution ------------------------------------------------


def test_undecorated_style_grid_scores_lower_than_content_only_grid():
    rows = [["Name", "City"], ["Alice", 1], ["Bob", 2]]
    g_content = grid_from_rows(rows, styled=False)
    g_styled = grid_from_rows(rows, styled=True)  # styles present but undecorated
    r = RawRegion(1, 3, 1, 2)
    s_content = score_header_row(g_content, r, 1, 2)
    s_styled = score_header_row(g_styled, r, 1, 2)
    # When styles exist but carry no decoration, the style cue contributes 0,
    # so the styled grid scores strictly lower than the content-only grid.
    assert s_styled < s_content
    # Both still clear the default threshold for this clear header.
    assert detect_header(g_content, r).has_header is True
    assert detect_header(g_styled, r).has_header is True


# --- multi-row headers and label extraction ----------------------------------


def test_two_row_header_detected_labels_from_bottom_row():
    g, r = _region(
        [["Sales", "Sales"], ["Q1", "Q2"], [10, 20], [30, 40]]
    )
    res = detect_header(g, r)
    assert res.header_rows == [1, 2]
    assert res.header_row == 2
    assert res.headers == ["Q1", "Q2"]


def test_header_labels_preserve_blank_columns_as_empty_string():
    g, r = _region([["A", None, "C"], [1, 2, 3], [4, 5, 6]])
    res = detect_header(g, r)
    assert res.has_header is True
    assert res.headers == ["A", "", "C"]


def test_no_header_has_none_header_row():
    g, r = _region([[1, 2], [3, 4]])
    res = detect_header(g, r)
    assert res.header_row is None


def test_score_zero_width_region_is_zero():
    g = grid_from_rows([["a"]])
    # a degenerate region with no columns scores 0 rather than dividing by zero
    assert score_header_row(g, RawRegion(1, 1, 2, 1), 1, 2) == 0.0


def test_secondary_candidate_rejected_when_sparse():
    # row 1 is a clear header; row 2 is all-text but only 1 of 3 columns is
    # populated (a stray annotation), so it is NOT taken as a second header row.
    g, r = _region([["Name", "Age", "City"], ["note", None, None], [1, 2, 3], [4, 5, 6]])
    res = detect_header(g, r)
    assert res.header_rows == [1]


def test_secondary_candidate_rejected_when_empty_row():
    g, r = _region([["Name", "Age"], [None, None], [1, 2], [3, 4]])
    res = detect_header(g, r)
    assert res.header_rows == [1]


def test_secondary_header_capped_at_max_header_rows():
    # Three all-text label rows over numeric data; default max_header_rows=2
    # must stop after two header rows even though row 3 also qualifies.
    g, r = _region(
        [["G", "G"], ["H1", "H2"], ["S1", "S2"], [1, 2], [3, 4]]
    )
    res = detect_header(g, r, max_header_rows=2)
    assert res.header_rows == [1, 2]
