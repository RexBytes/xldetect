"""Confidence-formula pinning and end-to-end inspection on real workbooks."""

from __future__ import annotations

import pytest
from conftest import grid_from_rows, make_workbook

from xldetect.detectors.headers import HeaderResult
from xldetect.detectors.regions import RawRegion
from xldetect.orchestrate import inspect_path, region_confidence


# --- confidence formula (pinned to the documented weights) -------------------


def _full_grid(rows):
    g = grid_from_rows(rows)
    return g, RawRegion(1, len(rows), 1, max(len(r) for r in rows))


def test_confidence_clean_table():
    g, r = _full_grid([["Name", "Age"], ["Alice", 1], ["Bob", 2]])
    h = HeaderResult(has_header=True, header_rows=[1], headers=["Name", "Age"], score=0.8)
    # 0.40*0.8 + 0.35*1.0 + 0.25*1.0 = 0.92
    assert region_confidence(g, r, h, data_start_row=2) == 0.92


def test_confidence_single_column_gets_degeneracy_penalty():
    g, r = _full_grid([["H"], ["a"], ["b"]])
    h = HeaderResult(has_header=True, header_rows=[1], headers=["H"], score=0.8)
    # base 0.92, halved because width < 2 -> 0.46
    assert region_confidence(g, r, h, data_start_row=2) == 0.46


def test_confidence_without_header_uses_flat_component():
    g, r = _full_grid([["a", "b"], ["c", "d"], ["e", "f"]])
    h = HeaderResult(has_header=False)
    # 0.40*0.30 + 0.35*1.0 + 0.25*1.0 = 0.72
    assert region_confidence(g, r, h, data_start_row=1) == 0.72


def test_confidence_drops_with_irregular_rows():
    g = grid_from_rows([["a", "b"], [1, 2], [3, None]])
    r = RawRegion(1, 3, 1, 2)
    h = HeaderResult(has_header=True, header_rows=[1], headers=["a", "b"], score=0.8)
    # fill 5/6, regularity 0.5 -> 0.40*0.8 + 0.35*(5/6) + 0.25*0.5 = 0.737
    assert region_confidence(g, r, h, data_start_row=2) == 0.737


# --- end-to-end --------------------------------------------------------------


@pytest.fixture
def messy_workbook(tmp_path):
    path = tmp_path / "messy.xlsx"
    make_workbook(
        path,
        {
            "Data": {
                "cells": [
                    {"coord": "A1", "value": "Quarterly Report"},
                    {"coord": "A3", "value": "Name", "bold": True},
                    {"coord": "B3", "value": "Region", "bold": True},
                    {"coord": "C3", "value": "Sales", "bold": True},
                    {"coord": "A4", "value": "Alice"},
                    {"coord": "B4", "value": "North"},
                    {"coord": "C4", "value": 100},
                    {"coord": "A5", "value": "Bob"},
                    {"coord": "B5", "value": "South"},
                    {"coord": "C5", "value": 200},
                    # second table, lower
                    {"coord": "A8", "value": "Product"},
                    {"coord": "B8", "value": "Qty"},
                    {"coord": "A9", "value": "Widget"},
                    {"coord": "B9", "value": 5},
                ],
                "merges": ["A1:C1"],
            }
        },
    )
    return str(path)


def test_inspect_detects_multiple_regions(messy_workbook):
    report = inspect_path(messy_workbook)
    assert len(report.sheets) == 1
    sheet = report.sheets[0]
    # two real data tables; the separated banner is classified decorative, not tabular
    assert sheet.n_regions == 2
    assert len(sheet.decorative_regions) == 1
    assert sheet.decorative_regions[0].range_a1 == "A1:C1"
    assert all(r.n_data_rows >= 1 for r in sheet.regions)
    assert len(sheet.merged_ranges) == 1
    # the skip is surfaced to humans via a sheet note
    assert any("decorative" in n for n in sheet.notes)


def test_inspect_finds_the_real_table_with_header(messy_workbook):
    report = inspect_path(messy_workbook)
    tables = [r for r in report.iter_regions() if r.has_header and r.n_data_rows >= 2]
    main = next(r for r in tables if r.headers == ["Name", "Region", "Sales"])
    assert main.range_a1 == "A3:C5"
    assert main.header_row == 3
    assert main.data_start_row == 4
    assert main.confidence > 0.8


def test_inspect_second_table_detected(messy_workbook):
    report = inspect_path(messy_workbook)
    second = next(r for r in report.iter_regions() if r.headers == ["Product", "Qty"])
    assert second.range_a1 == "A8:B9"


def test_inspect_sheet_selection_and_unknown_sheet(tmp_path):
    path = tmp_path / "multi.xlsx"
    make_workbook(
        path,
        {
            "First": {"cells": [{"coord": "A1", "value": "x"}]},
            "Second": {"cells": [{"coord": "A1", "value": "y"}]},
        },
    )
    report = inspect_path(str(path), sheets=["Second"])
    assert [s.sheet for s in report.sheets] == ["Second"]
    with pytest.raises(ValueError):
        inspect_path(str(path), sheets=["Nope"])


def test_inspect_empty_sheet_has_no_regions(tmp_path):
    path = tmp_path / "empty.xlsx"
    make_workbook(path, {"Blank": {"cells": []}})
    report = inspect_path(str(path))
    assert report.sheets[0].n_regions == 0


def test_zero_data_region_excluded_and_recoverable_in_decorative(tmp_path):
    # A header-only block (no data rows) is non-tabular: kept out of regions but
    # available under decorative_regions.
    path = tmp_path / "hdr_only.xlsx"
    make_workbook(
        path,
        {"S": {"cells": [
            {"coord": "A1", "value": "Name", "bold": True},
            {"coord": "B1", "value": "Age", "bold": True},
        ]}},
    )
    sheet = inspect_path(str(path)).sheets[0]
    assert sheet.n_regions == 0
    assert len(sheet.decorative_regions) == 1
    assert sheet.decorative_regions[0].range_a1 == "A1:B1"


def test_decorative_regions_do_not_produce_xlfilldown_plans(messy_workbook):
    from xldetect.integration import workbook_to_xlfilldown_plans

    report = inspect_path(messy_workbook)
    plans = workbook_to_xlfilldown_plans(report)
    # only the two real tables, never the banner
    assert len(plans) == 2
    assert all(p["header_row"] in (3, 8) for p in plans)
