"""Status command implementation for `agentinit status`."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class StatusState:
    missing: list[str] = field(default_factory=list)
    tbd: list[str] = field(default_factory=list)
    hard_violations: list[str] = field(default_factory=list)
    broken_refs: list[str] = field(default_factory=list)
    file_sizes: list[tuple[str, int]] = field(default_factory=list)
    contextlint_hard: bool = False
    contextlint_failed: bool = False


def _print_status_header(dest: str) -> None:
    print("Agent Context Status")
    print(f"Directory: {dest}\n")


def _is_missing_path(path: str) -> tuple[bool, str]:
    if os.path.islink(path) and not os.path.exists(path):
        return True, "broken symlink"
    if not os.path.exists(path):
        return True, "missing"
    if not os.path.isfile(path):
        return True, "not a file"
    return False, ""


def _is_always_loaded(rel: str) -> bool:
    return not rel.startswith("docs/") and rel not in {
        ".gitignore",
        ".contextlintrc.json",
    }


def _build_file_messages(
    rel: str, content: str, line_count: int, state: StatusState
) -> tuple[str, list[str], list[str]]:
    symbol = "+"
    msgs: list[str] = []
    hints: list[str] = []

    if "TBD" in content:
        state.tbd.append(rel)
        symbol = "!"
        msgs.append("(contains TBD, needs update)")

    if line_count >= 300 and _is_always_loaded(rel):
        state.hard_violations.append(rel)
        symbol = "x"
        msgs.append(f"({line_count} lines >= 300)")
        if "CLAUDE.md" in rel or "GEMINI.md" in rel:
            hints.append(
                f"Move details to docs/ and keep {os.path.basename(rel)} as a router (10–20 lines)."
            )
        elif "AGENTS.md" in rel:
            hints.append("Split AGENTS.md into topic docs and link them.")
        else:
            hints.append(f"Reduce size of {rel} to keep context lean.")
        return symbol, msgs, hints

    if line_count >= 200:
        if symbol != "x":
            symbol = "!"
        msgs.append(f"({line_count} lines >= 200)")
        if _is_always_loaded(rel):
            hints.append(
                f"Consider moving details from {os.path.basename(rel)} to docs/."
            )
        else:
            hints.append("Consider splitting this document if it grows further.")

    return symbol, msgs, hints


def _print_file_status(
    rel: str, symbol: str, msgs: list[str], hints: list[str]
) -> None:
    msg_str = " ".join(msgs)
    print(f"  {symbol} {rel} {msg_str}".rstrip())
    for hint in hints:
        print(f"      Hint: {hint}")


def _collect_agent_ref_candidates(content: str, lines: list[str]) -> set[str]:
    md_links = re.findall(r"\[.*?\]\(([^)]+)\)", content)
    code_links = re.findall(r"`([^`\n]+)`", content)
    potential_paths = set(md_links + code_links)

    for line in lines:
        line = line.strip()
        if (
            line
            and " " not in line
            and ("/" in line or "\\" in line)
            and not line.startswith("#")
            and "](" not in line
        ):
            potential_paths.add(line)
    return potential_paths


def _normalize_ref(value: str) -> str:
    value = value.split("#", 1)[0]
    value = value.split("?", 1)[0]
    value = value.strip()
    if " " in value:
        value = value.split()[0]
    return value


def _is_valid_ref_candidate(value: str) -> bool:
    if not value:
        return False
    if value.startswith(("http://", "https://", "mailto:", "/")):
        return False
    if "*" in value:
        return False
    return (
        "/" in value
        or "\\" in value
        or value.endswith((".md", ".mdc", ".txt", ".py", ".yml", ".yaml"))
    )


def _check_agents_refs(
    dest: str,
    content: str,
    lines: list[str],
    state: StatusState,
    resolves_within: Callable[[str, str], bool],
    minimal_mode: bool,
    minimal_ref_paths: set[str],
) -> None:
    seen_broken: set[str] = set()
    dest_real = os.path.realpath(dest)

    for raw in _collect_agent_ref_candidates(content, lines):
        ref = _normalize_ref(raw)
        if not _is_valid_ref_candidate(ref):
            continue
        norm_ref = os.path.normpath(ref).replace("\\", "/")
        if minimal_mode and norm_ref not in minimal_ref_paths:
            continue

        target_path = os.path.join(dest_real, ref)
        if not resolves_within(dest_real, target_path):
            continue

        target_real = os.path.realpath(target_path)
        if os.path.exists(target_real) or norm_ref in seen_broken:
            continue

        seen_broken.add(norm_ref)
        state.broken_refs.append(norm_ref)
        print(f"      x Broken reference: {norm_ref}")
        print(
            f"      Hint: Fix broken link: create {norm_ref} or remove the reference."
        )


def _check_single_file(
    rel: str,
    dest: str,
    state: StatusState,
    resolves_within: Callable[[str, str], bool],
    minimal_mode: bool,
    minimal_ref_paths: set[str],
) -> None:
    path = os.path.join(dest, rel)
    is_missing, reason = _is_missing_path(path)
    if is_missing:
        state.missing.append(rel)
        print(f"  x {rel} ({reason})")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        state.missing.append(rel)
        print(f"  x {rel} (unreadable)")
        return

    lines = content.splitlines()
    line_count = len(lines)
    state.file_sizes.append((rel, line_count))
    symbol, msgs, hints = _build_file_messages(rel, content, line_count, state)
    _print_file_status(rel, symbol, msgs, hints)

    if rel == "AGENTS.md":
        _check_agents_refs(
            dest,
            content,
            lines,
            state,
            resolves_within,
            minimal_mode,
            minimal_ref_paths,
        )


def _run_contextlint(dest: str, state: StatusState) -> None:
    try:
        from agentinit.contextlint_adapter import get_checks_module

        checks_mod = get_checks_module()
        lint_result = checks_mod.run_checks(root=__import__("pathlib").Path(dest))
        hard_diags = [d for d in lint_result.diagnostics if d.hard]
        soft_diags = [d for d in lint_result.diagnostics if not d.hard]
        if lint_result.diagnostics:
            print("\nContext checks (contextlint):")
            for diag in lint_result.diagnostics:
                prefix = "ERROR" if diag.hard else "warn"
                loc = f"{diag.path}:{diag.lineno}" if diag.lineno else diag.path
                print(f"  {prefix}  {loc}: {diag.message}")
            offenders = checks_mod.top_offenders(lint_result)
            if offenders:
                print("\n  Top offenders by size:")
                for path, size in offenders:
                    print(f"    {path}: {size} lines")
            print(
                f"\n  contextlint: {len(hard_diags)} error(s), {len(soft_diags)} warning(s)"
            )
            if hard_diags:
                state.contextlint_hard = True
    except Exception as exc:  # pragma: no cover - defensive failure mode
        state.contextlint_failed = True
        state.contextlint_hard = True
        print(f"Warning: contextlint checks unavailable: {exc}", file=sys.stderr)


def _issue_list(state: StatusState) -> list[str]:
    issues: list[str] = []
    if state.missing:
        issues.append(f"{len(state.missing)} missing")
    if state.tbd:
        issues.append(f"{len(state.tbd)} incomplete")
    if state.hard_violations:
        issues.append(f"{len(state.hard_violations)} too large")
    if state.broken_refs:
        issues.append(f"{len(state.broken_refs)} broken refs")
    if state.contextlint_failed:
        issues.append("contextlint unavailable")
    elif state.contextlint_hard:
        issues.append("contextlint errors")
    return issues


def _print_top_offenders(state: StatusState) -> None:
    print("Top offenders:")
    if state.file_sizes:
        filtered = [(f, n) for f, n in state.file_sizes if f != ".gitignore"]
        filtered.sort(key=lambda x: x[1], reverse=True)
        for f_rel, f_lines in filtered[:3]:
            print(f"  {f_rel} ({f_lines} lines)")
    if state.broken_refs:
        print(f"  AGENTS.md: {len(state.broken_refs)} broken references")
    print()


def _has_issues(state: StatusState) -> bool:
    return bool(
        state.missing
        or state.tbd
        or state.hard_violations
        or state.broken_refs
        or state.contextlint_hard
    )


def cmd_status(
    args,
    *,
    managed_files: list[str],
    minimal_managed_files: list[str],
    resolves_within: Callable[[str, str], bool],
) -> None:
    """Show the status of agentinit context files in the current directory."""
    dest = os.path.abspath(".")
    minimal_mode = bool(getattr(args, "minimal", False))
    files_to_check = minimal_managed_files if minimal_mode else managed_files
    minimal_ref_paths = {
        os.path.normpath(p).replace("\\", "/") for p in minimal_managed_files
    }

    state = StatusState()
    _print_status_header(dest)

    for rel in files_to_check:
        _check_single_file(
            rel,
            dest,
            state,
            resolves_within,
            minimal_mode,
            minimal_ref_paths,
        )

    _run_contextlint(dest, state)
    print()

    if _has_issues(state):
        _print_top_offenders(state)
        print(f"Result: Action required ({', '.join(_issue_list(state))})")
        if args.check:
            sys.exit(1)
        return

    print("Result: Ready (All files present, filled, and within budgets)")
    if args.check:
        sys.exit(0)
