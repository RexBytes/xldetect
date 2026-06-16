"""Contract tests for the xlfilldown integration mapping (+ live round-trip)."""

from __future__ import annotations

import sqlite3

import pytest
from conftest import make_workbook

from xldetect.integration import to_xlfilldown_plan, workbook_to_xlfilldown_plans
from xldetect.models import Region, SheetReport, WorkbookReport
from xldetect.orchestrate import inspect_path


def _region(**kw):
    base = dict(sheet="S", min_row=3, max_row=6, min_col=1, max_col=3,
               has_header=True, header_rows=[3], headers=["A", "B", "C"])
    base.update(kw)
    return Region(**base)


def test_clean_full_width_region_has_no_caveats():
    plan = to_xlfilldown_plan(_region(), "f.xlsx", sheet_max_col=3)
    assert plan["file"] == "f.xlsx"
    assert plan["sheet"] == "S"
    assert plan["header_row"] == 3
    assert plan["fill_cols"] == ["A", "B", "C"]
    assert plan["caveats"] == []


def test_no_header_yields_caveat_and_empty_fill_cols():
    plan = to_xlfilldown_plan(
        _region(has_header=False, header_rows=[], headers=[]), "f.xlsx"
    )
    assert plan["fill_cols"] == []
    assert plan["header_row"] == 3  # falls back to region top row
    assert any("no header" in c for c in plan["caveats"])


def test_blank_header_column_yields_caveat():
    plan = to_xlfilldown_plan(_region(headers=["A", "", "C"]), "f.xlsx", sheet_max_col=3)
    assert plan["fill_cols"] == ["A", "C"]
    assert any("blank header" in c for c in plan["caveats"])


def test_column_offset_yields_caveat():
    plan = to_xlfilldown_plan(_region(min_col=2, max_col=4), "f.xlsx", sheet_max_col=4)
    assert any("column B" in c for c in plan["caveats"])


def test_region_narrower_than_sheet_yields_caveat():
    plan = to_xlfilldown_plan(_region(max_col=2, headers=["A", "B"]), "f.xlsx", sheet_max_col=5)
    assert any("out to E" in c for c in plan["caveats"])


def test_multi_region_sheet_adds_shared_caveat_to_each_plan():
    s = SheetReport(
        sheet="S",
        max_col=3,
        regions=[_region(), _region(min_row=10, max_row=12, header_rows=[10])],
    )
    plans = workbook_to_xlfilldown_plans(WorkbookReport(path="f.xlsx", sheets=[s]))
    assert len(plans) == 2
    for plan in plans:
        assert any("2 regions" in c for c in plan["caveats"])


# --- live round-trip against the real xlfilldown package ----------------------


def test_plan_drives_real_xlfilldown_ingest(tmp_path):
    xlf = pytest.importorskip("xlfilldown")
    src = tmp_path / "clean.xlsx"
    make_workbook(
        src,
        {
            "Sheet1": {
                "cells": [
                    {"coord": "A1", "value": "Name"},
                    {"coord": "B1", "value": "Amount"},
                    {"coord": "A2", "value": "Alice"},
                    {"coord": "B2", "value": 10},
                    {"coord": "A3", "value": "Bob"},
                    {"coord": "B3", "value": 20},
                ]
            }
        },
    )
    report = inspect_path(str(src))
    region = next(report.iter_regions())
    plan = to_xlfilldown_plan(region, str(src), sheet_max_col=report.sheets[0].max_col)
    assert plan["caveats"] == []

    db = tmp_path / "out.db"
    xlf.ingest_excel_to_sqlite(
        file=plan["file"],
        sheet=plan["sheet"],
        header_row=plan["header_row"],
        fill_cols=plan["fill_cols"],
        db=str(db),
        table="t",
        if_exists="replace",
    )
    rows = sqlite3.connect(str(db)).execute("SELECT COUNT(*) FROM t").fetchone()[0]
    assert rows == 2
