"""Contract tests for coordinate helpers."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from xldetect.coords import a1, a1_range, column_index, column_letter


@pytest.mark.parametrize(
    "index,letters",
    [(1, "A"), (26, "Z"), (27, "AA"), (52, "AZ"), (702, "ZZ"), (703, "AAA")],
)
def test_column_letter_known_values(index, letters):
    assert column_letter(index) == letters
    assert column_index(letters) == index


def test_column_letter_rejects_below_one():
    with pytest.raises(ValueError):
        column_letter(0)
    with pytest.raises(ValueError):
        column_letter(-5)


@pytest.mark.parametrize("bad", ["", "  ", "A1", "3", "Z9", "!"])
def test_column_index_rejects_non_alpha(bad):
    with pytest.raises(ValueError):
        column_index(bad)


def test_column_index_is_case_insensitive_and_strips():
    assert column_index("  aa ") == 27


def test_a1_basic():
    assert a1(3, 2) == "B3"
    assert a1(1, 1) == "A1"


def test_a1_rejects_below_one():
    with pytest.raises(ValueError):
        a1(0, 1)
    with pytest.raises(ValueError):
        a1(1, 0)


def test_a1_range_including_single_cell():
    assert a1_range(2, 2, 6, 6) == "B2:F6"
    # single-cell rectangle still renders as a range, for uniform downstream parsing
    assert a1_range(3, 3, 3, 3) == "C3:C3"


@given(st.integers(min_value=1, max_value=20000))
def test_column_letter_index_round_trip(n):
    assert column_index(column_letter(n)) == n
