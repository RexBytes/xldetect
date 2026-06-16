"""Rendering :class:`~xldetect.models.WorkbookReport` for humans and machines.

This module exists to keep all output formatting in one place so the CLI stays a
thin wrapper and so the exact output shape can be pinned by golden-file tests.
:func:`format_json` produces deterministic, sorted JSON; :func:`format_text`
produces a stable human-readable preview with no timestamps or other volatile
fields.
"""

from __future__ import annotations

import json

from .models import WorkbookReport


def _plural(n: int, noun: str) -> str:
    """Return ``"1 row"`` / ``"2 rows"`` -- naive ``s`` pluralisation."""
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def format_json(report: WorkbookReport) -> str:
    """Render a report as deterministic JSON (sorted keys, 2-space indent)."""
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def _format_region(index: int, region) -> list[str]:
    lines = [
        f"  Region {index}: {region.range_a1}  "
        f"(confidence {region.confidence:.3f})",
    ]
    if region.has_header:
        cols = ", ".join(h if h else "<blank>" for h in region.headers)
        lines.append(f"    header row {region.header_row}: {cols}")
    else:
        lines.append("    header: none detected")
    if region.n_data_rows >= 1:
        lines.append(
            f"    data rows {region.data_start_row}-{region.max_row} "
            f"({_plural(region.n_data_rows, 'row')} x {_plural(region.n_cols, 'col')})"
        )
    else:
        lines.append(f"    data rows: none ({_plural(region.n_cols, 'col')})")
    if region.decorative_rows:
        rows = ", ".join(str(r) for r in region.decorative_rows)
        lines.append(f"    decorative rows skipped: {rows}")
    if region.merged_ranges:
        lines.append(f"    merged ranges: {len(region.merged_ranges)}")
    return lines


def format_text(report: WorkbookReport) -> str:
    """Render a report as a stable, human-readable multi-line preview."""
    lines = [
        f"File: {report.path}",
        f"Sheets: {len(report.sheets)}   Regions: {report.n_regions}",
    ]
    for sheet in report.sheets:
        lines.append("")
        lines.append(
            f"Sheet '{sheet.sheet}': {sheet.n_regions} region(s), "
            f"used range {sheet.max_row} rows x {sheet.max_col} cols, "
            f"{len(sheet.merged_ranges)} merged range(s)"
        )
        if not sheet.regions:
            lines.append("  (no data regions detected)")
        for i, region in enumerate(sheet.regions, start=1):
            lines.extend(_format_region(i, region))
        for note in sheet.notes:
            lines.append(f"  note: {note}")
    return "\n".join(lines)
