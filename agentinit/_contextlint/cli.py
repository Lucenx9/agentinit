"""CLI entry point for contextlint (vendored copy)."""

from __future__ import annotations

import argparse
import json as _json
import sys
from pathlib import Path

from agentinit._contextlint import __version__
from agentinit._contextlint.checks import (
    Diagnostic,
    LintResult,
    load_config,
    run_checks,
    top_offenders,
)

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_HARD_PREFIX = "  ERROR"
_SOFT_PREFIX = "  warn "


def _loc(d: Diagnostic) -> str:
    return f"{d.path}:{d.lineno}" if d.lineno else d.path


def _format_diagnostic(d: Diagnostic) -> str:
    prefix = _HARD_PREFIX if d.hard else _SOFT_PREFIX
    return f"{prefix}  {_loc(d)}: {d.message}"


def _print_text(result: LintResult) -> None:
    if not result.diagnostics:
        print("contextlint: all clear ✓")
        return

    hards = [d for d in result.diagnostics if d.hard]
    softs = [d for d in result.diagnostics if not d.hard]

    if softs:
        print("Warnings:")
        for d in softs:
            print(_format_diagnostic(d))

    if hards:
        if softs:
            print()
        print("Errors:")
        for d in hards:
            print(_format_diagnostic(d))

    offenders = top_offenders(result)
    if offenders:
        print()
        print("Top offenders by size:")
        for path, size in offenders:
            print(f"  {path}: {size} lines")

    print()
    total = len(result.diagnostics)
    print(
        f"contextlint: {total} issue{'s' if total != 1 else ''} "
        f"({len(hards)} error{'s' if len(hards) != 1 else ''}, "
        f"{len(softs)} warning{'s' if len(softs) != 1 else ''})"
    )


def _print_json(result: LintResult) -> None:
    hards = [d for d in result.diagnostics if d.hard]
    softs = [d for d in result.diagnostics if not d.hard]
    output = {
        "diagnostics": [
            {
                "path": d.path,
                "lineno": d.lineno,
                "message": d.message,
                "hard": d.hard,
            }
            for d in result.diagnostics
        ],
        "file_sizes": result.file_sizes,
        "summary": {
            "total": len(result.diagnostics),
            "errors": len(hards),
            "warnings": len(softs),
        },
    }
    print(_json.dumps(output, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="contextlint",
        description="Lint AI agent context files for bloat, broken refs, and duplication.",
    )
    parser.add_argument(
        "--version", action="version", version=f"contextlint {__version__}"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="check",
        choices=["check"],
        help="Sub-command to run (default: check).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Repository root to lint (default: current directory).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to config file (default: auto-detect .contextlintrc.json).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--no-dup",
        action="store_true",
        default=False,
        help="Disable duplicate-block detection.",
    )

    args = parser.parse_args(argv)

    root = args.root.resolve()
    config = load_config(root, config_path=args.config)
    result = run_checks(root, config=config, check_dup=not args.no_dup)

    if args.format == "json":
        _print_json(result)
    else:
        _print_text(result)

    return 1 if result.has_hard else 0
