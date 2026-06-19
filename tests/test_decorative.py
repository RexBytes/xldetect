"""Contract tests for decorative top-row trimming."""

from __future__ import annotations

from conftest import grid_from_rows

from xldetect.detectors.decorative import trim_decorative
from xldetect.detectors.regions import RawRegion
from xldetect.grid import Grid


def test_lone_title_row_is_trimmed():
    # Row 1 has a single cell; rows 2-4 are a 2-col table.
    g = grid_from_rows([["Report", None], ["Name", "Val"], ["a", 1], ["b", 2]])
    region = RawRegion(1, 4, 1, 2)
    res = trim_decorative(g, region)
    assert res.region == RawRegion(2, 4, 1, 2)
    assert res.removed_rows == [1]
    assert res.notes


def test_merged_banner_row_is_trimmed():
    # A1:C1 merged banner above a 3-col table.
    g = Grid(
        values={
            (1, 1): "BANNER", (1, 2): "BANNER", (1, 3): "BANNER",
            (2, 1): "Name", (2, 2): "Age", (2, 3): "City",
            (3, 1): "a", (3, 2): 1, (3, 3): "x",
        },
        merged=[(1, 1, 1, 3)],
    )
    res = trim_decorative(g, RawRegion(1, 3, 1, 3))
    assert res.region == RawRegion(2, 3, 1, 3)
    assert res.removed_rows == [1]


def test_legit_single_column_table_is_not_trimmed():
    # Every row has one logical cell, but there is no wider body, so nothing is
    # decorative -- a 1-column table is a valid table.
    g = grid_from_rows([["Header"], ["a"], ["b"], ["c"]])
    region = RawRegion(1, 4, 1, 1)
    res = trim_decorative(g, region)
    assert res.region == region
    assert res.removed_rows == []


def test_multiple_decorative_rows_trimmed_until_tabular_row():
    g = grid_from_rows(
        [["Title", None], ["Subtitle", None], ["Name", "Val"], ["a", 1]]
    )
    res = trim_decorative(g, RawRegion(1, 4, 1, 2))
    assert res.region == RawRegion(3, 4, 1, 2)
    assert res.removed_rows == [1, 2]


def test_never_trims_region_out_of_existence():
    # All rows look like lone titles; region is returned unchanged (can't strip
    # past the last row).
    g = grid_from_rows([["a", None], ["b", None], ["c", None]])
    region = RawRegion(1, 3, 1, 2)
    res = trim_decorative(g, region)
    # body_is_wide is False (no row has >=2 logical cells), so nothing trimmed.
    assert res.region == region
    assert res.removed_rows == []


def test_all_banner_region_keeps_last_row():
    # Every row is a full-width merged banner. Trimming removes all but the last
    # row (a region is never trimmed out of existence); the surviving header-only
    # row carries no data and is later classified decorative. The last row is
    # never stripped, so removed_rows never covers the whole region.
    g = Grid(
        values={
            (1, 1): "T1", (1, 2): "T1", (1, 3): "T1",
            (2, 1): "T2", (2, 2): "T2", (2, 3): "T2",
            (3, 1): "T3", (3, 2): "T3", (3, 3): "T3",
        },
        merged=[(1, 1, 1, 3), (2, 1, 2, 3), (3, 1, 3, 3)],
    )
    res = trim_decorative(g, RawRegion(1, 3, 1, 3))
    assert res.region == RawRegion(3, 3, 1, 3)  # last row kept
    assert res.removed_rows == [1, 2]
    assert res.region.max_row == 3
