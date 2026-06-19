"""Tests for the openpyxl -> Grid boundary."""

from __future__ import annotations

from conftest import make_workbook

from xldetect.grid import CellStyle
from xldetect.reader import load_grids


def _grid(path, sheet="Sheet1"):
    return load_grids(str(path))[sheet]


def test_blank_and_whitespace_cells_are_omitted(tmp_path):
    path = tmp_path / "b.xlsx"
    make_workbook(
        path,
        {"Sheet1": {"cells": [
            {"coord": "A1", "value": "x"},
            {"coord": "B1", "value": "   "},   # whitespace only -> blank
            {"coord": "C1", "value": None},     # explicit None -> blank
        ]}},
    )
    g = _grid(path)
    assert g.occupied == {(1, 1)}


def test_styles_extracted(tmp_path):
    path = tmp_path / "s.xlsx"
    make_workbook(
        path,
        {"Sheet1": {"cells": [
            {"coord": "A1", "value": "bold", "bold": True},
            {"coord": "B1", "value": "fill", "fill": True},
            {"coord": "C1", "value": "border", "border": True},
            {"coord": "D1", "value": "plain"},
        ]}},
    )
    g = _grid(path)
    assert g.style_at(1, 1).bold is True
    assert g.style_at(1, 2).filled is True
    assert g.style_at(1, 3).bordered is True
    assert g.style_at(1, 4) == CellStyle()  # no decoration


def test_merged_area_is_filled_with_anchor_value(tmp_path):
    path = tmp_path / "m.xlsx"
    make_workbook(
        path,
        {"Sheet1": {
            "cells": [{"coord": "A1", "value": "Banner"}],
            "merges": ["A1:C1"],
        }},
    )
    g = _grid(path)
    # all three merged cells are occupied with the anchor value
    assert g.value_at(1, 1) == "Banner"
    assert g.value_at(1, 2) == "Banner"
    assert g.value_at(1, 3) == "Banner"
    assert (1, 1, 1, 3) in g.merged


def test_empty_merged_range_adds_no_values(tmp_path):
    path = tmp_path / "em.xlsx"
    make_workbook(
        path,
        {"Sheet1": {"cells": [], "merges": ["A1:C1"]}},
    )
    g = _grid(path)
    assert g.occupied == set()           # anchor is empty -> nothing filled
    assert (1, 1, 1, 3) in g.merged      # but the merge is still recorded


def test_load_grids_unknown_sheet_raises(tmp_path):
    path = tmp_path / "u.xlsx"
    make_workbook(path, {"Sheet1": {"cells": [{"coord": "A1", "value": "x"}]}})
    import pytest

    with pytest.raises(ValueError):
        load_grids(str(path), sheets=["Ghost"])


def test_load_grids_corrupt_file_raises_valueerror(tmp_path):
    # A non-xlsx file (plain text with an .xlsx name) must surface as a clean
    # ValueError, not a raw zipfile.BadZipFile / InvalidFileException traceback.
    import pytest

    bad = tmp_path / "fake.xlsx"
    bad.write_text("this is not an excel file")
    with pytest.raises(ValueError):
        load_grids(str(bad))


def test_load_grids_missing_file_raises_valueerror(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        load_grids(str(tmp_path / "nope.xlsx"))


def test_load_grids_zip_without_content_types_raises_valueerror(tmp_path):
    # A structurally-valid zip with no [Content_Types].xml -- e.g. a plain .zip
    # renamed to .xlsx. openpyxl raises a raw KeyError here; load_grids must
    # normalise it to ValueError like every other "wrong format" input, not leak
    # a LookupError traceback to the caller / CLI.
    import zipfile

    import pytest

    bad = tmp_path / "renamed.xlsx"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("data/readme.txt", "just a renamed zip")
    with pytest.raises(ValueError):
        load_grids(str(bad))


def test_load_grids_corrupt_content_types_raises_valueerror(tmp_path):
    # A zip whose [Content_Types].xml is malformed -- a truncated/corrupt Office
    # file. openpyxl raises xml.etree's ParseError (a SyntaxError); load_grids
    # must normalise it to ValueError.
    import zipfile

    import pytest

    bad = tmp_path / "corrupt.xlsx"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("[Content_Types].xml", "<Types><broken")
    with pytest.raises(ValueError):
        load_grids(str(bad))
