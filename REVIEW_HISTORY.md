# Review History

A record of how this package was reviewed and hardened: the trajectory, the
issues found, and the fixes made. Methodology lives in `CONTRIBUTING.md`;
deliberate tradeoffs in `LIMITATIONS.md`; the release rubric in
`RELEASE_READINESS.md`.

## TL;DR

| Metric | Value |
|---|---|
| Multi-model review panels | 0 (kit installed; no panel run yet) |
| Confirmed findings (panels) | — |
| Severity-weighted yield | — |
| Tests | 138 passing, 0 skipped; ruff + mypy clean; coverage 99% |
| Release-Readiness Score | 71.0 / 100 |
| Convergence | clean streak 0 of 2 required; confidence 0.00 |
| Verdict | NOT RELEASABLE — no review panels run yet (gates green) |

The review kit (this file, `CONTRIBUTING.md`, `RELEASE_READINESS.md`,
`release_readiness.json`, `scripts/readiness.py`, `panel_prompt.template.md`)
was applied to the repository and the hard gates were wired up: `ruff` and
`mypy` were added to the dev extras and configured in `pyproject.toml`, and CI
runs tests/lint/type plus a dependency-version matrix. `scripts/readiness.py`
reports green gates at 99% coverage; the score is held below the release bar
only by the convergence requirement, which is satisfied by running panels.

## Trajectory

Severity weights: CRITICAL=40, HIGH=10, MEDIUM=4, LOW=1, NIT=0.2.

| Panel | Findings | Weighted | Theme |
|---|---|---|---|
| _(none yet)_ | — | — | — |

## What each panel found and how it was fixed

- _No panels have been run yet. Append one bullet per panel here, and a row to
  the trajectory table, keeping the TL;DR numbers in sync with
  `release_readiness.json`._

## Standing themes

- Convergence is non-monotonic and never reaches zero; measure residual risk.
- The late-stage defect class is symmetry gaps (a guard present in one path but
  not its siblings — row-split vs column-split, header-present vs header-absent,
  single region vs stacked).
- CI visibility: `openpyxl`/`xlfilldown` version-specific behaviour is invisible
  to a single-version local run — matrix it.

_Maintenance: append a row to the trajectory table and a bullet per new panel;
keep the TL;DR numbers in sync with `release_readiness.json`._
