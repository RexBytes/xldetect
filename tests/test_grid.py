"""Contract tests for cell_kind classification, CellStyle, and Grid accessors."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from fractions import Fraction

import pytest

from xldetect.grid import (
    KIND_BOOL,
    KIND_DATE,
    KIND_EMPTY,
    KIND_NUMBER,
    KIND_TEXT,
    CellStyle,
    Grid,
    cell_kind,
)


def test_cell_kind_none_is_empty():
    assert cell_kind(None) == KIND_EMPTY


@pytest.mark.parametrize("s", ["", " ", "\t", "\n  \n"])
def test_cell_kind_blank_strings_are_empty(s):
    assert cell_kind(s) == KIND_EMPTY


@pytest.mark.parametrize("s", ["x", " a ", "0", "Name"])
def test_cell_kind_nonblank_strings_are_text(s):
    assert cell_kind(s) == KIND_TEXT


def test_cell_kind_bool_checked_before_number():
    # bool is a subclass of int; it must classify as bool, not number.
    assert cell_kind(True) == KIND_BOOL
    assert cell_kind(False) == KIND_BOOL


@pytest.mark.parametrize("n", [0, 1, -3, 3.14, Decimal("1.5"), Fraction(1, 2), 2 + 1j])
def test_cell_kind_numbers(n):
    assert cell_kind(n) == KIND_NUMBER


@pytest.mark.parametrize(
    "d",
    [
        dt.date(2026, 1, 1),
        dt.datetime(2026, 1, 1, 12, 0),
        dt.time(9, 30),
    ],
)
def test_cell_kind_dates(d):
    assert cell_kind(d) == KIND_DATE


def test_cell_kind_unknown_object_is_text():
    class Weird:
        pass

    assert cell_kind(Weird()) == KIND_TEXT


def test_cellstyle_is_decorated_truth_table():
    assert CellStyle().is_decorated() is False
    assert CellStyle(bold=True).is_decorated() is True
    assert CellStyle(filled=True).is_decorated() is True
    assert CellStyle(bordered=True).is_decorated() is True
    assert CellStyle(italic=True).is_decorated() is True
    assert CellStyle(bold=True, italic=True).is_decorated() is True


def test_grid_accessors_and_defaults():
    g = Grid(values={(1, 1): "a", (2, 3): 5})
    assert g.is_occupied(1, 1) is True
    assert g.is_occupied(9, 9) is False
    assert g.value_at(2, 3) == 5
    assert g.value_at(9, 9) is None
    # missing style returns a default all-False style, not KeyError
    assert g.style_at(9, 9) == CellStyle()
    assert g.occupied == {(1, 1), (2, 3)}


def test_grid_bounds():
    g = Grid(values={(2, 2): "a", (5, 7): "b"})
    assert g.max_row == 5
    assert g.max_col == 7


def test_grid_empty_bounds_are_zero():
    g = Grid()
    assert g.max_row == 0
    assert g.max_col == 0
    assert g.occupied == set()
    assert g.has_styles is False


def test_grid_has_styles():
    assert Grid(values={(1, 1): "a"}, styles={(1, 1): CellStyle()}).has_styles is True
