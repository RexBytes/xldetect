"""xldetect -- structural detection of data regions in Excel worksheets.

Discovery step that pairs with ``xlfilldown``: find *where* the tables, headers,
and merged cells are, then hand those regions to ``xlfilldown`` for processing.

Typical use::

    from xldetect import inspect_path
    report = inspect_path("messy.xlsx")
    for region in report.iter_regions():
        print(region.range_a1, region.headers, region.confidence)
"""

from __future__ import annotations

from .grid import CellStyle, Grid, cell_kind
from .integration import to_xlfilldown_plan, workbook_to_xlfilldown_plans
from .models import MergedRegion, Region, SheetReport, WorkbookReport
from .orchestrate import inspect_grid, inspect_path, region_confidence
from .reader import build_grid, load_grids
from .report import format_json, format_text

__version__ = "0.1.0"

__all__ = [
    "inspect_path",
    "inspect_grid",
    "region_confidence",
    "Region",
    "SheetReport",
    "WorkbookReport",
    "MergedRegion",
    "Grid",
    "CellStyle",
    "cell_kind",
    "build_grid",
    "load_grids",
    "to_xlfilldown_plan",
    "workbook_to_xlfilldown_plans",
    "format_json",
    "format_text",
    "__version__",
]
