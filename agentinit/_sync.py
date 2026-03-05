"""Router file synchronization for `agentinit sync`."""

from __future__ import annotations

import os
import sys
from typing import Callable

SYNC_ROUTER_FILES = (
    "CLAUDE.md",
    "GEMINI.md",
    os.path.join(".cursor", "rules", "project.mdc"),
    os.path.join(".github", "copilot-instructions.md"),
)


def _fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def _validate_sync_root(dest: str) -> None:
    """Ensure destination project has AGENTS.md."""
    if not os.path.isfile(os.path.join(dest, "AGENTS.md")):
        _fail("AGENTS.md not found. Run 'agentinit init' first.")


def _read_text(path: str, label: str) -> tuple[str | None, str | None]:
    """Return (text, error_message) for *path*."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), None
    except OSError as exc:
        return None, f"cannot read {label}: {exc}"


def _write_text(path: str, content: str) -> str | None:
    """Write *content* to *path*; return error message on failure."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    except OSError as exc:
        return f"cannot write destination: {exc}"
    return None


def _validate_destination(
    dst: str, dest_real: str, resolves_within: Callable[[str, str], bool]
) -> str | None:
    """Validate destination path and return an error message when invalid."""
    if not resolves_within(dest_real, os.path.dirname(dst)) or not resolves_within(
        dest_real, dst
    ):
        return "destination escapes project root"
    if os.path.lexists(dst) and os.path.islink(dst):
        return "destination is a symlink"
    if os.path.exists(dst) and not os.path.isfile(dst):
        return "destination is not a regular file"
    return None


def _sync_single_router(
    rel: str,
    *,
    dest: str,
    dest_real: str,
    template_dir: str,
    check_mode: bool,
    resolves_within: Callable[[str, str], bool],
) -> tuple[str, str]:
    """Sync one router file and return (status, detail)."""
    template_path = os.path.join(template_dir, rel)
    if not os.path.isfile(template_path):
        return "error", "missing template in installation"

    dst = os.path.join(dest, rel)
    dst_error = _validate_destination(dst, dest_real, resolves_within)
    if dst_error:
        return "error", dst_error

    expected, read_error = _read_text(template_path, "template")
    if read_error:
        return "error", read_error
    assert expected is not None

    current = None
    if os.path.isfile(dst):
        current, read_error = _read_text(dst, "destination")
        if read_error:
            return "error", read_error

    if current == expected:
        return "unchanged", "in sync"

    reason = "missing" if current is None else "outdated"
    if check_mode:
        return "drift", reason

    write_error = _write_text(dst, expected)
    if write_error:
        return "error", write_error

    action = "created" if reason == "missing" else "updated"
    return "updated", action


def _print_check_result(
    dest: str,
    drift: list[tuple[str, str]],
    unchanged: list[str],
    errors: list[tuple[str, str]],
) -> None:
    print("Sync check")
    print(f"Directory: {dest}\n")
    for rel, reason in drift:
        print(f"  x {rel} ({reason})")
    for rel in unchanged:
        print(f"  + {rel} (in sync)")
    for rel, msg in errors:
        print(f"  x {rel} ({msg})")


def _print_sync_result(
    updated: list[tuple[str, str]],
    unchanged: list[str],
    errors: list[tuple[str, str]],
) -> None:
    for rel, action in updated:
        print(f"  + {rel} ({action})")
    for rel in unchanged:
        print(f"  = {rel} (unchanged)")
    for rel, msg in errors:
        print(f"  x {rel} ({msg})")


def cmd_sync(
    args, *, template_dir: str, resolves_within: Callable[[str, str], bool]
) -> None:
    """Sync vendor router files from template defaults."""
    dest = os.path.abspath(args.root or os.getcwd())
    dest_real = os.path.realpath(dest)
    check_mode = bool(getattr(args, "check", False))
    _validate_sync_root(dest)

    drift: list[tuple[str, str]] = []
    updated: list[tuple[str, str]] = []
    unchanged: list[str] = []
    errors: list[tuple[str, str]] = []

    for rel in SYNC_ROUTER_FILES:
        status, detail = _sync_single_router(
            rel,
            dest=dest,
            dest_real=dest_real,
            template_dir=template_dir,
            check_mode=check_mode,
            resolves_within=resolves_within,
        )
        if status == "drift":
            drift.append((rel, detail))
        elif status == "updated":
            updated.append((rel, detail))
        elif status == "unchanged":
            unchanged.append(rel)
        else:
            errors.append((rel, detail))

    if check_mode:
        _print_check_result(dest, drift, unchanged, errors)
        if drift or errors:
            print("\nResult: Out of sync")
            sys.exit(1)
        print("\nResult: In sync")
        sys.exit(0)

    _print_sync_result(updated, unchanged, errors)
    if errors:
        print("\nResult: Sync failed")
        sys.exit(1)
    print(
        f"\nResult: Sync complete ({len(updated)} changed, {len(unchanged)} unchanged)"
    )
