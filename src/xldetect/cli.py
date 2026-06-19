"""Command-line interface for xldetect.

A thin ``argparse`` wrapper around :func:`xldetect.orchestrate.inspect_path` and
the renderers in :mod:`xldetect.report`. All business logic lives in the library;
this module only parses arguments, selects an output renderer, and maps outcomes
to process exit codes.

Exit codes:
    0  success
    1  runtime error (missing file, unknown sheet, bad workbook)
    2  usage error (argparse handles this)
"""

from __future__ import annotations

import argparse
import json
import sys

from .integration import workbook_to_xlfilldown_plans
from .orchestrate import inspect_path
from .report import format_json, format_text


def _positive_int(value: str) -> int:
    """argparse type: accept only integers >= 1 (for blank-gap thresholds)."""
    try:
        n = int(value)
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"expected an integer, got {value!r}") from err
    if n < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {n}")
    return n


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xldetect",
        description="Detect table-like data regions and headers in Excel worksheets.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    inspect = sub.add_parser(
        "inspect", help="Detect and preview data regions in a workbook."
    )
    inspect.add_argument("file", help="Path to an .xlsx workbook.")
    inspect.add_argument(
        "--sheet",
        action="append",
        dest="sheets",
        metavar="NAME",
        help="Limit to this sheet (repeatable). Default: all sheets.",
    )
    inspect.add_argument(
        "--min-blank-rows",
        type=_positive_int,
        default=1,
        help="Blank-row gap that separates stacked regions (default: 1, min: 1).",
    )
    inspect.add_argument(
        "--min-blank-cols",
        type=_positive_int,
        default=1,
        help="Blank-column gap that separates side-by-side regions (default: 1, min: 1).",
    )
    inspect.add_argument(
        "--header-threshold",
        type=float,
        default=0.5,
        help="Minimum header score [0-1] to accept a header row (default: 0.5).",
    )
    out = inspect.add_mutually_exclusive_group()
    out.add_argument(
        "--json", action="store_true", help="Emit the full report as JSON."
    )
    out.add_argument(
        "--xlfilldown",
        action="store_true",
        help="Emit one xlfilldown plan per region as JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "inspect":
        try:
            report = inspect_path(
                args.file,
                sheets=args.sheets,
                min_blank_rows=args.min_blank_rows,
                min_blank_cols=args.min_blank_cols,
                header_threshold=args.header_threshold,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"xldetect: error: {exc}", file=sys.stderr)
            return 1

        if args.xlfilldown:
            print(json.dumps(workbook_to_xlfilldown_plans(report), indent=2, sort_keys=True))
        elif args.json:
            print(format_json(report))
        else:
            print(format_text(report))
        return 0

    parser.error(f"unknown command: {args.command}")  # pragma: no cover
    return 2  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
