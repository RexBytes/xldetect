"""End-to-end inspection pipeline.

This module wires the detectors together into the package's main entry point,
:func:`inspect_path`: load grids -> segment regions -> trim decorative rows ->
detect headers -> score confidence -> assemble typed result objects. It also
owns :func:`region_confidence`, the documented scoring formula, because
confidence depends on the combination of detectors rather than any single one.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .detectors.decorative import trim_decorative
from .detectors.headers import HeaderResult, detect_header
from .detectors.merged import merged_in_region
from .detectors.regions import RawRegion, detect_regions
from .grid import Grid
from .models import MergedRegion, Region, SheetReport, WorkbookReport
from .reader import load_grids


def region_confidence(
    grid: Grid, region: RawRegion, header: HeaderResult, data_start_row: int
) -> float:
    """Score a region's "table-likeness" in ``[0, 1]`` (rounded to 3 decimals).

    The score is a weighted blend of three signals plus a degeneracy penalty:

    * ``0.40 * header_component`` -- the header score if a header was found, else
      a flat ``0.30`` (a region can still be a real table without a header);
    * ``0.35 * fill_ratio`` -- occupied cells divided by bounding-box area;
    * ``0.25 * regularity`` -- the fraction of data rows whose occupied-cell
      count equals the most common (modal) data-row width.

    The blended score is multiplied by ``0.5`` when the region is degenerate
    (fewer than one data row, or only a single column), because a 1xN strip or a
    header with no data is rarely a table a caller wants to extract.
    """
    rows = range(region.min_row, region.max_row + 1)
    cols = range(region.min_col, region.max_col + 1)
    width = region.n_cols
    area = region.n_rows * width
    occ = sum(1 for r in rows for c in cols if grid.is_occupied(r, c))
    fill_ratio = occ / area if area else 0.0

    data_rows = list(range(data_start_row, region.max_row + 1))
    counts = [sum(1 for c in cols if grid.is_occupied(r, c)) for r in data_rows]
    if counts:
        modal = Counter(counts).most_common(1)[0][0]
        regularity = sum(1 for x in counts if x == modal) / len(counts)
    else:
        regularity = 0.0

    header_component = header.score if header.has_header else 0.30
    conf = 0.40 * header_component + 0.35 * fill_ratio + 0.25 * regularity

    if len(data_rows) < 1 or width < 2:
        conf *= 0.5
    return round(min(max(conf, 0.0), 1.0), 3)


def build_region(
    grid: Grid, raw: RawRegion, *, header_threshold: float = 0.5
) -> Region:
    """Run the per-region pipeline (trim -> header -> confidence) and build a :class:`Region`."""
    trim = trim_decorative(grid, raw)
    r = trim.region
    header = detect_header(grid, r, threshold=header_threshold)

    data_start = (header.header_row + 1) if header.has_header else r.min_row
    n_data_rows = max(0, r.max_row - data_start + 1)
    conf = region_confidence(grid, r, header, data_start)

    merged = [
        MergedRegion(mr0, mc0, mr1, mc1, value=grid.value_at(mr0, mc0))
        for (mr0, mc0, mr1, mc1) in merged_in_region(
            grid.merged, r.min_row, r.max_row, r.min_col, r.max_col
        )
    ]

    notes = list(trim.notes)
    if merged:
        notes.append(f"{len(merged)} merged range(s) intersect this region")

    return Region(
        sheet=grid.sheet,
        min_row=r.min_row,
        max_row=r.max_row,
        min_col=r.min_col,
        max_col=r.max_col,
        has_header=header.has_header,
        header_rows=header.header_rows,
        headers=header.headers,
        data_start_row=data_start,
        n_data_rows=n_data_rows,
        n_cols=r.n_cols,
        confidence=conf,
        merged_ranges=merged,
        decorative_rows=trim.removed_rows,
        notes=notes,
    )


def inspect_grid(
    grid: Grid,
    *,
    min_blank_rows: int = 1,
    min_blank_cols: int = 1,
    header_threshold: float = 0.5,
) -> SheetReport:
    """Inspect a single :class:`Grid` and return a :class:`SheetReport`."""
    raw_regions = detect_regions(
        grid.occupied, min_blank_rows=min_blank_rows, min_blank_cols=min_blank_cols
    )
    regions = [
        build_region(grid, raw, header_threshold=header_threshold) for raw in raw_regions
    ]
    merged = [
        MergedRegion(mr0, mc0, mr1, mc1, value=grid.value_at(mr0, mc0))
        for (mr0, mc0, mr1, mc1) in grid.merged
    ]
    return SheetReport(
        sheet=grid.sheet,
        max_row=grid.max_row,
        max_col=grid.max_col,
        regions=regions,
        merged_ranges=merged,
    )


def inspect_path(
    path: str | Path,
    *,
    sheets: list[str] | None = None,
    min_blank_rows: int = 1,
    min_blank_cols: int = 1,
    header_threshold: float = 0.5,
) -> WorkbookReport:
    """Inspect a workbook file and return a :class:`WorkbookReport`.

    Args:
        path: Path to an ``.xlsx`` workbook.
        sheets: Optional subset of sheet names to inspect (``None`` = all).
        min_blank_rows: Blank-row gap that separates stacked regions (default 1).
        min_blank_cols: Blank-column gap that separates side-by-side regions (default 1).
        header_threshold: Minimum header score to accept a header row (default 0.5).
    """
    grids = load_grids(path, sheets=sheets)
    sheet_reports = [
        inspect_grid(
            grid,
            min_blank_rows=min_blank_rows,
            min_blank_cols=min_blank_cols,
            header_threshold=header_threshold,
        )
        for grid in grids.values()
    ]
    return WorkbookReport(path=str(path), sheets=sheet_reports)
