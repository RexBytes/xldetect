<!--
Release title (paste into the GitHub release "title" field):

  xldetect 1.0.0 — Find the table in any Excel sheet

Tag: v1.0.0   Target: main
Everything below the line is the release body.
-->

---

# xldetect 1.0.0

First stable release. `xldetect` is the **discovery** step for messy Excel
workbooks: it finds *where* the data is — table regions, headers, and merged
cells — so a processing step like [`xlfilldown`](https://pypi.org/project/xlfilldown/)
can act on it. `openpyxl` tells you cell values; `xldetect` tells you where the
table starts.

## Highlights

- **Multi-table detection** — multiple rectangular regions per sheet (stacked
  *and* side-by-side), across sheets, via recursive blank-gap segmentation.
  Every occupied cell lands in exactly one non-overlapping region.
- **Header detection** — content-based scoring (text-over-data type distinction)
  with formatting as *corroborating* evidence: bold/fill/border can only raise a
  header's confidence, never lower it, so a clean plain header scores as high as
  a styled one. Conservative multi-row (stacked) header support.
- **Merged cells** — reported as ranges and forward-filled with the anchor value
  so banners are detected correctly.
- **Decorative content** — title rows and full-width merged banners are trimmed;
  zero-data regions (separated banners, stray titles) are classified decorative
  and kept out of the tabular results (recoverable via `decorative_regions`).
- **Confidence score** per region for easy filtering.
- **xlfilldown integration** — `to_xlfilldown_plan()` maps a region onto
  xlfilldown's real API and emits honest `caveats` when a region can't be
  ingested losslessly (it reads one header row to end-of-sheet across all
  headered columns).
- **CLI** — `xldetect inspect file.xlsx` with text, `--json`, and `--xlfilldown`
  output. Bad workbooks and bad arguments produce clean errors, never tracebacks.
- **Typed results** — dataclasses with JSON-safe `to_dict()` throughout.

## Install

    pip install xldetect

Requires Python 3.11+. Runtime dependency: `openpyxl>=3.1`.

## Quick start

```python
from xldetect import inspect_path

report = inspect_path("messy.xlsx")
for region in report.iter_regions():
    print(region.range_a1, region.headers, region.confidence)
```

```bash
xldetect inspect messy.xlsx              # human-readable preview
xldetect inspect messy.xlsx --json       # full report as JSON
xldetect inspect messy.xlsx --xlfilldown # one xlfilldown plan per region
```

## Pairing with xlfilldown

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

## Notes

- Detection is structural, not semantic: no formula evaluation, no data
  transformation. Deliberate tradeoffs (single-blank-row splitting, all-text
  header ambiguity, summary rows kept as data, formula caching) are documented
  with rationale and overrides in **LIMITATIONS.md**.
- AI assistants: **SKILL.md** ships in the package as an LLM-consumable guide.

## Quality

138 tests (truth-table corners, threshold pinning, hypothesis property tests,
golden CLI files, and a live xlfilldown round-trip), 99% coverage. CI runs on
Python 3.11 and 3.12.

**Full scope of in/out of scope, API, and design rationale:** see README.md,
SKILL.md, and LIMITATIONS.md.
