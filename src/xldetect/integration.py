"""Mapping detected regions onto ``xlfilldown`` parameters.

This module exists to hand a detected :class:`~xldetect.models.Region` to
``xlfilldown`` (the downstream fill-down/ingest step) without the caller having
to reverse-engineer the join. ``xldetect`` never imports ``xlfilldown`` -- it
only emits a plain ``dict`` whose keys match ``xlfilldown``'s public functions
``ingest_excel_to_sqlite`` / ``ingest_excel_to_excel`` (``file``, ``sheet``,
``header_row``, ``fill_cols``).

Important constraint, verified against ``xlfilldown`` 1.0.x: it reads from
``header_row + 1`` to the **end of the sheet**, across **every column that has a
header value in that row**. It has no notion of a data-end row or a column
range. So a plan is only loss-free when the region spans the sheet's full used
width and is the sole region below its header. For every way a region deviates
from that, :func:`to_xlfilldown_plan` records a human-readable ``caveat`` rather
than pretending the mapping is exact. See ``LIMITATIONS.md``.
"""

from __future__ import annotations

from .coords import column_letter
from .models import Region, WorkbookReport


def to_xlfilldown_plan(region: Region, file: str, *, sheet_max_col: int | None = None) -> dict:
    """Build an ``xlfilldown``-consumable plan dict for a single region.

    Args:
        region: A detected region (ideally one with ``has_header=True``).
        file: Path to the workbook, passed straight through as ``file``.
        sheet_max_col: The sheet's highest used column, if known. Used only to
            decide whether the region reaches the sheet's right edge (a caveat
            is added if other columns sit to its right, since ``xlfilldown``
            would also ingest them).

    Returns:
        A dict with keys ``file``, ``sheet``, ``header_row``, ``fill_cols``
        (non-empty header labels, the columns ``xlfilldown`` keeps), plus
        ``min_col``/``max_col`` for reference and a ``caveats`` list. ``fill_cols``
        is ``[]`` and a caveat is recorded when no header was detected.
    """
    caveats: list[str] = []

    header_row = region.header_row
    if not region.has_header or header_row is None:
        caveats.append(
            "no header detected; set 'header_row' manually before calling xlfilldown"
        )
        header_row = region.min_row

    fill_cols = [h for h in region.headers if h]
    if region.has_header and len(fill_cols) < len(region.headers):
        caveats.append(
            "some columns have blank headers; xlfilldown ingests only headered columns"
        )

    if region.min_col != 1:
        caveats.append(
            f"region starts at column {column_letter(region.min_col)} (not A); "
            "xlfilldown reads from column A, so columns to the left would also be ingested"
        )

    if sheet_max_col is not None and region.max_col < sheet_max_col:
        caveats.append(
            f"region ends at column {column_letter(region.max_col)} but the sheet uses "
            f"columns out to {column_letter(sheet_max_col)}; xlfilldown would include them"
        )

    return {
        "file": file,
        "sheet": region.sheet,
        "header_row": header_row,
        "fill_cols": fill_cols,
        "min_col": region.min_col,
        "max_col": region.max_col,
        "caveats": caveats,
    }


def workbook_to_xlfilldown_plans(report: WorkbookReport) -> list[dict]:
    """Build one plan per region in a :class:`WorkbookReport`.

    When a sheet holds more than one region, a shared caveat is added to every
    plan on that sheet: ``xlfilldown`` reads a single header row to end-of-sheet,
    so the regions cannot be isolated by header row alone and must be extracted
    to separate sheets/files first.
    """
    plans: list[dict] = []
    for sheet in report.sheets:
        multi = sheet.n_regions > 1
        for region in sheet.regions:
            plan = to_xlfilldown_plan(region, report.path, sheet_max_col=sheet.max_col)
            if multi:
                plan["caveats"].append(
                    f"sheet '{sheet.sheet}' has {sheet.n_regions} regions; xlfilldown reads "
                    "one header row to end-of-sheet -- extract each region separately first"
                )
            plans.append(plan)
    return plans
