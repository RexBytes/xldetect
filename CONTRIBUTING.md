# Contributing to xldetect

This document records **how xldetect is tested and reviewed**. It is the
project's quality contract: changes are expected to follow the testing
philosophy below, and significant changes are expected to survive the review
approach below.

Run the suite before sending anything:

```bash
pip install -e ".[dev]"
pytest -q          # tests
ruff check src tests
mypy               # type-check (config in pyproject.toml)
```

---

## Testing philosophy

Write tests that would **fail if a promise were broken**, not tests that
confirm the code you just wrote happened to run.

1. **Contracts are promises.** Every docstring sentence, type signature,
   parameter description, named behaviour, and threshold constant is a promise.
   Before testing a function, list its promises; write one test per promise.
   If you can't, the docstring is aspirational or wrong — fix the docstring.

2. **Boolean functions: all four truth-table corners.** For a predicate, cover
   confirmed-true, confirmed-false, false-for-a-*different*-reason, and
   true-under-adversarial-input. Example from this codebase: a header row is
   detected (true) for `["Name", "Region"]` over numeric data; not detected
   (false) for three numeric data rows; not detected *for a different reason*
   when the candidate row is all-text but matches the body's types (no
   type-distinction); and `_is_secondary_header` must reject a stray one-column
   annotation row that is technically all-text (adversarial).

3. **Every parameter: empty, boundary, and the messy real input.** Probe the
   empty case (a blank sheet → zero regions), the boundary case, and the messy
   real-world input that motivated the code (the stacked tables, decorative
   banners, merged title rows, and summary rows that exist *because* users hit
   them).

4. **Pin thresholds just above and just below.** A "limit of N" means nothing
   unless `N` passes and `N+1` fails. See `min_blank_rows=1` (one blank row
   splits, the row before it does not), `max_header_rows=2` (a third candidate
   header row is *not* swallowed), and `header_threshold` pinned just above and
   just below an accepted header score.

5. **Fallbacks must preserve intent, not just type-check.** Ask what a fallback
   *returns* and whether the caller can still tell things apart: a header-only
   region with `n_data_rows == 0` must stay distinguishable from a real table
   (it goes to `decorative_regions`, not `regions`); a forward-filled merged
   cell must stay recoverable (the original rectangle survives in
   `merged_ranges`); a normalised file error must still carry its cause. A value
   that type-checks is not the same as a value that preserves meaning.

6. **Reach for stdlib primitives and their exact exception types.** Bugs hide in
   *which* exception a library raises and whether the catching code lists it.
   `reader.py` is the only module that touches `openpyxl`; it normalises
   `zipfile.BadZipFile` and `openpyxl`'s `InvalidFileException` into a single
   `ValueError` so callers never see a raw lower-level traceback. Test the exact
   exception type a corrupt/missing/non-xlsx file produces, not just "it raises".

7. **Round-trip / invariant property tests for transform paths.** Region
   segmentation has structural invariants that must hold for *arbitrary* cell
   sets: regions are disjoint, every occupied cell lands in exactly one region,
   and bounds are tight (`tests/test_regions_properties.py`, Hypothesis).
   Isolate the property from unrelated logic with explicit config so a
   falsifying example points at the right failure.

8. **Golden-file tests for CLI/formatted output.** Pin byte-exact stdout for
   each output mode (text, `--json`, `--xlfilldown`) with volatile fields
   masked, so formatting drift or a wrong exit code fails loudly instead of
   silently breaking downstream scripts (`tests/test_cli_golden.py`,
   `tests/golden/`).

9. **When a test reveals a real source bug, keep the test.** Pin the current
   contract; mark `xfail(strict=True)` if needed and report the bug — don't
   quietly fix source in the same pass that changed the test, or you lose the
   regression signal.

Test layout mirrors source (`tests/test_<module>.py`) plus cross-cutting files:
`test_regions_properties.py` (property/invariant), `test_cli_golden.py` (golden
CLI), and `test_integration.py` (the `xlfilldown` plan boundary). Tests must not
modify source.

---

## Review approach: competitive multi-model panel

xldetect is reviewed by **spinning up several review agents on *different*
underlying models, pointed at the same code**, then adjudicating their reports.
This is how the bugs that survive single-reviewer cycles get found.

**Why it works.** Different models have different blind spots. Run head-to-head
on identical scope, their *overlap* is a high-confidence signal and their
*singletons* are leads to verify.

**How to run it.** Fill `panel_prompt.template.md` for the round, then:

1. **Identical brief, different models.** Give each reviewer the *same* scope
   and the *same* brief, varying only the model. The brief **must include the
   full testing philosophy above, verbatim** — not a condensed summary. Every
   model is entitled to the same standard; do not hand one a fuller version than
   another, and do not assume a model "already knows it." Also tell each to read
   `LIMITATIONS.md` first and not re-flag documented tradeoffs, to prove
   findings with a `/tmp` repro built from a real `.xlsx`, and that false
   findings count against them.

   **Sub-agents stay on the same model.** A reviewer may spawn its own helper
   sub-agents (e.g. one per module) if it wants to parallelise — but every
   sub-agent it spawns must run on the *same* model as that panel slot, so each
   slot remains a clean single-model signal. Cross-model mixing happens only at
   the panel level (one slot per model), never inside a slot.

2. **Coordinator adjudicates; never relay unverified.**
   - **Consensus** (flagged by ≥2 models) → high confidence; fix.
   - **Singleton** → reproduce it yourself before touching code.
   - **False / no-op** → dismiss explicitly with the reason (e.g. a documented
     LIMITATIONS tradeoff re-reported as a bug), don't churn.
   - Beware reviewers running a **stale checkout** — reconcile their line
     numbers and test counts against current `HEAD`.

3. **Fix in adjudicated batches with full-philosophy regression tests.** Every
   fix lands with a test that pins the contract it restores (four corners,
   just-above/below boundary, no-partial-left, intent-preserving fallback).

4. **The done signal.** A panel that comes back with only confirmations of
   prior fixes (no new real defects) — and reviewers that *cite* `LIMITATIONS.md`
   when triaging — is the signal the surface has converged.

### Watching the long tail

What late panels surface is **residual** — the leftover after every prior cycle
removed what it could. Two senses, both in play:

- **Residual defect** — a bug that *survived* earlier passes (not newly
  introduced); often hidden behind a more obvious sibling that got fixed first.
- **Residual risk** — the estimated probability of *still-undiscovered* defects.
  It never reaches zero (you can't prove absence), so you measure it and decide
  if it's low enough to ship. The convergence metric is our proxy for it: a low,
  decaying per-panel yield ⇒ low residual risk.

Late panels behave differently from early ones; expect it rather than over-react:

- **The yield plateaus at a floor, not zero.** After the first few panels the
  severity-weighted yield drops sharply and then *sits* near a small floor. That
  floor is the long tail: one model finds one narrow thing per panel.
- **Findings get shallow, idiosyncratic, often pre-existing.** Long-tail defects
  are niche edges (a one-column all-text row at a region boundary) or ordering
  bugs predating a refactor — not structural clusters. They are singletons, so
  reproduce each against a real `.xlsx` before fixing and dismiss mock-only ones.
- **Don't let the tail inflate severity.** A panel that finds only a niche LOW is
  *near-converged*, not "still broken." Keep the severity weights honest.
- **Decide ship-vs-continue explicitly.** When successive panels return only
  niche LOW/NIT (or clean), weigh one more cycle against shipping with an
  explicit "RRS = X, known long-tail" note. Two consecutive full-diversity clean
  panels is the ideal stop; shipping a documented long tail is a legitimate
  alternative for a non-safety-critical library.

See `LIMITATIONS.md` for the deliberate tradeoffs reviewers should not re-litigate.

### Mind the blind spots (a clean panel only counts where it can see)

A panel can only "converge" on code it actually exercises. xldetect's
`xlfilldown` integration (`integration.py`) is exercised against the real
`xlfilldown` package, whose extraction contract is version-specific
(`xlfilldown` 1.0.x reads one `header_row` to end-of-sheet across every headered
column — see `LIMITATIONS.md`). And `reader.py` behaviour depends on the exact
`openpyxl` version's exceptions and style objects. A panel run without those
deps pinned is **blind** to a version break.

Rules that follow:

- Before trusting convergence, list the code paths the panel could *not* run
  (the `xlfilldown` plan boundary, `openpyxl` version-specific exceptions,
  formula-cache-absent workbooks) and exercise them explicitly.
- Pin dependency ranges and test across the boundaries (`xlfilldown>=1.0,<2`,
  `openpyxl>=3.1`) — an unconstrained dep can silently break a feature with zero
  red tests. CI runs the suite across an `openpyxl` version matrix and against
  the pinned `xlfilldown` for exactly this reason.
- A release decision must state which surfaces the convergence signal covers and
  which rest on CI/other evidence instead.

## Lessons learned (reusable across packages)

These are deliberately package-agnostic — apply them to any library.

1. **Multi-model panels beat any single reviewer.** Different models have
   different blind spots. Run several on the *same* code; a finding flagged by
   two or more is high-confidence, a singleton is a lead to verify.
2. **Give every reviewer the full testing philosophy, verbatim.** Not a summary,
   not "it already knows." The asymmetry of an under-briefed reviewer is a
   process bug, not a model difference.
3. **Demand real-input evidence; reject mock-only findings.** A defect that only
   reproduces by monkeypatching internals usually isn't reachable in practice.
   Require an executed repro built from a real `.xlsx`, and reproduce it yourself
   before changing code.
4. **Convergence is non-monotonic and never reaches zero.** Yield drops fast then
   plateaus at a floor; a deep defect can still surface late. Measure *residual
   risk* (severity-weighted yield, a clean-streak, a confidence number) rather
   than chasing a "no bugs" proof.
5. **The late-stage defect class is symmetry gaps.** Once the structural bugs are
   gone, what remains is "a guard/behaviour present in one path but not its
   siblings" — row-split vs column-split, header-present vs header-absent, single
   region vs stacked regions, a method vs its convenience wrapper. Audit by
   building a path×behaviour matrix and finding the empty cell.
6. **CI is non-negotiable — it sees what local runs and reviewers cannot.**
   Version-specific code paths *skip* or pass locally on one dependency version, so
   a green local suite can be blind to them. CI must run tests + lint + type on
   every push and **matrix the dependency versions** (e.g. `openpyxl`), because an
   unconstrained dep can silently break a feature with zero red tests.
7. **Pin and bound dependencies, and test the boundaries.** An open-ended `>=`
   range will eventually pull a version that removed an API you call.
8. **Make the release decision explicit and measurable.** A rubric (gates +
   weighted score) plus a stop rule (two consecutive full-diversity clean
   panels) beats vibes. State which surfaces the signal covers and which rest on
   CI.
9. **Write down deliberate tradeoffs (a LIMITATIONS file).** It stops reviewers
   re-litigating settled decisions and stops agents "fixing" intended behaviour.
   The signal it works: a later reviewer *cites* it when triaging.
10. **Be honest in the bookkeeping.** Dismiss false positives with a stated
    reason; mark provisional vs final; keep the tree committed and the branch
    HEAD verified (shared environments can install broken deps or reset the
    checkout — confirm `git rev-parse HEAD` and restore the baseline after).

## Replicating this in another package

This approach is portable. The small set of files that make it repeatable:

- **`CONTRIBUTING.md`** (this file) — the testing philosophy and the review-panel
  process. Start here; the rest support it.
- **`LIMITATIONS.md`** — a committed snapshot of *intentional* design tradeoffs
  (four fields per entry: concern / decision / rationale / escape hatch).
  Reviewers read it first and do not re-report what it covers.
- **`RELEASE_READINESS.md`** + `release_readiness.json` + `scripts/readiness.py`
  — the release rubric (hard gates + weighted score) and the convergence metric,
  with a script that computes a number. Verify the gate can actually say *yes*
  for your model set.
- **`REVIEW_HISTORY.md`** — the narrative record: a TL;DR of the numbers, the
  panel-by-panel trajectory, and what each found/fixed.
- **`panel_prompt.template.md`** — the brief sent to every model slot each round.
- **CI** (`.github/workflows/ci.yml`) — run tests/lint/type on every push and
  matrix the dependency versions.

Minimum to start: `CONTRIBUTING.md` + `LIMITATIONS.md` + CI. Add the readiness
rubric and history file once panels begin, so the convergence signal is recorded
from the first round.
