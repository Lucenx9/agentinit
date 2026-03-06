#!/usr/bin/env python3
"""agentinit CLI entrypoint and stable wrappers."""

from __future__ import annotations

import os
import sys
from argparse import Namespace

from agentinit._add import ADD_RESOURCE_TYPES, cmd_add as _cmd_add_impl
from agentinit._doctor import cmd_doctor as _cmd_doctor_impl
from agentinit._parser import build_parser as _build_parser_impl
from agentinit._project_detect import (
    _replace_commands_section as _replace_commands_section_impl,
)
from agentinit._scaffold import ConsolePalette, ScaffoldConfig, ScaffoldOps
from agentinit._status import cmd_status as _cmd_status_impl
from agentinit._sync import cmd_sync as _cmd_sync_impl

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template")
SKELETONS_DIR = os.path.join(TEMPLATE_DIR, "skeletons")
SKELETON_CHOICES = ("fastapi",)
SKELETON_IGNORED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    "build",
    "dist",
}
SKELETON_IGNORED_FILE_NAMES = {
    ".DS_Store",
    "CACHEDIR.TAG",
}
SKELETON_IGNORED_FILE_SUFFIXES = (
    ".egg-info",
    ".pyc",
    ".pyd",
    ".pyo",
)


# ---------------------------------------------------------------------------
# ANSI color helpers (zero dependencies)
# Respects NO_COLOR (https://no-color.org/), TERM=dumb, and non-TTY streams.
# ---------------------------------------------------------------------------


def _use_color(stream=None):
    """Return True when ANSI color codes should be emitted to *stream*."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    stream = stream or sys.stdout
    return hasattr(stream, "isatty") and stream.isatty()


_BOLD = "\033[1m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_RED = "\033[31m"
_RESET = "\033[0m"

_PALETTE = ConsolePalette(
    bold=_BOLD,
    green=_GREEN,
    yellow=_YELLOW,
    cyan=_CYAN,
    red=_RED,
)


def _c(text, code, stream=None):
    """Wrap *text* in an ANSI escape *code* if color is enabled for *stream*."""
    if _use_color(stream):
        return f"{code}{text}{_RESET}"
    return text


def _print_next_steps(dest="."):
    """Print actionable guidance after a successful init or new."""
    print(f"\n{_c('Next steps:', _CYAN + _BOLD)}")
    print(
        f"  {_c('1.', _CYAN)} Open {_c('docs/PROJECT.md', _BOLD)} and describe your project"
    )
    print(
        f"  {_c('2.', _CYAN)} Fill in {_c('docs/CONVENTIONS.md', _BOLD)} with your team's standards"
    )
    print(
        f"  {_c('3.', _CYAN)} Run your coding agent — it will read AGENTS.md automatically"
    )
    if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
        candidate_paths = ["AGENTS.md", "CLAUDE.md", "GEMINI.md", "docs/", ".agents/"]
        existing_paths = []
        for path in candidate_paths:
            full_path = os.path.join(dest, path.rstrip("/"))
            if os.path.exists(full_path):
                existing_paths.append(path)

        if existing_paths:
            paths_str = " ".join(existing_paths)
            print(f"\n  {_c('Tip:', _YELLOW)} Some agents only read tracked files.")
            print(f"       Consider: {_c(f'git add {paths_str}', _BOLD)}")


# Files managed by agentinit (relative to project root).
# Used by --force to decide what can be overwritten.
MANAGED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "llms.txt",
    ".gitignore",
    "docs/PROJECT.md",
    "docs/CONVENTIONS.md",
    "docs/TODO.md",
    "docs/DECISIONS.md",
    "docs/STATE.md",
    ".cursor/rules/project.mdc",
    ".github/copilot-instructions.md",
    ".claude/rules/coding-style.md",
    ".claude/rules/testing.md",
    ".claude/rules/repo-map.md",
    ".contextlintrc.json",
]

MINIMAL_MANAGED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "llms.txt",
    "docs/PROJECT.md",
    "docs/CONVENTIONS.md",
]

MINIMAL_TEMPLATE_OVERRIDES = {
    "AGENTS.md": os.path.join("minimal", "AGENTS.md"),
    "CLAUDE.md": os.path.join("minimal", "CLAUDE.md"),
    "llms.txt": os.path.join("minimal", "llms.txt"),
}


# Files that `remove` will delete or archive.
# .gitignore is intentionally excluded — it's a common file users may rely on.
REMOVABLE_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "llms.txt",
    "docs/PROJECT.md",
    "docs/CONVENTIONS.md",
    "docs/TODO.md",
    "docs/DECISIONS.md",
    "docs/STATE.md",
    ".cursor/rules/project.mdc",
    ".github/copilot-instructions.md",
    ".claude/rules/coding-style.md",
    ".claude/rules/testing.md",
    ".claude/rules/repo-map.md",
    ".contextlintrc.json",
]

# Directories to clean up if empty after removal (deepest first).
CLEANUP_DIRS = [
    "docs",
    os.path.join(".cursor", "rules"),
    ".cursor",
    os.path.join(".claude", "rules"),
    ".claude",
]


def _resolves_within(root: str, path: str) -> bool:
    """Return True when path resolves inside root after following symlinks."""
    try:
        root_real = os.path.realpath(root)
        path_real = os.path.realpath(path)
        return os.path.commonpath([root_real, path_real]) == root_real
    except ValueError:
        return False


def _scaffold_ops() -> ScaffoldOps:
    return ScaffoldOps(
        ScaffoldConfig(
            template_dir=TEMPLATE_DIR,
            skeletons_dir=SKELETONS_DIR,
            managed_files=MANAGED_FILES,
            minimal_managed_files=MINIMAL_MANAGED_FILES,
            minimal_template_overrides=MINIMAL_TEMPLATE_OVERRIDES,
            removable_files=REMOVABLE_FILES,
            cleanup_dirs=CLEANUP_DIRS,
            skeleton_ignored_dir_names=SKELETON_IGNORED_DIR_NAMES,
            skeleton_ignored_file_names=SKELETON_IGNORED_FILE_NAMES,
            skeleton_ignored_file_suffixes=SKELETON_IGNORED_FILE_SUFFIXES,
        ),
        colorize=_c,
        print_next_steps=_print_next_steps,
        resolves_within=_resolves_within,
        palette=_PALETTE,
    )


def copy_template(
    dest: str, force: bool = False, minimal: bool = False
) -> tuple[list[str], list[str]]:
    return _scaffold_ops().copy_template(dest, force=force, minimal=minimal)


def copy_skeleton(
    dest: str, skeleton: str, force: bool = False
) -> tuple[list[str], list[str]]:
    return _scaffold_ops().copy_skeleton(dest, skeleton, force=force)


def _render_llms_content(dest: str) -> str:
    return _scaffold_ops()._render_llms_content(dest)


def _replace_commands_section(content: str, new_body: str) -> str:
    return _replace_commands_section_impl(content, new_body)


def apply_updates(
    dest: str, args: Namespace, *, writable_files: set[str] | None = None
) -> None:
    _scaffold_ops().apply_updates(dest, args, writable_files=writable_files)


def refresh_llms_txt(dest: str) -> float | None:
    return _scaffold_ops().refresh_llms_txt(dest)


def write_todo(dest: str, force: bool = False) -> None:
    _scaffold_ops().write_todo(dest, force=force)


def write_decisions(dest: str, force: bool = False) -> None:
    _scaffold_ops().write_decisions(dest, force=force)


def cmd_new(args: Namespace) -> None:
    _scaffold_ops().cmd_new(args)


def cmd_init(args: Namespace) -> None:
    _scaffold_ops().cmd_init(args)


def cmd_remove(args: Namespace) -> None:
    _scaffold_ops().cmd_remove(args)


def cmd_status(args: Namespace) -> None:
    """Show the status of agentinit context files in the current directory."""
    _cmd_status_impl(
        args,
        managed_files=MANAGED_FILES,
        minimal_managed_files=MINIMAL_MANAGED_FILES,
        resolves_within=_resolves_within,
    )


def cmd_add(args: Namespace) -> None:
    """Add a modular agentic resource to the current project."""
    _cmd_add_impl(args, template_dir=TEMPLATE_DIR, resolves_within=_resolves_within)


def cmd_sync(args: Namespace) -> None:
    """Sync vendor router files from AGENTS.md-oriented templates."""
    _cmd_sync_impl(args, template_dir=TEMPLATE_DIR, resolves_within=_resolves_within)


def cmd_doctor(args: Namespace) -> None:
    """Run all checks and show actionable fix commands."""
    _cmd_doctor_impl(
        args,
        managed_files=MANAGED_FILES,
        minimal_managed_files=MINIMAL_MANAGED_FILES,
        template_dir=TEMPLATE_DIR,
        resolves_within=_resolves_within,
    )


def cmd_lint(args: Namespace) -> None:
    """Run contextlint on the current directory (or --root)."""
    from agentinit.contextlint_adapter import run_contextlint

    argv = []
    if args.root:
        argv.extend(["--root", args.root])
    if args.config:
        argv.extend(["--config", args.config])
    if args.format:
        argv.extend(["--format", args.format])
    if args.no_dup:
        argv.append("--no-dup")
    sys.exit(run_contextlint(argv))


def build_parser():
    """Build the CLI argument parser."""
    return _build_parser_impl(SKELETON_CHOICES, list(ADD_RESOURCE_TYPES))


def _maybe_enable_prompt(args: Namespace) -> None:
    """Enable interactive prompt mode for scaffold commands when appropriate."""
    if args.command not in ("new", "init", "minimal"):
        return
    has_prefills = bool(getattr(args, "purpose", None))
    if getattr(args, "yes", False):
        args.prompt = False
    elif not args.prompt and not has_prefills and sys.stdin.isatty():
        args.prompt = True


def _dispatch_command(args: Namespace, parser) -> None:
    """Dispatch parsed args to the selected command handler."""
    handlers = {
        "new": cmd_new,
        "init": cmd_init,
        "remove": cmd_remove,
        "status": cmd_status,
        "add": cmd_add,
        "lint": cmd_lint,
        "sync": cmd_sync,
        "doctor": cmd_doctor,
    }

    if args.command == "minimal":
        args.minimal = True
        cmd_init(args)
        return
    if args.command in ("refresh-llms", "refresh"):
        dest = args.root or os.getcwd()
        elapsed = refresh_llms_txt(dest)
        if elapsed is None:
            sys.exit(1)
        print(f"Regenerated llms.txt in {elapsed:.3f}s")
        return

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)
    handler(args)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    _maybe_enable_prompt(args)
    _dispatch_command(args, parser)


if __name__ == "__main__":
    main()
