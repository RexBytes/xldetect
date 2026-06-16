"""Contract tests for result dataclasses and their JSON-safe serialisation."""

from __future__ import annotations

import datetime as dt
import json

from xldetect.models import MergedRegion, Region, SheetReport, WorkbookReport


def test_merged_region_geometry_and_a1():
    m = MergedRegion(1, 1, 1, 3, value="Title")
    assert m.range_a1 == "A1:C1"
    assert m.n_rows == 1
    assert m.n_cols == 3
    assert m.is_multi_row is False
    assert m.is_multi_col is True


def test_merged_region_to_dict_stringifies_non_json_value():
    m = MergedRegion(2, 2, 3, 2, value=dt.date(2026, 1, 1))
    d = m.to_dict()
    assert d["range"] == "B2:B3"
    assert d["value"] == "2026-01-01"  # datetime -> str, JSON-safe
    json.dumps(d)  # must not raise


def test_region_header_row_is_bottom_most():
    r = Region(sheet="S", min_row=1, max_row=5, min_col=1, max_col=2, header_rows=[1, 2])
    assert r.header_row == 2
    assert r.range_a1 == "A1:B5"


def test_region_with_no_header_row():
    r = Region(sheet="S", min_row=1, max_row=5, min_col=1, max_col=2)
    assert r.header_row is None


def test_region_to_dict_is_json_safe_and_has_expected_keys():
    r = Region(
        sheet="S",
        min_row=1,
        max_row=3,
        min_col=1,
        max_col=2,
        has_header=True,
        header_rows=[1],
        headers=["A", "B"],
        data_start_row=2,
        n_data_rows=2,
        n_cols=2,
        confidence=0.9,
    )
    d = r.to_dict()
    assert d["range"] == "A1:B3"
    assert d["header_row"] == 1
    assert d["headers"] == ["A", "B"]
    json.dumps(d)


def test_sheet_report_n_regions_and_workbook_iteration():
    r1 = Region(sheet="S1", min_row=1, max_row=2, min_col=1, max_col=1)
    r2 = Region(sheet="S1", min_row=5, max_row=6, min_col=1, max_col=1)
    r3 = Region(sheet="S2", min_row=1, max_row=2, min_col=1, max_col=1)
    s1 = SheetReport(sheet="S1", regions=[r1, r2])
    s2 = SheetReport(sheet="S2", regions=[r3])
    assert s1.n_regions == 2
    wb = WorkbookReport(path="x.xlsx", sheets=[s1, s2])
    assert wb.n_regions == 3
    assert list(wb.iter_regions()) == [r1, r2, r3]
    json.dumps(wb.to_dict())


def test_empty_workbook_report():
    wb = WorkbookReport(path="x.xlsx", sheets=[])
    assert wb.n_regions == 0
    assert list(wb.iter_regions()) == []
