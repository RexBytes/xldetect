<!--
Release title (paste into the GitHub release "title" field):

  xldetect 1.0.1 — Review-hardened bug-fix release

Tag: v1.0.1   Target: main
Everything below the line is the release body.
-->

---

# xldetect 1.0.1

A bug-fix release. No API changes and no new features — `xldetect` still does
exactly what 1.0.0 did, but four defects surfaced by a competitive multi-model
review were fixed, each with a regression test. Drop-in upgrade from 1.0.0.

## Fixes

- **Malformed-workbook errors no longer escape as a traceback.** A zip-shaped
  file that is not a real `.xlsx` — a plain `.zip` renamed to `.xlsx` (no
  `[Content_Types].xml`), or a corrupt/truncated Office file — now raises a clean
  `ValueError` from `inspect_path()`/`load_grids()` and exits the CLI with the
  usual `xldetect: error: …` message instead of an uncaught `KeyError` /
  `ParseError`.
- **A first data row with a blank optional column is no longer mistaken for a
  header.** Header detection treated a blank candidate cell over a populated
  column as "type-distinct", so an ordinary record whose optional numeric/date
  field was empty could be swallowed as a second header row — losing that row and
  taking the headers from it. Stacked-header detection now requires both the
  candidate and the body cell to be populated before comparing them.
- **`--header-threshold` validates like the other options.** An out-of-range or
  non-numeric value is now a usage error (exit code 2), matching
  `--min-blank-rows`, instead of surfacing as a runtime error (exit code 1).
- **Docstring corrections** for the decorative-trim and confidence-degeneracy
  behaviours (no behavioural change).

## Upgrade

    pip install --upgrade xldetect

Requires Python 3.11+. Runtime dependency: `openpyxl>=3.1`.

## Quality

This release was put through a four-round **competitive multi-model review**
(opus, sonnet, haiku on the same brief each round; see `CONTRIBUTING.md` and
`REVIEW_HISTORY.md`):

- Panels 1–2 found and fixed the four defects above (2 MEDIUM, 2 LOW). Every one
  was a *singleton* — found by a single model and missed by the other two — which
  is the case for running diverse reviewers rather than one.
- Panels 3–4 came back clean at full diversity, satisfying the release rule (all
  gates green, RRS ≥ 90, two consecutive full-diversity clean panels).
- `scripts/readiness.py`: gates green, **RRS 94.3/100**, convergence confidence
  0.86 → **RELEASABLE**.

**151 tests** (truth-table corners, threshold pinning, Hypothesis property
tests, golden CLI files, and a live `xlfilldown` round-trip), **99% coverage**;
`ruff` + `mypy` clean. CI runs on Python 3.11 and 3.12 across an `openpyxl`
version matrix.

**Full API, scope, and design rationale:** see README.md, SKILL.md, and
LIMITATIONS.md. **Review trajectory:** see REVIEW_HISTORY.md.
