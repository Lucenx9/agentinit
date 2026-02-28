#!/usr/bin/env python3
"""agentinit — scaffold agent context files into a project."""

import argparse
import importlib.metadata
import os
import re
import shutil
import sys
from datetime import date, datetime

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template")


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


def _c(text, code, stream=None):
    """Wrap *text* in an ANSI escape *code* if color is enabled for *stream*."""
    if _use_color(stream):
        return f"{code}{text}{_RESET}"
    return text


def _print_next_steps():
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


# Files managed by agentinit (relative to project root).
# Used by --force to decide what can be overwritten.
MANAGED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".gitignore",
    "docs/PROJECT.md",
    "docs/CONVENTIONS.md",
    "docs/TODO.md",
    "docs/DECISIONS.md",
    ".cursor/rules/project.mdc",
    ".github/copilot-instructions.md",
]

MINIMAL_MANAGED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "docs/PROJECT.md",
    "docs/CONVENTIONS.md",
]


# Files that `remove` will delete or archive.
# .gitignore is intentionally excluded — it's a common file users may rely on.
REMOVABLE_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "docs/PROJECT.md",
    "docs/CONVENTIONS.md",
    "docs/TODO.md",
    "docs/DECISIONS.md",
    ".cursor/rules/project.mdc",
    ".github/copilot-instructions.md",
]

# Directories to clean up if empty after removal (deepest first).
CLEANUP_DIRS = [
    "docs",
    os.path.join(".cursor", "rules"),
    ".cursor",
]


def _resolves_within(root, path):
    """Return True when path resolves inside root after following symlinks."""
    try:
        root_real = os.path.realpath(root)
        path_real = os.path.realpath(path)
        return os.path.commonpath([root_real, path_real]) == root_real
    except ValueError:
        # On Windows, different drives are never within the same root.
        return False


def copy_template(dest, force=False, minimal=False):
    """Copy template files into dest. Skip files that already exist unless force.

    .gitignore is never overwritten, even with --force, because users commonly
    customize it and clobbering would lose their changes.
    """
    copied = []
    skipped = []
    dest_real = os.path.realpath(dest)
    files_to_copy = MINIMAL_MANAGED_FILES if minimal else MANAGED_FILES
    for rel in files_to_copy:
        src = os.path.join(TEMPLATE_DIR, rel)
        dst = os.path.join(dest, rel)
        if not os.path.exists(src):
            continue
        if not _resolves_within(dest_real, os.path.dirname(dst)):
            print(
                _c(
                    f"Warning: destination parent resolves outside project, skipping: {rel}",
                    _YELLOW,
                    sys.stderr,
                ),
                file=sys.stderr,
            )
            skipped.append(rel)
            continue
        if os.path.lexists(dst):
            if os.path.islink(dst):
                print(
                    _c(
                        f"Warning: destination is a symlink, skipping: {rel}",
                        _YELLOW,
                        sys.stderr,
                    ),
                    file=sys.stderr,
                )
                skipped.append(rel)
                continue
            if os.path.isdir(dst):
                print(
                    _c(
                        f"Warning: destination is a directory, skipping: {rel}",
                        _YELLOW,
                        sys.stderr,
                    ),
                    file=sys.stderr,
                )
                skipped.append(rel)
                continue
            if rel == ".gitignore":
                skipped.append(rel)
                if force:
                    print(
                        _c("Note:", _YELLOW, sys.stderr)
                        + " .gitignore already exists, leaving it untouched.",
                        file=sys.stderr,
                    )
                continue
            if not force:
                skipped.append(rel)
                continue
        if not _resolves_within(dest_real, dst):
            print(
                _c(
                    f"Warning: destination resolves outside project, skipping: {rel}",
                    _YELLOW,
                    sys.stderr,
                ),
                file=sys.stderr,
            )
            skipped.append(rel)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(src, dst)
        except PermissionError:
            if force:
                os.chmod(dst, 0o644)
                shutil.copy2(src, dst)
            else:
                print(
                    _c("Warning:", _YELLOW, sys.stderr)
                    + f" permission denied, skipping: {rel}",
                    file=sys.stderr,
                )
                skipped.append(rel)
                continue
        copied.append(rel)
    return copied, skipped


def _run_detect(dest, project_path, content):
    """Detect stack and commands from manifests and return updated content."""
    import json

    stack_updates = {}
    cmd_updates = {}

    # 1. Node: package.json
    pkg_json_path = os.path.join(dest, "package.json")
    if os.path.isfile(pkg_json_path):
        try:
            with open(pkg_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            stack_updates["- **Runtime:** TBD"] = "- **Runtime:** Node.js"

            pm = str(data.get("packageManager") or "")
            manager = "npm"
            if "pnpm" in pm:
                manager = "pnpm"
            elif "yarn" in pm:
                manager = "yarn"
            elif "bun" in pm:
                manager = "bun"
            else:
                if os.path.isfile(os.path.join(dest, "pnpm-lock.yaml")):
                    manager = "pnpm"
                elif os.path.isfile(os.path.join(dest, "yarn.lock")):
                    manager = "yarn"
                elif os.path.isfile(os.path.join(dest, "bun.lockb")):
                    manager = "bun"
                else:
                    manager = "npm"

            scripts = data.get("scripts")
            if not isinstance(scripts, dict):
                scripts = {}
            run_prefix = (
                f"{manager} run " if manager not in ("yarn", "bun") else f"{manager} "
            )

            if "setup" in scripts:
                cmd_updates["- Setup: TBD"] = f"- Setup: {run_prefix}setup"
            else:
                cmd_updates["- Setup: TBD"] = f"- Setup: {manager} install"

            if "build" in scripts:
                cmd_updates["- Build: TBD"] = f"- Build: {run_prefix}build"
            if "test" in scripts:
                cmd_updates["- Test: TBD"] = f"- Test: {run_prefix}test"
            if "lint" in scripts:
                cmd_updates["- Lint/Format: TBD"] = f"- Lint/Format: {run_prefix}lint"
            elif "format" in scripts:
                cmd_updates["- Lint/Format: TBD"] = f"- Lint/Format: {run_prefix}format"
            if "dev" in scripts:
                cmd_updates["- Run: TBD"] = f"- Run: {run_prefix}dev"
            elif "start" in scripts:
                cmd_updates["- Run: TBD"] = f"- Run: {run_prefix}start"
        except Exception:
            pass

    # 2. Go: go.mod
    go_mod_path = os.path.join(dest, "go.mod")
    if os.path.isfile(go_mod_path):
        try:
            with open(go_mod_path, "r", encoding="utf-8") as f:
                go_version = None
                for line in f:
                    line = line.strip()
                    if line.startswith("go "):
                        go_version = line.split(" ")[1]
                        break

            stack_updates["- **Language(s):** TBD"] = "- **Language(s):** Go"
            if go_version:
                stack_updates["- **Runtime:** TBD"] = f"- **Runtime:** Go {go_version}"

            cmd_updates["- Setup: TBD"] = "- Setup: go mod download"
            cmd_updates["- Build: TBD"] = "- Build: go build ./..."
            cmd_updates["- Test: TBD"] = "- Test: go test ./..."
            cmd_updates["- Run: TBD"] = "- Run: go run ."
        except Exception:
            pass

    # TOML parsers (Python, Rust)
    try:
        import tomllib
    except ImportError:
        tomllib = None

    if tomllib:
        # 3. Rust: Cargo.toml
        cargo_path = os.path.join(dest, "Cargo.toml")
        if os.path.isfile(cargo_path):
            try:
                with open(cargo_path, "rb") as f:
                    cargo_data = tomllib.load(f)

                pkg = cargo_data.get("package")
                if not isinstance(pkg, dict):
                    pkg = {}
                name = pkg.get("name", "")
                edition = pkg.get("edition", "")

                lang_str = "- **Language(s):** Rust"
                if edition:
                    lang_str += f" ({edition})"
                stack_updates["- **Language(s):** TBD"] = lang_str

                cmd_updates["- Setup: TBD"] = "- Setup: cargo fetch"
                cmd_updates["- Build: TBD"] = "- Build: cargo build"
                cmd_updates["- Test: TBD"] = "- Test: cargo test"
                cmd_updates["- Lint/Format: TBD"] = (
                    "- Lint/Format: cargo fmt && cargo clippy"
                )
                cmd_updates["- Run: TBD"] = "- Run: cargo run"
            except Exception:
                pass

        # 4. Python: pyproject.toml
        pyproject_path = os.path.join(dest, "pyproject.toml")
        if os.path.isfile(pyproject_path):
            try:
                with open(pyproject_path, "rb") as f:
                    py_data = tomllib.load(f)

                manager = "pip"
                tool = py_data.get("tool")
                if isinstance(tool, dict):
                    if "poetry" in tool:
                        manager = "poetry"
                    elif "uv" in tool:
                        manager = "uv"
                    elif "pdm" in tool:
                        manager = "pdm"

                project = py_data.get("project")
                if not isinstance(project, dict):
                    project = {}
                requires_python = project.get("requires-python", "")

                stack_updates["- **Language(s):** TBD"] = "- **Language(s):** Python"
                if requires_python:
                    stack_updates["- **Runtime:** TBD"] = (
                        f"- **Runtime:** Python {requires_python}"
                    )

                if manager == "poetry":
                    cmd_updates["- Setup: TBD"] = "- Setup: poetry install"
                    cmd_updates["- Run: TBD"] = "- Run: poetry run python"
                elif manager == "uv":
                    cmd_updates["- Setup: TBD"] = "- Setup: uv sync"
                    cmd_updates["- Run: TBD"] = "- Run: uv run python"
                elif manager == "pdm":
                    cmd_updates["- Setup: TBD"] = "- Setup: pdm install"
                    cmd_updates["- Run: TBD"] = "- Run: pdm run python"
                else:
                    cmd_updates["- Setup: TBD"] = "- Setup: pip install -e ."
            except Exception:
                pass

    for k, v in stack_updates.items():
        content = content.replace(k, v)
    for k, v in cmd_updates.items():
        content = content.replace(k, v)

    return content


def apply_updates(dest, args):
    """Apply purpose and wizard data to project files."""
    wizard_run = args.prompt
    if wizard_run:
        if not sys.stdin.isatty():
            print(
                _c("Error:", _RED, sys.stderr)
                + " --prompt requires an interactive terminal. Use --purpose for non-interactive prefill, or run without --prompt.",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            purpose = args.purpose
            while not purpose:
                purpose = input("Purpose: ").strip()
            env = input("Environment (OS/device) [optional]: ").strip()
            constraints = input("Constraints [optional]: ").strip()
            commands = input(
                "Commands I can run (comma-separated) [optional]: "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(130)
    else:
        purpose = args.purpose or "TBD"
        env = ""
        constraints = ""
        commands = ""

    project_path = os.path.join(dest, "docs", "PROJECT.md")
    if not os.path.isfile(project_path):
        print(
            _c("Warning:", _YELLOW, sys.stderr)
            + " docs/PROJECT.md is not a regular file; skipping purpose update.",
            file=sys.stderr,
        )
    else:
        with open(project_path, "r", encoding="utf-8") as f:
            content = f.read()

        if purpose:
            content = content.replace(
                "TBD (Describe what this project is for and expected outcomes)",
                purpose,
            ).replace(
                "Describe what this project is for, who it serves, and the expected outcomes.",
                purpose,
            )

        if wizard_run:
            if env:
                content = content.replace(
                    "## Stack (TBD)",
                    f"## Environment\n\n- OS/device: {env}\n\n## Stack (TBD)",
                )
            if commands:
                cmds_list = "\n".join(
                    f"- {c.strip()}" for c in commands.split(",") if c.strip()
                )
                old_commands = (
                    "## Commands (TBD)\n\n"
                    "- Setup: TBD\n"
                    "- Build: TBD\n"
                    "- Test: TBD\n"
                    "- Lint/Format: TBD\n"
                    "- Run: TBD"
                )
                content = content.replace(old_commands, f"## Commands\n\n{cmds_list}")
            if constraints:
                old_constraints = (
                    "- Document non-negotiable constraints here.\n"
                    "- List security/compliance/performance boundaries.\n"
                    "- Note delivery deadlines or operational limits."
                )
                content = content.replace(old_constraints, f"- {constraints}")

        if getattr(args, "detect", False):
            content = _run_detect(dest, project_path, content)

        with open(project_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    if wizard_run:
        conv_path = os.path.join(dest, "docs", "CONVENTIONS.md")
        if os.path.isfile(conv_path):
            safe_defaults = (
                "## Safe Defaults\n\n"
                "- Prefer small, reversible changes\n"
                "- Ask before destructive actions\n"
                "- Provide copy-paste commands\n"
                "- State assumptions\n\n"
            )
            with open(conv_path, "r", encoding="utf-8") as f:
                conv_content = f.read()
            if "# Conventions Template\n" in conv_content:
                conv_content = conv_content.replace(
                    "# Conventions Template\n",
                    f"# Conventions Template\n\n{safe_defaults}",
                    1,
                )
            else:
                conv_content = safe_defaults + conv_content
            with open(conv_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(conv_content)


def write_todo(dest, force=False):
    """Write a bootstrap TODO.md for a new project.

    Skips if the file already exists unless force is True.
    """
    path = os.path.join(dest, "docs", "TODO.md")
    if os.path.exists(path) and not force:
        print(
            _c("Warning:", _YELLOW, sys.stderr)
            + f" {path} already exists, skipping (use --force to overwrite).",
            file=sys.stderr,
        )
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    content = """\
# TODO

## In Progress
- Fill `docs/PROJECT.md` with real stack and command details.

## Next
- Fill `docs/CONVENTIONS.md` with concrete team standards.
- Review generated agent router files and customize as needed.

## Blocked
- (none)

## Done
- Scaffolded project with agentinit.
"""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def write_decisions(dest, force=False):
    """Write DECISIONS.md with the first ADR-lite entry.

    Skips if the file already exists unless force is True.
    """
    path = os.path.join(dest, "docs", "DECISIONS.md")
    if os.path.exists(path) and not force:
        print(
            _c("Warning:", _YELLOW, sys.stderr)
            + f" {path} already exists, skipping (use --force to overwrite).",
            file=sys.stderr,
        )
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    today = date.today().isoformat()
    content = f"""\
# Decisions

Use one ADR-lite entry per durable decision.

## Entry Format
- Date: YYYY-MM-DD
- Decision: Short statement
- Rationale: Why this choice was made
- Alternatives: Options considered and why they were not selected

## Entries
### {today}
- Date: {today}
- Decision: Adopt agentinit routing layout for agent context.
- Rationale: Provides a single source of truth (AGENTS.md + docs/*) that all coding agents can share.
- Alternatives: Per-agent full instructions; rejected due to drift risk and maintenance overhead.
"""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def cmd_new(args):
    # --yes disables the interactive wizard even when called directly.
    if getattr(args, "yes", False):
        args.prompt = False

    # Reject names whose final component is '.' or '..' to prevent traversal.
    basename = os.path.basename(os.path.normpath(args.name))
    if not basename or basename in (".", ".."):
        print(
            _c("Error:", _RED, sys.stderr) + f" invalid project name: {args.name!r}",
            file=sys.stderr,
        )
        print("The project name must not resolve to '.' or '..'.", file=sys.stderr)
        sys.exit(1)

    if args.dir:
        dest = os.path.join(args.dir, args.name)
    else:
        dest = os.path.join(".", args.name)

    dest = os.path.abspath(dest)

    if os.path.exists(dest) and not args.force:
        print(
            _c("Error:", _RED, sys.stderr) + f" directory already exists: {dest}",
            file=sys.stderr,
        )
        print("Use --force to overwrite agentinit files.", file=sys.stderr)
        sys.exit(1)

    # Validate template before creating anything.
    if not os.path.isdir(TEMPLATE_DIR):
        print(
            _c("Error:", _RED, sys.stderr)
            + " template directory not found. Installation may be corrupt.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Create dir and copy template
    os.makedirs(dest, exist_ok=True)
    copied, skipped = copy_template(dest, force=args.force, minimal=args.minimal)
    if not copied and not skipped:
        print(
            _c("Error:", _RED, sys.stderr)
            + " no template files copied. Installation may be corrupt.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Customize generated files
    apply_updates(dest, args)
    if not args.minimal:
        write_todo(dest, force=args.force)
        write_decisions(dest, force=args.force)

    print(_c("Created project", _GREEN + _BOLD) + f" at {dest}")
    if copied:
        print(f"  Copied: {len(copied)} files")
    if skipped:
        print(f"  Skipped (already exist): {', '.join(skipped)}")
    _print_next_steps()


def cmd_init(args):
    # --yes disables the interactive wizard even when called directly.
    if getattr(args, "yes", False):
        args.prompt = False

    dest = os.path.abspath(".")

    if not os.path.isdir(TEMPLATE_DIR):
        print(
            _c("Error:", _RED, sys.stderr)
            + " template directory not found. Installation may be corrupt.",
            file=sys.stderr,
        )
        sys.exit(1)

    copied, skipped = copy_template(dest, force=args.force, minimal=args.minimal)

    if not copied and not skipped:
        print(
            _c("Error:", _RED, sys.stderr)
            + " no template files copied. Installation may be corrupt.",
            file=sys.stderr,
        )
        sys.exit(1)

    apply_updates(dest, args)

    if copied:
        print(f"{_c('Copied', _GREEN)} {len(copied)} files:")
        for f in copied:
            print(f"  {_c('+', _GREEN)} {f}")
    if skipped:
        print(f"{_c('Skipped', _YELLOW)} {len(skipped)} files (already exist):")
        for f in skipped:
            print(f"  {_c('~', _YELLOW)} {f}")
    if not copied:
        print("All agentinit files already present. Nothing to copy.")
    else:
        _print_next_steps()


def cmd_remove(args):
    dest = os.path.abspath(".")
    dry_run = args.dry_run
    archive = args.archive

    # Find which managed files exist.
    found = []
    missing = []
    for rel in REMOVABLE_FILES:
        path = os.path.join(dest, rel)
        if os.path.lexists(path):
            is_dir = os.path.isdir(path) and not os.path.islink(path)
            found.append((rel, is_dir))
        else:
            missing.append(rel)

    if not found:
        print("No agentinit-managed files found. Nothing to do.")
        if missing:
            print(f"  Already absent: {len(missing)} files")
        return

    # Describe what will happen.
    action = "archive" if archive else "remove"
    for rel, is_dir in found:
        if is_dir:
            print(f"  {_c('!', _YELLOW)} {rel} (directory; will skip)")
            continue
        if archive:
            print(f"  {_c('→', _CYAN)} {rel}")
        else:
            print(f"  {_c('×', _RED)} {rel}")
    if missing:
        for rel in missing:
            print(f"  - {rel} (already absent)")

    if dry_run:
        actionable = sum(1 for _, is_dir in found if not is_dir)
        print(f"\nDry run: would {action} {actionable} file(s).")
        return

    # Confirm unless --force.
    if not args.force:
        actionable = sum(1 for _, is_dir in found if not is_dir)
        if not sys.stdin.isatty():
            print(
                _c("Error:", _RED, sys.stderr)
                + " confirmation requires a terminal. Use --force to skip.",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            answer = (
                input(f"\n{action.capitalize()} {actionable} file(s)? (y/N) ")
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return
        if answer != "y":
            print("Aborted.")
            return

    # Perform removal or archival.
    if archive:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        archive_dir = os.path.join(dest, ".agentinit-archive", ts)
        archived = 0
        for rel, is_dir in found:
            if is_dir:
                print(
                    _c("Warning:", _YELLOW, sys.stderr)
                    + f" managed path is a directory, skipping archive: {rel}",
                    file=sys.stderr,
                )
                continue
            src = os.path.join(dest, rel)
            dst = os.path.join(archive_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                shutil.move(src, dst)
                archived += 1
            except OSError as e:
                print(
                    _c("Error:", _RED, sys.stderr) + f" failed to archive {rel}: {e}",
                    file=sys.stderr,
                )
                continue
        print(f"Archived {archived} file(s) to .agentinit-archive/{ts}/")
    else:
        removed = 0
        for rel, is_dir in found:
            if is_dir:
                print(
                    _c("Warning:", _YELLOW, sys.stderr)
                    + f" managed path is a directory, skipping remove: {rel}",
                    file=sys.stderr,
                )
                continue
            try:
                os.remove(os.path.join(dest, rel))
                removed += 1
            except OSError as e:
                print(
                    _c("Error:", _RED, sys.stderr) + f" failed to remove {rel}: {e}",
                    file=sys.stderr,
                )
                continue
        print(f"Removed {removed} file(s).")

    # Cleanup empty directories.
    for d in CLEANUP_DIRS:
        dirpath = os.path.join(dest, d)
        if os.path.isdir(dirpath) and not os.listdir(dirpath):
            os.rmdir(dirpath)
            print(f"  Cleaned up empty directory: {d}/")


def cmd_status(args):
    """Show the status of agentinit context files in the current directory."""
    dest = os.path.abspath(".")

    missing = []
    tbd = []
    hard_violations = []
    broken_refs = []
    file_sizes = []
    files_to_check = (
        MINIMAL_MANAGED_FILES if getattr(args, "minimal", False) else MANAGED_FILES
    )

    print(f"{_c('Agent Context Status', _BOLD)}")
    print(f"Directory: {dest}\n")

    for rel in files_to_check:
        path = os.path.join(dest, rel)
        if os.path.islink(path) and not os.path.exists(path):
            missing.append(rel)
            print(f"  {_c('x', _RED)} {rel} {_c('(broken symlink)', _RED)}")
        elif not os.path.exists(path):
            missing.append(rel)
            print(f"  {_c('x', _RED)} {rel} {_c('(missing)', _RED)}")
        elif not os.path.isfile(path):
            missing.append(rel)
            print(f"  {_c('x', _RED)} {rel} {_c('(not a file)', _RED)}")
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                lines = content.splitlines()
                line_count = len(lines)
                file_sizes.append((rel, line_count))
                is_always_loaded = not rel.startswith("docs/") and rel != ".gitignore"

                status_symbol = _c("+", _GREEN)
                msgs = []
                hints = []

                if "TBD" in content:
                    tbd.append(rel)
                    status_symbol = _c("!", _YELLOW)
                    msgs.append(_c("(contains TBD, needs update)", _YELLOW))

                if line_count >= 300 and is_always_loaded:
                    hard_violations.append(rel)
                    status_symbol = _c("x", _RED)
                    msgs.append(_c(f"({line_count} lines >= 300)", _RED))
                    if "CLAUDE.md" in rel or "GEMINI.md" in rel:
                        hints.append(
                            f"Move details to docs/ and keep {os.path.basename(rel)} as a router (10–20 lines)."
                        )
                    elif "AGENTS.md" in rel:
                        hints.append("Split AGENTS.md into topic docs and link them.")
                    else:
                        hints.append(f"Reduce size of {rel} to keep context lean.")
                elif line_count >= 200:
                    status_symbol = (
                        _c("!", _YELLOW)
                        if status_symbol != _c("x", _RED)
                        else status_symbol
                    )
                    msgs.append(_c(f"({line_count} lines >= 200)", _YELLOW))
                    if is_always_loaded:
                        hints.append(
                            f"Consider moving details from {os.path.basename(rel)} to docs/."
                        )
                    else:
                        hints.append(
                            "Consider splitting this document if it grows further."
                        )

                msg_str = " ".join(msgs)
                print(f"  {status_symbol} {rel} {msg_str}".rstrip())
                for hint in hints:
                    print(f"      {_c('Hint:', _CYAN)} {hint}")

                if rel == "AGENTS.md":
                    # Check broken references
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

                    seen_broken = set()
                    dest_real = os.path.realpath(dest)
                    for p in potential_paths:
                        p = p.split("#", 1)[0]
                        p = p.split("?", 1)[0]
                        p = p.strip()
                        if " " in p:
                            p = p.split()[0]

                        if not p:
                            continue
                        if p.startswith(("http://", "https://", "mailto:", "/")):
                            continue
                        if not (
                            "/" in p
                            or "\\" in p
                            or p.endswith(
                                (".md", ".mdc", ".txt", ".py", ".yml", ".yaml")
                            )
                        ):
                            continue

                        target_path = os.path.join(dest_real, p)
                        if not _resolves_within(dest_real, target_path):
                            continue

                        target_real = os.path.realpath(target_path)
                        if not os.path.exists(target_real):
                            if p not in seen_broken:
                                seen_broken.add(p)
                                broken_refs.append(p)
                                print(f"      {_c('x', _RED)} Broken reference: {p}")
                                print(
                                    f"      {_c('Hint:', _CYAN)} Fix broken link: create {p} or remove the reference."
                                )

            except (OSError, UnicodeDecodeError):
                missing.append(rel)
                print(f"  {_c('x', _RED)} {rel} {_c('(unreadable)', _RED)}")

    print()
    if missing or tbd or hard_violations or broken_refs:
        issues = []
        if missing:
            issues.append(f"{len(missing)} missing")
        if tbd:
            issues.append(f"{len(tbd)} incomplete")
        if hard_violations:
            issues.append(f"{len(hard_violations)} too large")
        if broken_refs:
            issues.append(f"{len(broken_refs)} broken refs")

        print(f"{_c('Top offenders:', _YELLOW)}")
        if file_sizes:
            filtered = [(f, n) for f, n in file_sizes if f != ".gitignore"]
            filtered.sort(key=lambda x: x[1], reverse=True)
            for f_rel, f_lines in filtered[:3]:
                print(f"  {f_rel} ({f_lines} lines)")
        if broken_refs:
            print(f"  AGENTS.md: {len(broken_refs)} broken references")
        print()

        print(f"Result: {_c('Action required', _YELLOW)} ({', '.join(issues)})")
        if args.check:
            sys.exit(1)
    else:
        print(
            f"Result: {_c('Ready', _GREEN)} (All files present, filled, and within budgets)"
        )
        if args.check:
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        prog="agentinit",
        description="Scaffold agent context files into a project.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=importlib.metadata.version("agentinit"),
    )
    sub = parser.add_subparsers(dest="command")

    # agentinit new <name>
    p_new = sub.add_parser("new", help="Create a new project with agent context files.")
    p_new.add_argument("name", help="Project directory name.")
    p_new.add_argument(
        "--yes", "-y", action="store_true", help="Skip interactive wizard."
    )
    p_new.add_argument("--dir", help="Parent directory (default: current directory).")
    p_new.add_argument(
        "--force",
        action="store_true",
        help="Overwrite agentinit files (including TODO/DECISIONS) if they exist.",
    )
    p_new.add_argument(
        "--minimal",
        action="store_true",
        help="Create only AGENTS.md, CLAUDE.md, docs/PROJECT.md, and docs/CONVENTIONS.md.",
    )
    p_new.add_argument("--purpose", help="Non-interactive prefill for Purpose.")
    p_new.add_argument(
        "--prompt", action="store_true", help="Run interactive wizard (default on TTY)."
    )
    p_new.add_argument(
        "--detect",
        action="store_true",
        help="Auto-detect stack and commands from manifest files.",
    )

    # agentinit init
    p_init = sub.add_parser(
        "init", help="Add missing agent context files to the current directory."
    )
    p_init.add_argument(
        "--yes", "-y", action="store_true", help="Skip interactive wizard."
    )
    p_init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing agentinit files (including TODO/DECISIONS).",
    )
    p_init.add_argument(
        "--minimal",
        action="store_true",
        help="Create only AGENTS.md, CLAUDE.md, docs/PROJECT.md, and docs/CONVENTIONS.md.",
    )
    p_init.add_argument("--purpose", help="Non-interactive prefill for Purpose.")
    p_init.add_argument(
        "--prompt", action="store_true", help="Run interactive wizard (default on TTY)."
    )
    p_init.add_argument(
        "--detect",
        action="store_true",
        help="Auto-detect stack and commands from manifest files.",
    )

    # agentinit minimal  (shortcut for init --minimal)
    p_minimal = sub.add_parser("minimal", help="Shortcut for 'init --minimal'.")
    p_minimal.add_argument(
        "--yes", "-y", action="store_true", help="Skip interactive wizard."
    )
    p_minimal.add_argument(
        "--force", action="store_true", help="Overwrite existing agentinit files."
    )
    p_minimal.add_argument("--purpose", help="Non-interactive prefill for Purpose.")
    p_minimal.add_argument(
        "--prompt", action="store_true", help="Run interactive wizard (default on TTY)."
    )
    p_minimal.add_argument(
        "--detect",
        action="store_true",
        help="Auto-detect stack and commands from manifest files.",
    )

    # agentinit remove
    p_remove = sub.add_parser(
        "remove", help="Remove agentinit-managed files from the current directory."
    )
    p_remove.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only, do not change anything.",
    )
    p_remove.add_argument(
        "--archive",
        action="store_true",
        help="Move files to .agentinit-archive/ instead of deleting.",
    )
    p_remove.add_argument(
        "--force", action="store_true", help="Skip confirmation prompt."
    )

    # agentinit status
    p_status = sub.add_parser(
        "status",
        help="Show which agent context files are present, missing, or need updates.",
    )
    p_status.add_argument(
        "--check",
        action="store_true",
        help="Exit with code 1 if files are missing or incomplete. Useful for CI.",
    )
    p_status.add_argument(
        "--minimal", action="store_true", help="Check only the minimal core files."
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # Auto-enable interactive wizard on TTY unless --yes was passed.
    if args.command in ("new", "init", "minimal"):
        if getattr(args, "yes", False):
            args.prompt = False
        elif not args.prompt and sys.stdin.isatty():
            args.prompt = True

    if args.command == "new":
        cmd_new(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "minimal":
        args.minimal = True
        cmd_init(args)
    elif args.command == "remove":
        cmd_remove(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
