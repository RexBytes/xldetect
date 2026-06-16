---
name: xldetect
description: >-
  Find table-like data regions, headers, and merged cells in Excel/.xlsx
  worksheets. Use when the user says: "where does the data start", "find the
  table", "grab the table from this spreadsheet", "multiple tables on one sheet",
  "skip the title rows / header junk", "detect headers", "merged cells",
  "decorative rows", "pandas read garbage headers", "what columns are in this
  xlsx", "profile an Excel file", or wants to feed an Excel region into
  xlfilldown. Discovery step; pairs with xlfilldown for processing.
---

# xldetect

Structural detection of data regions in Excel worksheets. No content
understanding, no formula evaluation — geometry and formatting only. Coordinates
are 1-based inclusive (Excel-style).

## When to use what

| User intent | Call | Returns |
|---|---|---|
| Inspect a whole workbook | `inspect_path(path)` | `WorkbookReport` |
| Iterate every region found | `report.iter_regions()` | iterator of `Region` |
| Inspect one in-memory sheet | `inspect_grid(grid)` | `SheetReport` |
| JSON-safe dict of a result | `result.to_dict()` | `dict` |
| Map a region to xlfilldown params | `to_xlfilldown_plan(region, file)` | `dict` with `caveats` |
| Map every region to plans | `workbook_to_xlfilldown_plans(report)` | `list[dict]` |
| Human preview text | `format_text(report)` | `str` |
| Deterministic JSON | `format_json(report)` | `str` |
| CLI preview | `xldetect inspect file.xlsx` | stdout |

Import from the top level: `from xldetect import inspect_path, to_xlfilldown_plan`.

## Failure modes already handled — do not reinvent

- Multiple tables on one sheet (stacked **and** side-by-side) → separate regions.
- L-shaped / ragged occupancy → clean rectangular decomposition.
- Decorative title rows and full-width merged banners above a table → trimmed.
- Merged cells → forward-filled with anchor value; rectangles recorded.
- Header vs data → scored from text-over-data type distinction + bold/fill/border.
- Multi-row (stacked) headers → detected conservatively (all-text, populated, distinct).
- `bool` miscounted as `int` → handled (`cell_kind` checks bool first).
- Formula cells → cached values read (`data_only=True`); formulas never evaluated.
- Blank vs whitespace-only cells → both treated as empty.
- Confidence scoring so callers can filter junk regions.

## Worked examples

### inspect_path → Region.to_dict()

Sheet `Data`: `A1=Name`(bold) `B1=Amount`(bold); rows 2–3 = `Alice/10`, `Bob/20`.

```python
from xldetect import inspect_path
report = inspect_path("data.xlsx")
region = next(report.iter_regions())
region.to_dict()
```

```json
{
  "sheet": "Data",
  "range": "A1:B3",
  "min_row": 1, "max_row": 3, "min_col": 1, "max_col": 2,
  "has_header": true,
  "header_row": 1,
  "header_rows": [1],
  "headers": ["Name", "Amount"],
  "data_start_row": 2,
  "n_data_rows": 2,
  "n_cols": 2,
  "confidence": 0.95,
  "merged_ranges": [],
  "decorative_rows": [],
  "notes": []
}
```

`header_row` is the bottom-most header row (the one labelling the data);
`header_rows` lists all of them. `headers` has one entry per column; a blank
header cell is `""` (not dropped). `data_start_row` = first data row.

### to_xlfilldown_plan

```python
from xldetect import inspect_path, to_xlfilldown_plan
report = inspect_path("data.xlsx")
region = next(report.iter_regions())
to_xlfilldown_plan(region, "data.xlsx", sheet_max_col=report.sheets[0].max_col)
```

```json
{
  "file": "data.xlsx",
  "sheet": "Data",
  "header_row": 1,
  "fill_cols": ["Name", "Amount"],
  "min_col": 1,
  "max_col": 2,
  "caveats": []
}
```

Then pass straight to xlfilldown (only `caveats == []` is loss-free):

```python
import xlfilldown
xlfilldown.ingest_excel_to_sqlite(
    file=plan["file"], sheet=plan["sheet"],
    header_row=plan["header_row"], fill_cols=plan["fill_cols"],
    db="out.db", table="data", if_exists="replace",
)
```

A non-empty `caveats` means xlfilldown would over-read (it reads `header_row+1`
to end-of-sheet across all headered columns). Common caveats: `"no header
detected..."`, `"region starts at column B..."`, `"sheet '...' has N regions..."`.

### cell_kind (lower-level)

```python
from xldetect import cell_kind
cell_kind(True)            # "bool"   (checked before number!)
cell_kind(3.14)            # "number"
cell_kind("Name")          # "text"
cell_kind("   ")           # "empty"
cell_kind(None)            # "empty"
import datetime; cell_kind(datetime.date(2026, 1, 1))  # "date"
```

### Tuning detection

```python
inspect_path("f.xlsx", min_blank_rows=2)      # 1 blank row no longer splits
inspect_path("f.xlsx", header_threshold=0.7)  # stricter header acceptance
inspect_path("f.xlsx", sheets=["Q1"])         # only this sheet
```

## Don't

- **Don't** `openpyxl.load_workbook(...)` yourself to find the table — that is
  exactly what this package does. Call `inspect_path`.
- **Don't** `pandas.read_excel(skiprows=N)` with a hand-guessed `N`; use
  `region.data_start_row` (and `header_row`) from detection.
- **Don't** assume one table per sheet — iterate `report.iter_regions()`.
- **Don't** feed a region to xlfilldown without checking `plan["caveats"]`.
- **Don't** treat `headers == []` as an error — it means `has_header` is `False`;
  use the region as raw data.
- **Don't** re-read the file per region — `inspect_path` reads once and returns
  everything.
- **Don't** expect formula results — load+save in Excel first if formula cells
  matter (see LIMITATIONS.md).

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| One logical table split into two regions | a blank spacer row inside it | `min_blank_rows=2` |
| Two stacked tables merged into one | no blank row between them | leave default; or pre-insert a blank row |
| A title row reported as the header | title separated from table by a blank row → own region | filter by `confidence`/`n_data_rows` |
| `has_header` False on a real header | header not text-distinct from body, no styling | lower `header_threshold` |
| Formula columns missing | workbook never opened in Excel (no cached values) | open + save the file, re-run |
| xlfilldown ingests extra columns/rows | region not full-width / multiple regions | read `plan["caveats"]`; split sheet first |
| `ValueError: Sheet 'X' not found` | wrong `sheets=` name | check `[s.sheet for s in report.sheets]` |

## Testing code that uses this library

- **Property test** region invariants with hypothesis: every occupied cell is in
  exactly one region; region bounding boxes never overlap (pass explicit
  `min_blank_rows`/`min_blank_cols`).
- **Cross-API**: `to_xlfilldown_plan(region, file)` with `caveats == []` should
  drive a real `xlfilldown.ingest_excel_to_sqlite` round-trip.
- **Golden-file** the CLI output (`xldetect inspect`), masking the file path.
- Build `Grid` objects directly (`from xldetect import Grid`) to unit-test
  detection without `.xlsx` fixtures.

See **LIMITATIONS.md** for deliberate tradeoffs before "fixing" surprising behaviour.
