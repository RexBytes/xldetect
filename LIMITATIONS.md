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

## Cost-of-fix exceeds value

### A decorative banner separated by a blank row becomes its own low-confidence region
- **Concern:** A title in `A1` with a blank row 2 above the table surfaces as a
  standalone region (with the banner mis-reported as its header), separate from
  the table below.
- **Decision:** Decorative trimming runs *within* a region only; a banner isolated
  by blank rows is a separate region and is left in the output with low
  `confidence` and `n_data_rows == 0`.
- **Rationale:** Cross-region "is this lone block decorative?" reasoning would add
  a whole second pass and new heuristics, while the signal callers actually need
  is already present: such regions score low and have no data rows. The cleaner
  implementation is not worth the added complexity and false-merge risk.
- **Escape hatch:** Filter regions, e.g. `[r for r in report.iter_regions()
  if r.n_data_rows >= 1 and r.confidence >= 0.5]`.

---

## Maintenance rule

When a limitation is genuinely fixed, **delete its entry** — do not leave
"fixed in vX" breadcrumbs. `git log` carries the history; this file describes
only the current state of the library. Add an entry only when a second reviewer
flags the same non-bug.
