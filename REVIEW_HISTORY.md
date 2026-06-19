# Review History

A record of how this package was reviewed and hardened: the trajectory, the
issues found, and the fixes made. Methodology lives in `CONTRIBUTING.md`;
deliberate tradeoffs in `LIMITATIONS.md`; the release rubric in
`RELEASE_READINESS.md`.

## TL;DR

| Metric | Value |
|---|---|
| Multi-model review panels | 4 (3 models each: opus, sonnet, haiku) |
| Confirmed findings (panels) | 4 — 0 CRITICAL, 0 HIGH, 2 MEDIUM, 2 LOW, 0 NIT |
| Severity-weighted yield | 4.0 → 6.0 → 0.0 → 0.0 (two clean panels) |
| Tests | 151 passing, 0 skipped; ruff + mypy clean; coverage 99% |
| Release-Readiness Score | 94.3 / 100 |
| Convergence | clean streak 2 of 2; confidence 0.86 |
| Verdict | **RELEASABLE** — gates green, RRS ≥ 90, two consecutive full-diversity clean panels |

The review kit (this file, `CONTRIBUTING.md`, `RELEASE_READINESS.md`,
`release_readiness.json`, `scripts/readiness.py`, `panel_prompt.template.md`)
was applied to the repository and the hard gates were wired up: `ruff` and
`mypy` were added to the dev extras and configured in `pyproject.toml`, and CI
runs tests/lint/type plus a dependency-version matrix. Four review panels then
ran: panels 1–2 found and fixed four defects (2 MEDIUM, 2 LOW), and panels 3–4
came back clean at full diversity. With gates green, RRS 94.3, and a 2-of-2
clean streak, `scripts/readiness.py` now reports **RELEASABLE**.

## Trajectory

Severity weights: CRITICAL=40, HIGH=10, MEDIUM=4, LOW=1, NIT=0.2.

| Panel | Findings | Weighted | Theme |
|---|---|---|---|
| 1 | 1 MEDIUM | 4.0 | Exception-normalisation gap in the openpyxl boundary |
| 2 | 1 MEDIUM, 2 LOW | 6.0 | Sibling-symmetry gap (header detection) + CLI/doc contract gaps |
| 3 | none (clean) | 0.0 | First clean full-diversity panel; 2 NITs dismissed |
| 4 | none (clean) | 0.0 | Second clean panel (fresh surfaces); RELEASABLE reached |

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
- **3 — First clean panel.** Full-diversity panel (opus/sonnet/haiku); no new
  behavioural defects from any slot, and both Panel 2 fixes independently
  re-verified intact. The only residue was two NIT-level observations, each
  dismissed by its own reporter: an `orchestrate.py` docstring orientation typo
  ("1xN" → "Nx1" for the single-column degeneracy penalty, corrected in
  `9a8f795`, non-behavioural) and a self-consistent `data_start_row = max_row+1`
  artifact on header-only decorative regions (callers check `n_data_rows` first;
  no change). Opus also spawned a same-model sub-agent whose degeneracy-penalty
  candidate the slot adjudicated and rejected — the proposed fix would have
  halved the confidence of every legitimate single-record table. Weighted yield
  0.0; clean streak 1 of 2; RRS crosses 90 (91.4).
- **4 — Second clean panel; release reached.** Full-diversity panel steered into
  the surfaces panels 1–3 under-exercised: Unicode/exotic whitespace (zero-width
  space, NBSP), `_jsonable`/`to_dict` over the full object graph (error cells,
  rich text, datetimes), text-vs-JSON renderer agreement, style detection
  (gradient/indexed fills), sheet-name and ordering edges, coordinate overflow to
  Excel's limits, and an end-to-end `xlfilldown` ingest. No new defects from any
  slot. Three reviewer observations were all adjudicated non-defects: ZWS treated
  as text is consistent with the documented `str.strip()` contract; an
  embedded-newline header label is cosmetic (no sanitisation promised); a
  null-byte filename still exits 1 correctly. No code changes — HEAD stayed
  identical to the reviewed commit. Weighted yield 0.0; **clean streak 2 of 2;
  RRS 94.3 → RELEASABLE.**

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
