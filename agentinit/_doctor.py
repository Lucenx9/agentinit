"""Diagnostic command: run all checks and suggest fix commands."""

from __future__ import annotations

import os
from argparse import Namespace
from pathlib import Path
from typing import Callable

from agentinit._profiles import looks_like_minimal_profile


def _read_text(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def _check_missing_files(
    dest: str,
    files: list[str],
) -> list[tuple[str, str]]:
    """Return (message, fix_hint) pairs for missing managed files."""
    issues: list[tuple[str, str]] = []
    for rel in files:
        path = os.path.join(dest, rel)
        if not os.path.isfile(path):
            issues.append((f"{rel} is missing", "agentinit init"))
    return issues


def _check_tbd_content(
    dest: str,
    files: list[str],
) -> list[tuple[str, str]]:
    """Return (message, fix_hint) pairs for files containing TBD."""
    issues: list[tuple[str, str]] = []
    for rel in files:
        path = os.path.join(dest, rel)
        content = _read_text(path)
        if content and "TBD" in content:
            issues.append((f"{rel} contains TBD placeholders", f"edit {rel}"))
    return issues


def _check_line_budgets(
    dest: str,
    files: list[str],
) -> list[tuple[str, str]]:
    """Return (message, fix_hint) for oversized always-hot files."""
    always_hot = {
        f
        for f in files
        if not f.startswith("docs/")
        and f
        not in {
            ".gitignore",
            ".contextlintrc.json",
        }
    }
    issues: list[tuple[str, str]] = []
    for rel in always_hot:
        path = os.path.join(dest, rel)
        content = _read_text(path)
        if content:
            lines = len(content.splitlines())
            if lines >= 300:
                issues.append(
                    (
                        f"{rel} is {lines} lines (hard limit 300)",
                        f"move details from {rel} to docs/",
                    )
                )
    return issues


def _check_sync_drift(
    dest: str,
    template_dir: str,
    minimal_mode: bool,
    missing_files: set[str],
) -> list[tuple[str, str]]:
    """Return (message, fix_hint) for out-of-sync router files.

    Files already in *missing_files* are skipped to avoid duplicate reports.
    """
    from agentinit._sync import (
        FULL_SYNC_ROUTER_FILES,
        MINIMAL_SYNC_ROUTER_FILES,
        _template_path_for,
    )

    router_files = MINIMAL_SYNC_ROUTER_FILES if minimal_mode else FULL_SYNC_ROUTER_FILES
    issues: list[tuple[str, str]] = []

    for rel in router_files:
        if rel in missing_files:
            continue

        tmpl_path = _template_path_for(rel, template_dir, minimal_mode)
        if not os.path.isfile(tmpl_path):
            continue

        dst = os.path.join(dest, rel)
        if not os.path.isfile(dst):
            continue

        expected = _read_text(tmpl_path)
        current = _read_text(dst)
        if expected and current != expected:
            issues.append((f"{rel} is out of sync", "agentinit sync"))

    return issues


def _check_llms_freshness(dest: str) -> list[tuple[str, str]]:
    """Check if llms.txt exists and has no unconfigured placeholders."""
    llms_path = os.path.join(dest, "llms.txt")
    if not os.path.isfile(llms_path):
        return [("llms.txt is missing", "agentinit refresh-llms")]
    content = _read_text(llms_path)
    if content and "(not configured" in content:
        return [("llms.txt has unconfigured fields", "agentinit refresh-llms")]
    return []


def _check_contextlint(
    dest: str, minimal_mode: bool, managed_files: list[str]
) -> list[tuple[str, str]]:
    """Run contextlint and return issues with fix hints."""
    try:
        from agentinit.contextlint_adapter import get_checks_module

        checks_mod = get_checks_module()
        selected_paths = None
        if minimal_mode:
            selected_paths = {p for p in managed_files if p.endswith((".md", ".mdc"))}

        try:
            result = checks_mod.run_checks(
                root=Path(dest), selected_paths=selected_paths
            )
        except TypeError:
            result = checks_mod.run_checks(root=Path(dest))

        issues: list[tuple[str, str]] = []
        for diag in result.diagnostics:
            if diag.hard:
                loc = f"{diag.path}:{diag.lineno}" if diag.lineno else diag.path
                if "broken ref" in diag.message:
                    issues.append(
                        (f"{loc}: {diag.message}", "fix or remove the broken reference")
                    )
                elif "duplicate" in diag.message:
                    issues.append(
                        (f"{loc}: {diag.message}", "consolidate duplicated content")
                    )
                else:
                    issues.append((f"{loc}: {diag.message}", "agentinit lint"))
        return issues
    except Exception:
        return [("contextlint checks unavailable", "pip install agentinit")]


def cmd_doctor(
    args: Namespace,
    *,
    managed_files: list[str],
    minimal_managed_files: list[str],
    template_dir: str,
    resolves_within: Callable[[str, str], bool],
) -> None:
    """Run all checks and print actionable fix suggestions."""
    dest = os.path.abspath(".")
    explicit_minimal = bool(getattr(args, "minimal", False))
    detected_minimal = not explicit_minimal and looks_like_minimal_profile(dest)
    minimal_mode = explicit_minimal or detected_minimal
    files = minimal_managed_files if minimal_mode else managed_files

    print("agentinit doctor")
    print(f"Directory: {dest}")
    if explicit_minimal:
        print("Profile: minimal")
    elif detected_minimal:
        print("Profile: minimal (auto-detected)")
    print()

    all_issues: list[tuple[str, str]] = []

    # 1. Missing files
    missing_issues = _check_missing_files(dest, files)
    all_issues.extend(missing_issues)
    missing_rels = {msg.split(" is missing")[0] for msg, _ in missing_issues}

    # 2. TBD content
    all_issues.extend(_check_tbd_content(dest, files))

    # 3. Line budgets
    all_issues.extend(_check_line_budgets(dest, files))

    # 4. Sync drift (skip files already reported as missing)
    if os.path.isfile(os.path.join(dest, "AGENTS.md")):
        all_issues.extend(
            _check_sync_drift(dest, template_dir, minimal_mode, missing_rels)
        )

    # 5. llms.txt freshness (skip if already reported as missing)
    if "llms.txt" not in missing_rels:
        all_issues.extend(_check_llms_freshness(dest))

    # 6. Contextlint
    all_issues.extend(_check_contextlint(dest, minimal_mode, files))

    if not all_issues:
        print("All checks passed. Project is healthy.")
        return

    # Deduplicate by message
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for msg, fix in all_issues:
        if msg not in seen:
            seen.add(msg)
            unique.append((msg, fix))

    print(f"Found {len(unique)} issue(s):\n")
    for msg, fix in unique:
        print(f"  x {msg}")
        print(f"    fix: {fix}")
    print()

    # Group fixes by command for a summary
    fix_commands: dict[str, int] = {}
    for _, fix in unique:
        if fix.startswith("agentinit "):
            fix_commands[fix] = fix_commands.get(fix, 0) + 1

    if fix_commands:
        print("Quick fixes:")
        for cmd in sorted(fix_commands):
            print(f"  $ {cmd}")
