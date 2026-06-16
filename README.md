# xldetect

[![CI](https://github.com/RexBytes/xldetect/actions/workflows/ci.yml/badge.svg)](https://github.com/RexBytes/xldetect/actions/workflows/ci.yml)

Structural detection of table-like **data regions**, **headers**, and **merged
cells** in Excel worksheets. `xldetect` is the *discovery* step: it finds *where*
the tables are so a processing step (like
[`xlfilldown`](https://pypi.org/project/xlfilldown/)) can act on them.

Users say "grab the table", but a worksheet has no concept of one — just
scattered cells, merged banners, decorative titles, summary rows, and sometimes
several tables on one sheet. `openpyxl` tells you cell values; it does not tell
you where the data starts. `xldetect` answers that question from structure alone.

- Detect multiple rectangular data regions per sheet, across sheets
- Detect header row(s) from content cues (text-over-data) and formatting (bold/fill/border)
- Report and forward-fill merged cells
- Skip decorative title/banner rows
- Confidence score per region
- Emit regions in a shape [`xlfilldown`](https://pypi.org/project/xlfilldown/) can consume

## Install

```bash
pip install xldetect
```

Requires Python 3.11+. Runtime dependency: `openpyxl`.

## Quickstart (CLI)

```bash
xldetect inspect messy.xlsx
```

```
File: messy.xlsx
Sheets: 1   Regions: 2

Sheet 'Data': 2 region(s), used range 8 rows x 3 cols, 1 merged range(s)
  Region 1: A2:C4  (confidence 0.933)
    header row 2: Name, Region, Sales
    data rows 3-4 (2 rows x 3 cols)
    decorative rows skipped: 1
  Region 2: A7:B8  (confidence 0.870)
    header row 7: Product, Qty
    data rows 8-8 (1 row x 2 cols)
```

Other output modes:

```bash
xldetect inspect messy.xlsx --json          # full report as JSON
xldetect inspect messy.xlsx --xlfilldown    # one xlfilldown plan per region
xldetect inspect messy.xlsx --sheet Data --min-blank-rows 2 --header-threshold 0.6
```

## Quickstart (Python)

```python
from xldetect import inspect_path

report = inspect_path("messy.xlsx")
for region in report.iter_regions():
    print(region.range_a1, region.headers, region.confidence)
    # A2:C4 ['Name', 'Region', 'Sales'] 0.933
```

Every result is a typed dataclass with a JSON-safe `to_dict()`. A `Region`
carries: `sheet`, `min_row/max_row/min_col/max_col`, `range_a1`, `has_header`,
`header_rows`/`header_row`, `headers`, `data_start_row`, `n_data_rows`,
`n_cols`, `confidence`, `merged_ranges`, `decorative_rows`, and `notes`.

## Pairing with xlfilldown

`xldetect` finds the region; `xlfilldown` fills it down and ingests it.

```python
from xldetect import inspect_path, to_xlfilldown_plan
import xlfilldown

report = inspect_path("messy.xlsx")
region = next(report.iter_regions())
plan = to_xlfilldown_plan(region, "messy.xlsx",
                          sheet_max_col=report.sheets[0].max_col)

if not plan["caveats"]:
    xlfilldown.ingest_excel_to_sqlite(
        file=plan["file"], sheet=plan["sheet"],
        header_row=plan["header_row"], fill_cols=plan["fill_cols"],
        db="out.db", table="data", if_exists="replace",
    )
```

`xlfilldown` reads one `header_row` to the end of the sheet across all headered
columns. When a region does not span the full sheet (multiple regions, column
offsets), the plan's `caveats` list says so — read it before ingesting. See
[`LIMITATIONS.md`](LIMITATIONS.md).

## Deliberate design tradeoffs

`xldetect` makes opinionated structural guesses. The behaviours most likely to
look like bugs (single-blank-row splitting, all-text header detection, summary
rows kept as data, formula caching) are documented with rationale and overrides
in **[LIMITATIONS.md](LIMITATIONS.md)**.

## Using with AI assistants

[`SKILL.md`](SKILL.md) is an LLM-consumable guide (decision tree, worked
examples, anti-patterns) so coding agents call `xldetect` correctly instead of
hand-rolling region detection.

## Development

```bash
pip install -e .[dev]
pytest            # runs straight from a clean clone (pythonpath = src)
```

## License

MIT — see [LICENSE](LICENSE).
