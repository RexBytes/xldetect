"""Header-row detection within a region.

This module exists to decide whether the top row(s) of a region are column
labels rather than data, and to extract those labels. It scores a candidate row
in ``[0, 1]`` from four cues and compares the score against a threshold:

* **populated** -- fraction of the region's columns the row fills (headers are
  usually fully populated);
* **text** -- fraction of the row's non-empty cells that are text;
* **distinct** -- fraction of columns where the candidate cell's kind differs
  from the dominant kind of the column body below it (labels over numbers/dates);
* **style** -- fraction of non-empty cells carrying a formatting cue
  (bold/fill/border/italic).

When the grid carries no style information at all, the style cue is dropped and
its weight is redistributed across the content cues, so content-only grids are
scored on their merits rather than penalised for missing styles.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ..grid import (
    KIND_EMPTY,
    KIND_TEXT,
    Grid,
    cell_kind,
)
from .regions import RawRegion

# Scoring weights. Two profiles: with style evidence and without. Each sums to 1.
_W_STYLED = {"populated": 0.25, "text": 0.30, "distinct": 0.25, "style": 0.20}
_W_CONTENT = {"populated": 0.30, "text": 0.40, "distinct": 0.30}


@dataclass
class HeaderResult:
    """Outcome of :func:`detect_header`.

    ``header_rows`` lists the absolute (1-based) rows judged to be header rows,
    top to bottom. ``header_row`` is the bottom-most of those -- the single row a
    consumer like ``xlfilldown`` should treat as *the* header. ``headers`` holds
    one label per region column (left to right); blank cells become ``""``.
    ``score`` is the score of the primary (top) candidate row.
    """

    has_header: bool
    header_rows: list[int] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    score: float = 0.0

    @property
    def header_row(self) -> int | None:
        """Bottom-most header row, or ``None`` when no header was detected."""
        return max(self.header_rows) if self.header_rows else None


def _column_body_kinds(
    grid: Grid, region: RawRegion, first_body_row: int
) -> dict[int, str]:
    """Dominant non-empty cell kind per column, over rows at/below ``first_body_row``."""
    out: dict[int, str] = {}
    for c in range(region.min_col, region.max_col + 1):
        counts: Counter[str] = Counter()
        for r in range(first_body_row, region.max_row + 1):
            k = cell_kind(grid.value_at(r, c))
            if k != KIND_EMPTY:
                counts[k] += 1
        out[c] = counts.most_common(1)[0][0] if counts else KIND_EMPTY
    return out


def score_header_row(grid: Grid, region: RawRegion, row: int, body_row: int) -> float:
    """Score a single candidate ``row`` as a header, using the body below ``body_row``.

    Returns a value in ``[0, 1]``. ``body_row`` is the first row treated as data
    for the type-distinction cue (normally ``row + 1``).
    """
    cols = list(range(region.min_col, region.max_col + 1))
    n = len(cols)
    if n == 0:
        return 0.0

    kinds = [cell_kind(grid.value_at(row, c)) for c in cols]
    nonempty_kinds = [k for k in kinds if k != KIND_EMPTY]

    populated = len(nonempty_kinds) / n
    text = (
        sum(1 for k in nonempty_kinds if k == KIND_TEXT) / len(nonempty_kinds)
        if nonempty_kinds
        else 0.0
    )

    body_kinds = _column_body_kinds(grid, region, body_row)
    distinct = comparable = 0
    for c, k in zip(cols, kinds):
        bk = body_kinds.get(c, KIND_EMPTY)
        if bk == KIND_EMPTY or k == KIND_EMPTY:
            continue
        comparable += 1
        if k != bk:
            distinct += 1
    distinct_frac = distinct / comparable if comparable else 0.0

    if grid.has_styles:
        decorated = [
            grid.style_at(row, c) for c, k in zip(cols, kinds) if k != KIND_EMPTY
        ]
        style_frac = (
            sum(1 for s in decorated if s.is_decorated()) / len(decorated)
            if decorated
            else 0.0
        )
        w = _W_STYLED
        return (
            w["populated"] * populated
            + w["text"] * text
            + w["distinct"] * distinct_frac
            + w["style"] * style_frac
        )
    w = _W_CONTENT
    return (
        w["populated"] * populated
        + w["text"] * text
        + w["distinct"] * distinct_frac
    )


def _is_secondary_header(
    grid: Grid, region: RawRegion, row: int, threshold: float
) -> bool:
    """Decide whether ``row`` is an additional (stacked) header row.

    A secondary header row is held to a stricter bar than the primary, to avoid
    swallowing the first data row or a stray annotation: every non-empty cell
    must be text (labels, never numbers/dates), at least half of the region's
    columns must be populated, the row must clear ``threshold``, and it must be
    type-distinct from the body below it in at least half of the comparable
    columns. In an all-text table the body is also text, so distinctness fails
    and only the single top row is taken as the header.
    """
    cols = list(range(region.min_col, region.max_col + 1))
    kinds = [cell_kind(grid.value_at(row, c)) for c in cols]
    nonempty = [k for k in kinds if k != KIND_EMPTY]
    if not nonempty or any(k != KIND_TEXT for k in nonempty):
        return False
    if len(nonempty) / len(cols) < 0.5:
        return False
    if score_header_row(grid, region, row, row + 1) < threshold:
        return False
    body_kinds = _column_body_kinds(grid, region, row + 1)
    comparable = distinct = 0
    for c, k in zip(cols, kinds):
        bk = body_kinds.get(c, KIND_EMPTY)
        if bk == KIND_EMPTY:
            continue
        comparable += 1
        if k != bk:
            distinct += 1
    return comparable > 0 and (distinct / comparable) >= 0.5


def _row_labels(grid: Grid, region: RawRegion, row: int) -> list[str]:
    """Extract one label string per region column from ``row``; blanks become ``""``."""
    labels = []
    for c in range(region.min_col, region.max_col + 1):
        v = grid.value_at(row, c)
        labels.append("" if v is None else str(v).strip())
    return labels


def detect_header(
    grid: Grid,
    region: RawRegion,
    *,
    threshold: float = 0.5,
    max_header_rows: int = 2,
) -> HeaderResult:
    """Detect the header row(s) at the top of ``region``.

    The first region row is scored with :func:`score_header_row`; if its score is
    ``>= threshold`` it is taken as a header. Up to ``max_header_rows - 1``
    further consecutive rows are accepted as additional (stacked) header rows
    only if they pass the stricter :func:`_is_secondary_header` test (all-text and
    type-distinct from the body below), which prevents the first data row from
    being swallowed. The reported ``headers`` come from the bottom-most header
    row, since that is the row that labels the data columns.

    When no header clears the threshold, ``has_header`` is ``False`` and
    ``headers`` is empty; the caller should treat the whole region as data.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold must be in [0, 1] (got {threshold}).")

    first = region.min_row
    primary_score = score_header_row(grid, region, first, first + 1)
    if primary_score < threshold:
        return HeaderResult(has_header=False, header_rows=[], headers=[], score=primary_score)

    header_rows = [first]
    row = first + 1
    while len(header_rows) < max_header_rows and row < region.max_row:
        if not _is_secondary_header(grid, region, row, threshold):
            break
        header_rows.append(row)
        row += 1

    bottom = max(header_rows)
    return HeaderResult(
        has_header=True,
        header_rows=header_rows,
        headers=_row_labels(grid, region, bottom),
        score=primary_score,
    )
