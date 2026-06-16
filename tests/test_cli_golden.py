"""Golden-file tests pinning exact CLI output shape.

These compare byte-exact CLI output (with the volatile file path masked to
``<FILE>``) against committed golden files, so any formatting drift fails loudly
instead of silently breaking downstream scripts that parse the output.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import pytest
from conftest import make_workbook

from xldetect.cli import main

GOLDEN = Path(__file__).parent / "golden"


def _golden_workbook(tmp_path):
    """The single deterministic workbook the golden files were generated from."""
    path = tmp_path / "golden.xlsx"
    make_workbook(
        path,
        {
            "Sheet1": {
                "cells": [
                    {"coord": "A1", "value": "Sales Report"},
                    {"coord": "A3", "value": "Name", "bold": True},
                    {"coord": "B3", "value": "Amount", "bold": True},
                    {"coord": "A4", "value": "Alice"},
                    {"coord": "B4", "value": 10},
                    {"coord": "A5", "value": "Bob"},
                    {"coord": "B5", "value": 20},
                    {"coord": "A8", "value": "Region"},
                    {"coord": "B8", "value": "Total"},
                    {"coord": "A9", "value": "North"},
                    {"coord": "B9", "value": 30},
                ],
                "merges": ["A1:B1"],
            }
        },
    )
    return str(path)


def _run(args, mask):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(args)
    assert rc == 0
    return buf.getvalue().replace(mask, "<FILE>")


@pytest.mark.parametrize(
    "flags,golden_name",
    [
        ([], "inspect_text.txt"),
        (["--json"], "inspect_json.txt"),
        (["--xlfilldown"], "inspect_xlfilldown.txt"),
    ],
)
def test_cli_output_matches_golden(tmp_path, flags, golden_name):
    path = _golden_workbook(tmp_path)
    got = _run(["inspect", path, *flags], path)
    expected = (GOLDEN / golden_name).read_text()
    assert got == expected


def test_unknown_file_returns_exit_code_1(capsys):
    rc = main(["inspect", "/no/such/file.xlsx"])
    assert rc == 1
    assert "error" in capsys.readouterr().err


def test_corrupt_workbook_returns_exit_code_1_without_traceback(tmp_path, capsys):
    bad = tmp_path / "fake.xlsx"
    bad.write_text("not an excel file")
    rc = main(["inspect", str(bad)])
    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("xldetect: error:")
    assert "Traceback" not in err


def test_valid_min_blank_rows_runs(tmp_path, capsys):
    path = _golden_workbook(tmp_path)
    assert main(["inspect", path, "--min-blank-rows", "2"]) == 0
    assert "Region" in capsys.readouterr().out


@pytest.mark.parametrize("bad", ["0", "-1", "abc"])
def test_invalid_min_blank_is_usage_error(tmp_path, bad):
    path = _golden_workbook(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["inspect", path, "--min-blank-rows", bad])
    assert exc.value.code == 2  # argparse usage error


def test_json_and_xlfilldown_are_mutually_exclusive(tmp_path):
    path = _golden_workbook(tmp_path)
    with pytest.raises(SystemExit):
        main(["inspect", path, "--json", "--xlfilldown"])
