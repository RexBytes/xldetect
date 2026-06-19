# Review History

A record of how this package was reviewed and hardened: the trajectory, the
issues found, and the fixes made. Methodology lives in `CONTRIBUTING.md`;
deliberate tradeoffs in `LIMITATIONS.md`; the release rubric in
`RELEASE_READINESS.md`.

## TL;DR

| Metric | Value |
|---|---|
| Multi-model review panels | 2 (3 models each: opus, sonnet, haiku) |
| Confirmed findings (panels) | 4 — 0 CRITICAL, 0 HIGH, 2 MEDIUM, 2 LOW, 0 NIT |
| Severity-weighted yield | 4.0 → 6.0 (non-monotonic; panel 2 went deeper) |
| Tests | 151 passing, 0 skipped; ruff + mypy clean; coverage 99% |
| Release-Readiness Score | 71.0 / 100 |
| Convergence | clean streak 0 of 2 required; confidence 0.00 |
| Verdict | NOT RELEASABLE — RRS < 90 and surface not yet converged (panels 1–2 both found real defects) |

The review kit (this file, `CONTRIBUTING.md`, `RELEASE_READINESS.md`,
`release_readiness.json`, `scripts/readiness.py`, `panel_prompt.template.md`)
was applied to the repository and the hard gates were wired up: `ruff` and
`mypy` were added to the dev extras and configured in `pyproject.toml`, and CI
runs tests/lint/type plus a dependency-version matrix. `scripts/readiness.py`
reports green gates at 99% coverage; the score is held below the release bar by
the convergence requirement, which is satisfied by running clean panels.

## Trajectory

Severity weights: CRITICAL=40, HIGH=10, MEDIUM=4, LOW=1, NIT=0.2.

| Panel | Findings | Weighted | Theme |
|---|---|---|---|
| 1 | 1 MEDIUM | 4.0 | Exception-normalisation gap in the openpyxl boundary |
| 2 | 1 MEDIUM, 2 LOW | 6.0 | Sibling-symmetry gap (header detection) + CLI/doc contract gaps |

## What each panel found and how it was fixed

- **1 — Exception-normalisation gap (`reader.py`).** Full-diversity panel
  (opus/sonnet/haiku). Opus surfaced a singleton MEDIUM: `load_grids` promised to
  normalise openpyxl's lower-level exceptions to `ValueError` for "corrupt, wrong
  format, not a zip" inputs, but its `except` chain missed two real cases — a
  valid zip with no `[Content_Types].xml` (a plain `.zip` renamed to `.xlsx`,
  raising a raw `KeyError`) and a malformed `[Content_Types].xml` (a corrupt
  Office file, raising `xml.etree`'s `ParseError`). Both escaped unnormalised and
  surfaced through the CLI as an uncaught traceback. The coordinator reproduced
  both with real `zipfile`-built inputs, widened the catch around `load_workbook`
  to normalise `KeyError`/`ParseError`, and pinned both at the `load_grids`
  boundary plus a CLI exit-code/no-traceback test (commit `5ea8a4c`). Sonnet and
  haiku independently found no new defects (82 and 60+ adversarial experiments).
- **2 — Header-detection symmetry gap + contract gaps (`headers.py`, `cli.py`,
  `decorative.py`).** Full-diversity panel; three singletons, haiku clean
  (commit `2acf741`). **MEDIUM (opus):** `_is_secondary_header` counted a *blank*
  candidate cell over a populated body as "type-distinct", so an ordinary first
  data row with an empty optional column was misread as a stacked header — the
  record was swallowed and `headers` taken from it. Fixed by matching the
  "comparable" rule of `score_header_row` (skip columns empty on either side).
  Notably this is the exact path Panel 1's opus slot probed and *cleared* — a
  deeper residual surfacing late, hidden behind the sibling guard. **LOW
  (sonnet):** `--header-threshold` out-of-range exited 1 (runtime) instead of 2
  (usage) like `--min-blank-rows`; added a `_unit_float` argparse validator.
  **LOW (sonnet):** `trim_decorative`'s docstring promised "returned unchanged"
  when every row is decorative, but the code keeps the last row (correct for
  detection — returning it unchanged makes forward-filled banners look like a
  table); corrected the docstring. Each fix landed with a four-corners/contract
  regression test (suite 141 → 151).

## Standing themes

- Convergence is non-monotonic and never reaches zero; measure residual risk.
  Panel 2 demonstrated this directly: weighted yield rose 4.0 → 6.0 as a deeper
  panel surfaced a residual (the header-swallowing MEDIUM) that Panel 1 had
  looked at and cleared.
- The late-stage defect class is symmetry gaps (a guard present in one path but
  not its siblings — row-split vs column-split, header-present vs header-absent,
  single region vs stacked).
- CI visibility: `openpyxl`/`xlfilldown` version-specific behaviour is invisible
  to a single-version local run — matrix it.

_Maintenance: append a row to the trajectory table and a bullet per new panel;
keep the TL;DR numbers in sync with `release_readiness.json`._
