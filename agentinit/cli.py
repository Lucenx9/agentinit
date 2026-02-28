#!/usr/bin/env python3
"""agentinit — scaffold agent context files into a project."""

import argparse
import os
import shutil
import sys
from datetime import date, datetime

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template")

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


def copy_template(dest, force=False):
    """Copy template files into dest. Skip files that already exist unless force.

    .gitignore is never overwritten, even with --force, because users commonly
    customize it and clobbering would lose their changes.
    """
    copied = []
    skipped = []
    dest_real = os.path.realpath(dest)
    for rel in MANAGED_FILES:
        src = os.path.join(TEMPLATE_DIR, rel)
        dst = os.path.join(dest, rel)
        if not os.path.exists(src):
            continue
        if not _resolves_within(dest_real, os.path.dirname(dst)):
            print(f"Warning: destination parent resolves outside project, skipping: {rel}", file=sys.stderr)
            skipped.append(rel)
            continue
        if os.path.lexists(dst):
            if os.path.islink(dst):
                print(f"Warning: destination is a symlink, skipping: {rel}", file=sys.stderr)
                skipped.append(rel)
                continue
            if os.path.isdir(dst):
                print(f"Warning: destination is a directory, skipping: {rel}", file=sys.stderr)
                skipped.append(rel)
                continue
            if rel == ".gitignore":
                skipped.append(rel)
                if force:
                    print(f"  Note: .gitignore already exists, leaving it untouched.")
                continue
            if not force:
                skipped.append(rel)
                continue
        if not _resolves_within(dest_real, dst):
            print(f"Warning: destination resolves outside project, skipping: {rel}", file=sys.stderr)
            skipped.append(rel)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    return copied, skipped


def write_purpose(dest, purpose):
    """Replace the Purpose section placeholder in docs/PROJECT.md."""
    path = os.path.join(dest, "docs", "PROJECT.md")
    if not os.path.isfile(path):
        print("Warning: docs/PROJECT.md is not a regular file; skipping purpose update.", file=sys.stderr)
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace(
        "Describe what this project is for, who it serves, and the expected outcomes.",
        purpose,
    )
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def write_todo(dest, force=False):
    """Write a bootstrap TODO.md for a new project.

    Skips if the file already exists unless force is True.
    """
    path = os.path.join(dest, "docs", "TODO.md")
    if os.path.exists(path) and not force:
        print(f"Warning: {os.path.relpath(path)} already exists, skipping (use --force to overwrite).", file=sys.stderr)
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
        print(f"Warning: {os.path.relpath(path)} already exists, skipping (use --force to overwrite).", file=sys.stderr)
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


def _validate_slug(name):
    """Reject names that could escape the parent directory."""
    if not name or name in (".", "..") or "/" in name or "\\" in name or os.path.isabs(name):
        print(f"Error: invalid project name: {name!r}", file=sys.stderr)
        print("Name must be a simple directory slug (no slashes, '..', or absolute paths).", file=sys.stderr)
        sys.exit(1)


def cmd_new(args):
    _validate_slug(args.name)

    if args.dir:
        dest = os.path.join(args.dir, args.name)
    else:
        dest = os.path.join(".", args.name)

    dest = os.path.abspath(dest)

    if os.path.exists(dest) and not args.force:
        print(f"Error: directory already exists: {dest}", file=sys.stderr)
        print("Use --force to overwrite agentinit files.", file=sys.stderr)
        sys.exit(1)

    # Ask for purpose
    if args.yes:
        purpose = "TBD"
    else:
        purpose = input("Project purpose (one line): ").strip()
        if not purpose:
            purpose = "TBD"

    # Validate template before creating anything.
    if not os.path.isdir(TEMPLATE_DIR):
        print("Error: template directory not found. Installation may be corrupt.", file=sys.stderr)
        sys.exit(1)

    # Create dir and copy template
    os.makedirs(dest, exist_ok=True)
    copied, skipped = copy_template(dest, force=args.force)
    if not copied and not skipped:
        print("Error: no template files copied. Installation may be corrupt.", file=sys.stderr)
        sys.exit(1)

    # Customize generated files
    write_purpose(dest, purpose)
    write_todo(dest, force=args.force)
    write_decisions(dest, force=args.force)

    print(f"Created project at {dest}")
    if copied:
        print(f"  Copied: {len(copied)} files")
    if skipped:
        print(f"  Skipped (already exist): {', '.join(skipped)}")


def cmd_init(args):
    dest = os.path.abspath(".")

    copied, skipped = copy_template(dest, force=args.force)

    if not copied and not skipped:
        print("Nothing to do — template directory not found.")
        sys.exit(1)

    if copied:
        print(f"Copied {len(copied)} files:")
        for f in copied:
            print(f"  + {f}")
    if skipped:
        print(f"Skipped {len(skipped)} files (already exist):")
        for f in skipped:
            print(f"  ~ {f}")
    if not copied:
        print("All agentinit files already present. Nothing to copy.")


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
            print(f"  ! {rel} (directory; will skip)")
            continue
        print(f"  {'→' if archive else '×'} {rel}")
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
        answer = input(f"\n{action.capitalize()} {actionable} file(s)? (y/N) ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    # Perform removal or archival.
    if archive:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_dir = os.path.join(dest, ".agentinit-archive", ts)
        archived = 0
        for rel, is_dir in found:
            if is_dir:
                print(f"Warning: managed path is a directory, skipping archive: {rel}", file=sys.stderr)
                continue
            src = os.path.join(dest, rel)
            dst = os.path.join(archive_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                shutil.move(src, dst)
                archived += 1
            except OSError as e:
                print(f"Error: failed to archive {rel}: {e}", file=sys.stderr)
                continue
        print(f"Archived {archived} file(s) to .agentinit-archive/{ts}/")
    else:
        removed = 0
        for rel, is_dir in found:
            if is_dir:
                print(f"Warning: managed path is a directory, skipping remove: {rel}", file=sys.stderr)
                continue
            try:
                os.remove(os.path.join(dest, rel))
                removed += 1
            except OSError as e:
                print(f"Error: failed to remove {rel}: {e}", file=sys.stderr)
                continue
        print(f"Removed {removed} file(s).")

    # Cleanup empty directories.
    for d in CLEANUP_DIRS:
        dirpath = os.path.join(dest, d)
        if os.path.isdir(dirpath) and not os.listdir(dirpath):
            os.rmdir(dirpath)
            print(f"  Cleaned up empty directory: {d}/")


def main():
    parser = argparse.ArgumentParser(
        prog="agentinit",
        description="Scaffold agent context files into a project.",
    )
    sub = parser.add_subparsers(dest="command")

    # agentinit new <name>
    p_new = sub.add_parser("new", help="Create a new project with agent context files.")
    p_new.add_argument("name", help="Project directory name.")
    p_new.add_argument("--yes", "-y", action="store_true", help="Skip prompts (set purpose to TBD).")
    p_new.add_argument("--dir", help="Parent directory (default: current directory).")
    p_new.add_argument("--force", action="store_true", help="Overwrite agentinit files (including TODO/DECISIONS) if they exist.")

    # agentinit init
    p_init = sub.add_parser("init", help="Add missing agent context files to the current directory.")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing agentinit files (including TODO/DECISIONS).")

    # agentinit remove
    p_remove = sub.add_parser("remove", help="Remove agentinit-managed files from the current directory.")
    p_remove.add_argument("--dry-run", action="store_true", help="Print actions only, do not change anything.")
    p_remove.add_argument("--archive", action="store_true", help="Move files to .agentinit-archive/ instead of deleting.")
    p_remove.add_argument("--force", action="store_true", help="Skip confirmation prompt.")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "new":
        cmd_new(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "remove":
        cmd_remove(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
