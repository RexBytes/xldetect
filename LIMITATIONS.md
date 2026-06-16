# LIMITATIONS.md

Deliberate design decisions in `xldetect` that can look like defects on review
but are intentional. Each entry: **concern**, **decision**, **rationale**,
**escape hatch**. Grouped by *why* the behaviour is not "fixed".

---

## Fundamental ambiguity — no correct answer without content understanding

### A single blank row splits stacked tables
- **Concern:** Two blocks separated by one blank row become two regions, and a
  single spacer row inside one logical table also splits it.
- **Decision:** Default `min_blank_rows = 1` (and `min_blank_cols = 1`): one
  fully blank line separates regions.
- **Rationale:** Managers stack distinct tables with a one-row gap far more often
  than they put a blank spacer inside a single table, so this default matches the
  pain point that motivated the package. There is no content-free way to tell a
  spacer from a separator. A larger default would silently merge genuinely
  separate stacked tables, which is the worse failure for the discovery step.
- **Escape hatch:** `inspect_path(path, min_blank_rows=2)` (or `--min-blank-rows 2`)
  treats a single blank row as within-region.

### An all-text block's first row is always called a header
- **Concern:** A table of pure text (e.g. addresses) with no real header still
  reports row 1 as the header.
- **Decision:** Score text-over-text as a header (the `text` cue alone clears the
  default threshold).
- **Rationale:** `b"Name|City"` over `b"Alice|NYC"` is byte-structurally identical
  to two text data rows — distinguishing them needs semantics we don't have.
  Treating the top row as the header is right far more often (most text tables do
  have a header row) and matches what `pandas`/spreadsheet users expect.
- **Escape hatch:** Raise `header_threshold` toward `1.0` to require stronger
  (type-distinction / style) evidence, or ignore `headers` and use
  `region.has_header`/`confidence` to decide per region.

### Summary / total rows are not separated from data
- **Concern:** A "Total" row at the bottom of a table is reported as a data row.
- **Decision:** Trim decorative rows only from the *top* of a region; never strip
  trailing rows.
- **Rationale:** A summary row is structurally a normal data row (same column
  count, often same types); reliably detecting it needs content/formula
  understanding, which is out of scope (that is `xlfilldown`'s and the caller's
  job). Guessing wrong would drop real data.
- **Escape hatch:** Inspect the last row of `region` yourself (e.g. check for a
  bold row or a blank key column) before handing data downstream.

### A header row with no data below is treated as decorative, not a table
- **Concern:** A region that has a detected header (or a lone text/banner row) but
  zero data rows is excluded from `regions` and placed in `decorative_regions`.
- **Decision:** Classify any region with `n_data_rows == 0` as decorative/no-data
  and keep it out of the tabular `regions` list (and out of xlfilldown plans).
- **Rationale:** A zero-data region carries nothing extractable downstream, and a
  separated banner or stray title is far more common than a genuinely empty,
  header-only table. Distinguishing "empty table" from "decorative row" needs
  semantics we do not have, so the structural rule (no data = not a table) is the
  predictable choice and makes the "skip decorative rows" promise hold even when a
  banner is separated from its table by a blank row.
- **Escape hatch:** Read `SheetReport.decorative_regions` (same `Region` type) to
  recover these, e.g. for schema-profiling an empty headered sheet.

### Formula cells with no cached value are invisible
- **Concern:** A workbook authored programmatically and never opened in Excel has
  `None` for formula cells, so those cells are treated as blank.
- **Decision:** Load with `data_only=True` (cached values); never evaluate formulas.
- **Rationale:** Formula evaluation is explicitly out of scope and re-implementing
  Excel's engine is enormous and unsafe. Reading the cached value is the only
  correct, dependency-free option; when there is no cache there is nothing to read.
- **Escape hatch:** Open and re-save the workbook in Excel/LibreOffice once so the
  values cache is populated, then run `xldetect`.

---

## Behaviour is the contract — changing it would silently break callers

### Merged cells are forward-filled with the anchor value
- **Concern:** Every cell of a merged range reports the top-left value, so a
  caller can't tell a filled cell from an originally-populated one by value alone.
- **Decision:** Fill the whole merged area with the anchor value in the `Grid`,
  and record the original rectangles in `merged_ranges`.
- **Rationale:** Filling is what makes a merged banner count as occupied across
  its width (so it is detected/segmented correctly) and mirrors how `xlfilldown`
  treats merges. Leaving inner cells blank would fragment regions around every
  merge. The original geometry is not lost — it is in `merged_ranges`.
- **Escape hatch:** Consult `region.merged_ranges` / `SheetReport.merged_ranges`
  to recover exact merge rectangles and anchor values.

### `xlfilldown` plans for multi-region or offset tables carry caveats, not exact bounds
- **Concern:** `to_xlfilldown_plan` emits only `file`/`sheet`/`header_row`/`fill_cols`
  and a `caveats` list — not a data-end row or column range.
- **Decision:** Mirror `xlfilldown`'s real API exactly and surface every deviation
  as a human-readable caveat instead of inventing parameters it ignores.
- **Rationale:** `xlfilldown` (1.0.x) reads from `header_row + 1` to the **end of
  the sheet**, across **every column with a header value in that row**. It has no
  data-end-row or column-range concept. Emitting fields it ignores would imply a
  precision the downstream tool does not provide; a caveat tells the caller the
  truth (e.g. "extract each region to its own sheet first").
- **Escape hatch:** Split each region onto its own sheet/file before calling
  `xlfilldown`, or read `region.min_row/max_row/min_col/max_col` and slice yourself.

---

## Maintenance rule

When a limitation is genuinely fixed, **delete its entry** — do not leave
"fixed in vX" breadcrumbs. `git log` carries the history; this file describes
only the current state of the library. Add an entry only when a second reviewer
flags the same non-bug.
