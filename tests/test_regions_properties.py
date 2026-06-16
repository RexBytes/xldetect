"""Property-based tests for region segmentation invariants.

These pin the structural guarantees of :func:`detect_regions` against random
occupied-cell sets: every occupied cell lands in exactly one region, and the
detected region bounding boxes never overlap. Configuration (the blank-gap
thresholds) is passed explicitly so a falsifying example points squarely at the
segmentation logic rather than at defaults.
"""

from __future__ import annotations

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from xldetect.detectors.regions import detect_regions  # noqa: E402

cells_strategy = st.sets(
    st.tuples(st.integers(min_value=1, max_value=12), st.integers(min_value=1, max_value=12)),
    min_size=0,
    max_size=40,
)


def _contains(region, r, c):
    return region.min_row <= r <= region.max_row and region.min_col <= c <= region.max_col


def _boxes_overlap(a, b):
    return not (
        a.max_row < b.min_row
        or a.min_row > b.max_row
        or a.max_col < b.min_col
        or a.min_col > b.max_col
    )


@given(cells=cells_strategy, mbr=st.integers(1, 3), mbc=st.integers(1, 3))
@settings(max_examples=300)
def test_every_occupied_cell_belongs_to_exactly_one_region(cells, mbr, mbc):
    regions = detect_regions(cells, min_blank_rows=mbr, min_blank_cols=mbc)
    for (r, c) in cells:
        owners = [reg for reg in regions if _contains(reg, r, c)]
        assert len(owners) == 1


@given(cells=cells_strategy, mbr=st.integers(1, 3), mbc=st.integers(1, 3))
@settings(max_examples=300)
def test_region_bounding_boxes_never_overlap(cells, mbr, mbc):
    regions = detect_regions(cells, min_blank_rows=mbr, min_blank_cols=mbc)
    for i in range(len(regions)):
        for j in range(i + 1, len(regions)):
            assert not _boxes_overlap(regions[i], regions[j])


@given(cells=cells_strategy)
@settings(max_examples=100)
def test_huge_threshold_collapses_to_single_region(cells):
    # With a gap threshold larger than the sheet, nothing can separate -> one region.
    regions = detect_regions(cells, min_blank_rows=99, min_blank_cols=99)
    assert len(regions) == (1 if cells else 0)


@given(cells=cells_strategy, mbr=st.integers(1, 3), mbc=st.integers(1, 3))
@settings(max_examples=200)
def test_region_bounds_are_tight(cells, mbr, mbc):
    # Each region edge must touch at least one occupied cell (no padding).
    regions = detect_regions(cells, min_blank_rows=mbr, min_blank_cols=mbc)
    for reg in regions:
        owned = [(r, c) for (r, c) in cells if _contains(reg, r, c)]
        assert min(r for r, _ in owned) == reg.min_row
        assert max(r for r, _ in owned) == reg.max_row
        assert min(c for _, c in owned) == reg.min_col
        assert max(c for _, c in owned) == reg.max_col
