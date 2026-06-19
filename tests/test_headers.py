"""Contract tests for header detection: truth-table corners + threshold pin."""

from __future__ import annotations

from conftest import grid_from_rows

from xldetect.detectors.headers import detect_header, score_header_row
from xldetect.detectors.regions import RawRegion
from xldetect.grid import CellStyle


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


def _grid_with_styles(rows, styles):
    """Build a grid from rows, then attach a {coord: CellStyle} overlay."""
    g = grid_from_rows(rows)
    g.styles.update(styles)
    return g


def test_style_presence_without_decoration_does_not_change_score():
    # A grid that records styles but none are decorated must score identically to
    # a grid with no style records at all -- "style metadata exists" is not
    # "formatting evidence exists".
    rows = [["Name", "City"], ["Alice", 1], ["Bob", 2]]
    g_content = grid_from_rows(rows, styled=False)
    g_styled = grid_from_rows(rows, styled=True)  # records present, none decorated
    r = RawRegion(1, 3, 1, 2)
    assert score_header_row(g_content, r, 1, 2) == score_header_row(g_styled, r, 1, 2)


def test_clean_plain_header_scores_same_as_clean_bold_header():
    # The whole point: absence of formatting must not lower a clear header.
    # Text labels over a fully numeric body -> both columns distinct -> base 1.0.
    rows = [["Qty", "Cost"], [1, 10], [2, 20]]
    r = RawRegion(1, 3, 1, 2)
    g_plain = grid_from_rows(rows)
    g_bold = _grid_with_styles(rows, {(1, 1): CellStyle(bold=True), (1, 2): CellStyle(bold=True)})
    s_plain = score_header_row(g_plain, r, 1, 2)
    s_bold = score_header_row(g_bold, r, 1, 2)
    assert s_plain == s_bold == 1.0  # base already 1.0; bonus capped, never a penalty


def test_style_bonus_lifts_a_borderline_header():
    # Header whose content base is < 1.0 (only one distinct column) gets lifted by
    # a bold contrast against a plain body.
    rows = [["Name", "City"], ["Alice", "NYC"], ["Bob", "LA"]]  # all text -> distinct 0
    r = RawRegion(1, 3, 1, 2)
    g_plain = grid_from_rows(rows)
    g_bold = _grid_with_styles(rows, {(1, 1): CellStyle(bold=True), (1, 2): CellStyle(bold=True)})
    assert score_header_row(g_bold, r, 1, 2) > score_header_row(g_plain, r, 1, 2)


def test_uniform_decoration_earns_no_bonus():
    # Whole table bold -> bold is not discriminating -> bonus is 0.
    rows = [["Name", "City"], ["Alice", "NYC"], ["Bob", "LA"]]
    r = RawRegion(1, 3, 1, 2)
    g_plain = grid_from_rows(rows)
    bold_all = {(rr, cc): CellStyle(bold=True) for rr in range(1, 4) for cc in (1, 2)}
    g_uniform = _grid_with_styles(rows, bold_all)
    assert score_header_row(g_uniform, r, 1, 2) == score_header_row(g_plain, r, 1, 2)


def test_decorated_body_does_not_penalize_plain_header():
    # Finding #2: formatting in the body must not lower a plain header's score.
    rows = [["Name", "City"], ["Alice", "NYC"], ["Bob", "LA"]]
    r = RawRegion(1, 3, 1, 2)
    g_plain = grid_from_rows(rows)
    bold_body = {(rr, cc): CellStyle(bold=True) for rr in (2, 3) for cc in (1, 2)}
    g_bold_body = _grid_with_styles(rows, bold_body)
    assert score_header_row(g_bold_body, r, 1, 2) == score_header_row(g_plain, r, 1, 2)


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


def test_first_data_row_with_blank_optional_column_not_swallowed():
    # Adversarial: a real first data row ("Zoe", blank Score) sits over a numeric
    # Score body. A blank candidate cell must NOT count as type-distinct, or the
    # row gets misread as a second header -- swallowing the record and taking the
    # headers from it. Only the genuine header row 1 may be detected.
    g, r = _region([["Name", "Score"], ["Zoe", None], ["Amy", 90], ["Ben", 80]])
    res = detect_header(g, r)
    assert res.header_rows == [1]
    assert res.headers == ["Name", "Score"]


def test_secondary_header_capped_at_max_header_rows():
    # Three all-text label rows over numeric data; default max_header_rows=2
    # must stop after two header rows even though row 3 also qualifies.
    g, r = _region(
        [["G", "G"], ["H1", "H2"], ["S1", "S2"], [1, 2], [3, 4]]
    )
    res = detect_header(g, r, max_header_rows=2)
    assert res.header_rows == [1, 2]
