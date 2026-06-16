"""Shared fixtures and grid/workbook builders for the test suite."""

from __future__ import annotations

import openpyxl
from openpyxl.styles import Border, Font, PatternFill, Side

from xldetect.grid import CellStyle, Grid


def grid_from_rows(
    rows,
    *,
    start_row: int = 1,
    start_col: int = 1,
    sheet: str = "S",
    styled: bool = False,
    merged=None,
):
    """Build a :class:`Grid` from a 2D list of values.

    ``None`` and whitespace-only strings are treated as blank (omitted). When
    ``styled`` is True, every occupied cell gets a plain (all-False) style so the
    grid reports ``has_styles`` True without any decoration; pass explicit styles
    via :func:`grid_with_styles` when decoration matters.
    """
    values = {}
    styles = {}
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            if v is None or (isinstance(v, str) and v.strip() == ""):
                continue
            coord = (start_row + i, start_col + j)
            values[coord] = v
            if styled:
                styles[coord] = CellStyle()
    return Grid(values=values, styles=styles, merged=list(merged or []), sheet=sheet)


def make_workbook(path, sheets):
    """Write an .xlsx file. ``sheets`` maps sheet name -> list of (coord, value) or dicts.

    Each entry in a sheet's list is a dict with keys: ``coord`` (e.g. "A1"),
    ``value``, and optional ``bold``/``fill``/``border``. Merges are given under
    the special key handled by ``_merges``.
    """
    wb = openpyxl.Workbook()
    first = True
    for name, spec in sheets.items():
        ws = wb.active if first else wb.create_sheet(title=name)
        if first:
            ws.title = name
            first = False
        for cell in spec.get("cells", []):
            c = ws[cell["coord"]]
            c.value = cell["value"]
            if cell.get("bold"):
                c.font = Font(bold=True)
            if cell.get("fill"):
                c.fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
            if cell.get("border"):
                thin = Side(style="thin")
                c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        for rng in spec.get("merges", []):
            ws.merge_cells(rng)
    wb.save(str(path))
    return str(path)
