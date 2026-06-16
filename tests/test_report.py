"""Tests for the human-readable text renderer's branches."""

from __future__ import annotations

from xldetect.models import MergedRegion, Region, SheetReport, WorkbookReport
from xldetect.report import _plural, format_text


def test_plural():
    assert _plural(1, "row") == "1 row"
    assert _plural(0, "row") == "0 rows"
    assert _plural(2, "col") == "2 cols"


def test_format_text_empty_sheet():
    wb = WorkbookReport(path="f.xlsx", sheets=[SheetReport(sheet="S")])
    out = format_text(wb)
    assert "(no data regions detected)" in out


def test_format_text_zero_data_region_renders_none_not_inverted_range():
    # Finding 4: a region with no data rows must not print "data rows 2-1".
    region = Region(
        sheet="S", min_row=1, max_row=1, min_col=1, max_col=2,
        has_header=True, header_rows=[1], headers=["Name", "Age"],
        data_start_row=2, n_data_rows=0, n_cols=2, confidence=0.2,
    )
    wb = WorkbookReport(path="f.xlsx", sheets=[SheetReport(sheet="S", regions=[region])])
    out = format_text(wb)
    assert "data rows: none" in out
    assert "2-1" not in out


def test_format_text_no_header_region():
    region = Region(
        sheet="S", min_row=1, max_row=3, min_col=1, max_col=2,
        has_header=False, data_start_row=1, n_data_rows=3, n_cols=2, confidence=0.5,
    )
    wb = WorkbookReport(path="f.xlsx", sheets=[SheetReport(sheet="S", regions=[region])])
    out = format_text(wb)
    assert "header: none detected" in out


def test_format_text_blank_header_and_decorative_and_merged():
    region = Region(
        sheet="S", min_row=1, max_row=4, min_col=1, max_col=2,
        has_header=True, header_rows=[2], headers=["Name", ""],
        data_start_row=3, n_data_rows=2, n_cols=2, confidence=0.7,
        decorative_rows=[1], merged_ranges=[MergedRegion(1, 1, 1, 2, value="T")],
    )
    wb = WorkbookReport(path="f.xlsx", sheets=[SheetReport(sheet="S", regions=[region])])
    out = format_text(wb)
    assert "<blank>" in out  # blank header label rendered explicitly
    assert "decorative rows skipped: 1" in out
    assert "merged ranges: 1" in out
