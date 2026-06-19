# Panel prompt template

The brief sent to each model slot in a review panel. Send the SAME text to every
model (vary only the model itself), filling the `<…>` placeholders. Run the
panel as: one slot per available model (e.g. opus, sonnet, haiku), each
optionally spawning SAME-model sub-agents. Then adjudicate (see CONTRIBUTING.md):
consensus → fix; singleton → reproduce yourself before fixing; mock-only/
documented → dismiss with a reason.

---

HEAD-TO-HEAD adversarial review (read-only; MAKE NO CHANGES) of `xldetect` at
`<repo path>`. `<N cycles / panels>` deep. **"No new defects" after genuine effort
is the expected, valued result — do NOT manufacture findings; mock-only /
shallow / duplicate findings count against you.**

=== VERIFY LATEST CODE ===
`git -C <repo path> rev-parse HEAD` must equal `<HEAD sha>`. If your Read tool
disagrees with disk, distrust the cache and re-read via `python -c`/`nl -ba`.
Cite real current file:line. Already `pip install -e .[dev]`'d; pytest/ruff/mypy
pass (`<X passed, Y skipped>`). You MAY spawn helper sub-agents but they MUST run
on the SAME model as you. Run python/pytest/ruff/mypy + /tmp repros freely
(build real `.xlsx` fixtures with `openpyxl`).

=== RULES OF EVIDENCE (strict) ===
A finding MUST reproduce with a REAL input — a real `.xlsx` built with
`openpyxl` (no monkeypatching/mocking internal methods; those paths are
intentionally not defended). Provide an executed repro for every CONFIRMED
finding. No real-input repro -> not a finding.

=== FULL TESTING / REVIEW PHILOSOPHY (apply rigorously; this is the standard) ===
Hunt inputs that FALSIFY a promise, not confirm the happy path.
1. Every docstring sentence, type, parameter description, named behaviour, and
   threshold constant is a promise — list them and break each. If docs claim X,
   find the input where the code does not-X.
2. Boolean functions: all four corners — confirmed-true, confirmed-false,
   false-for-a-DIFFERENT-reason, true-under-adversarial-input.
3. Every parameter: empty, boundary, and the messy real-world input it exists for.
4. Pin thresholds N (passes) and N+1 (fails).
5. Fallbacks preserve intent, not just type-check ("decorative/no-data" stays
   distinct from a real region; a forward-filled merged cell stays recoverable
   via `merged_ranges`; a normalised file error still carries its cause).
6. Reach for stdlib primitives and their EXACT exception types — bugs hide in
   which exception `openpyxl`/`zipfile` raises and whether `reader.py` lists it.
7. Round-trip / invariant thinking for transform paths: region segmentation must
   stay disjoint, total, and tight for arbitrary cell sets.
8. Golden/CLI thinking: would formatting drift or a wrong exit code slip silently
   across the text / `--json` / `--xlfilldown` modes?
9. A test that reveals a real source bug IS the finding.

=== WHERE TO LOOK (tune per round) ===
The deepest residuals for this package:
- Symmetry across siblings: row-split vs column-split segmentation; header-present
  vs header-absent confidence; single region vs stacked/side-by-side regions;
  `to_xlfilldown_plan` (single) vs `workbook_to_xlfilldown_plans` (batch).
- Threshold interactions not jointly tested: `min_blank_rows` × `min_blank_cols`
  × `header_threshold` × `max_header_rows` on one messy sheet.
- Numeric/accounting invariants: confidence formula bounds [0,1]; `n_data_rows`,
  `data_start_row`, and reported ranges agreeing with the actual grid.
- Dependency-version edges: `openpyxl` style/exception differences; `xlfilldown`
  1.0.x plan contract (`integration.py` caveats).
- Merged-cell forward-fill vs `merged_ranges` recovery; formula cells with no
  cached value treated as blank.

=== ALREADY-FIXED (do NOT re-report) ===
`<running list of fixes from prior panels, so reviewers hunt only what's left.>`

READ `<repo>/LIMITATIONS.md` FIRST; do NOT re-report documented tradeoffs (you
may argue one is wrong, with reasoning).

=== DELIVERABLE ===
Numbered, severity-ranked (CRITICAL/HIGH/MEDIUM/LOW/NIT). Each: title; severity;
exact file.py:line; concrete real-input failure (input + what breaks); fix
direction. Mark CONFIRMED + the repro for executed items. NEW real defects only.
"No new defects" is valid and expected.
