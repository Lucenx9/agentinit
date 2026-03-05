#!/usr/bin/env python3
"""agentinit — scaffold agent context files into a project."""

import os
import shutil
import sys
from datetime import date, datetime

from agentinit._add import (
    ADD_RESOURCE_TYPES,
    cmd_add as _cmd_add_impl,
)
from agentinit._llms import _render_llms_content as _render_llms_content_impl
from agentinit._parser import build_parser as _build_parser_impl
from agentinit._project_detect import (
    _PURPOSE_PLACEHOLDER,
    _clear_purpose_original_marker,
    _detect_purpose_language,
    _extract_purpose_text,
    _purpose_seems_non_english,
    _replace_commands_section,
    _replace_purpose_text,
    _run_detect,
    _run_detect_conventions,
    _set_purpose_original_marker,
    _translate_text_to_english,
)
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


def _resolves_within(root, path):
    """Return True when path resolves inside root after following symlinks."""
    try:
        root_real = os.path.realpath(root)
        path_real = os.path.realpath(path)
        return os.path.commonpath([root_real, path_real]) == root_real
    except ValueError:
        # On Windows, different drives are never within the same root.
        return False


def _template_source_for(rel, minimal):
    """Resolve template source path for a managed file."""
    if minimal and rel in MINIMAL_TEMPLATE_OVERRIDES:
        override = os.path.join(TEMPLATE_DIR, MINIMAL_TEMPLATE_OVERRIDES[rel])
        if os.path.exists(override):
            return override
    return os.path.join(TEMPLATE_DIR, rel)


def _should_skip_skeleton_dir(dirname):
    """Return True when a skeleton subdirectory is a transient cache/build dir."""
    return dirname in SKELETON_IGNORED_DIR_NAMES or dirname.endswith(".egg-info")


def _should_skip_skeleton_file(filename):
    """Return True when a skeleton file is a transient cache/build artifact."""
    if filename in SKELETON_IGNORED_FILE_NAMES:
        return True
    return filename.endswith(SKELETON_IGNORED_FILE_SUFFIXES)


def _warn_skip(rel, message):
    """Print a standardized skip warning."""
    print(_c(message.format(rel=rel), _YELLOW, sys.stderr), file=sys.stderr)


def _relpath_from(dest, path):
    """Return a relative path label for logging."""
    try:
        return os.path.relpath(path, dest)
    except ValueError:
        return path


def _validate_managed_path(dest, path):
    """Return True when a managed path stays within the project root and is not a symlink."""
    dest_real = os.path.realpath(dest)
    rel = _relpath_from(dest, path)
    parent = os.path.dirname(path) or dest

    if not _resolves_within(dest_real, parent):
        _warn_skip(
            rel,
            "Warning: managed path parent resolves outside project, skipping: {rel}",
        )
        return False
    if os.path.lexists(path) and os.path.islink(path):
        _warn_skip(rel, "Warning: managed path is a symlink, skipping: {rel}")
        return False
    if not _resolves_within(dest_real, path):
        _warn_skip(
            rel,
            "Warning: managed path resolves outside project, skipping: {rel}",
        )
        return False
    return True


def _skip_existing_destination(rel, dst, force, skipped):
    """Handle destination existence policy. Return True when caller should skip."""
    if not os.path.lexists(dst):
        return False
    if os.path.islink(dst):
        _warn_skip(rel, "Warning: destination is a symlink, skipping: {rel}")
        skipped.append(rel)
        return True
    if os.path.isdir(dst):
        _warn_skip(rel, "Warning: destination is a directory, skipping: {rel}")
        skipped.append(rel)
        return True
    if rel == ".gitignore":
        skipped.append(rel)
        if force:
            print(
                _c("Note:", _YELLOW, sys.stderr)
                + " .gitignore already exists, leaving it untouched.",
                file=sys.stderr,
            )
        return True
    if not force:
        skipped.append(rel)
        return True
    return False


def _copy_template_file(src, dst, rel, force, skipped):
    """Copy one template file. Return True when copy succeeded."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        shutil.copy2(src, dst)
    except PermissionError:
        if not force:
            print(
                _c("Warning:", _YELLOW, sys.stderr)
                + f" permission denied, skipping: {rel}",
                file=sys.stderr,
            )
            skipped.append(rel)
            return False
        os.chmod(dst, 0o644)
        shutil.copy2(src, dst)
    return True


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
        src = _template_source_for(rel, minimal)
        dst = os.path.join(dest, rel)
        if not os.path.exists(src):
            continue
        if not _resolves_within(dest_real, os.path.dirname(dst)):
            _warn_skip(
                rel,
                "Warning: destination parent resolves outside project, skipping: {rel}",
            )
            skipped.append(rel)
            continue
        if _skip_existing_destination(rel, dst, force, skipped):
            continue
        if not _resolves_within(dest_real, dst):
            _warn_skip(
                rel, "Warning: destination resolves outside project, skipping: {rel}"
            )
            skipped.append(rel)
            continue
        if _copy_template_file(src, dst, rel, force, skipped):
            copied.append(rel)
    return copied, skipped


def copy_skeleton(dest, skeleton, force=False):
    """Copy a skeleton tree into *dest*. Skip existing files unless force is set."""
    copied = []
    skipped = []
    skeleton_root = os.path.join(SKELETONS_DIR, skeleton)
    if not os.path.isdir(skeleton_root):
        print(
            _c("Error:", _RED, sys.stderr) + f" unknown skeleton: {skeleton!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    dest_real = os.path.realpath(dest)
    for root, dirnames, files in os.walk(skeleton_root):
        dirnames[:] = sorted(
            name for name in dirnames if not _should_skip_skeleton_dir(name)
        )
        files.sort()
        rel_root = os.path.relpath(root, skeleton_root)
        for filename in files:
            if _should_skip_skeleton_file(filename):
                continue
            rel = os.path.normpath(os.path.join(rel_root, filename)).replace("\\", "/")
            if rel == ".":
                rel = filename
            src = os.path.join(root, filename)
            dst = os.path.join(dest, rel)
            if not _resolves_within(dest_real, os.path.dirname(dst)):
                skipped.append(rel)
                continue
            if os.path.lexists(dst):
                if os.path.islink(dst) or os.path.isdir(dst) or not force:
                    skipped.append(rel)
                    continue
            if not _resolves_within(dest_real, dst):
                skipped.append(rel)
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(rel)
    return copied, skipped


def _render_llms_content(dest):
    """Render llms.txt from project files using the llms template."""
    return _render_llms_content_impl(dest, TEMPLATE_DIR)


def apply_updates(dest, args, *, writable_files=None):
    """Apply purpose and wizard data to project files."""
    writable = (
        {os.path.normpath(rel).replace("\\", "/") for rel in writable_files}
        if writable_files is not None
        else None
    )

    def _can_write(rel):
        norm_rel = os.path.normpath(rel).replace("\\", "/")
        return writable is None or norm_rel in writable

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
            if not purpose:
                purpose = input("Purpose (required): ").strip()
            if not purpose:
                purpose = input("Purpose cannot be empty: ").strip()
            if not purpose:
                print("No purpose provided — leaving as placeholder.")
                purpose = ""
            env = input("Environment (OS/device) [optional]: ").strip()
            constraints = input("Constraints [optional]: ").strip()
            commands = input(
                "Commands I can run (comma-separated) [optional]: "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(130)
    else:
        purpose = args.purpose or ""
        env = ""
        constraints = ""
        commands = ""
    translate_requested = bool(getattr(args, "translate_purpose", False))
    translated_for_docs = False

    project_content = ""
    project_path = os.path.join(dest, "docs", "PROJECT.md")
    project_rel = os.path.join("docs", "PROJECT.md")
    project_safe = _validate_managed_path(dest, project_path)
    if not project_safe:
        pass
    elif not os.path.isfile(project_path):
        print(
            _c("Warning:", _YELLOW, sys.stderr)
            + " docs/PROJECT.md is not a regular file; skipping purpose update.",
            file=sys.stderr,
        )
    else:
        with open(project_path, "r", encoding="utf-8") as f:
            content = f.read()

        if _can_write(project_rel):
            if purpose:
                content = content.replace(_PURPOSE_PLACEHOLDER, purpose)
                content = _replace_purpose_text(content, purpose)
                if _detect_purpose_language(purpose) == "en":
                    content = _clear_purpose_original_marker(content)

            if wizard_run:
                if env:
                    content = content.replace(
                        "## Stack",
                        f"## Environment\n\n- OS/device: {env}\n\n## Stack",
                        1,
                    )
                if commands:
                    cmds_list = "\n".join(
                        f"- {c.strip()}" for c in commands.split(",") if c.strip()
                    )
                    content = _replace_commands_section(content, cmds_list)
                if constraints:
                    old_constraints = (
                        "- **Security:** (document security constraints)\n"
                        "- **Performance:** (document performance constraints)\n"
                        "- **Deadlines/Limits:** (document deadline constraints)"
                    )
                    content = content.replace(old_constraints, f"- {constraints}")

            current_purpose = _extract_purpose_text(content)
            current_lang = _detect_purpose_language(current_purpose)
            should_translate = bool(
                current_purpose
                and current_purpose != _PURPOSE_PLACEHOLDER
                and current_lang in {"it", "es", "fr"}
                and (translate_requested or getattr(args, "detect", False))
            )
            if should_translate:
                translated = _translate_text_to_english(current_purpose)
                if translated and translated != current_purpose:
                    content = _replace_purpose_text(content, translated)
                    content = _set_purpose_original_marker(content, current_purpose)
                    translated_for_docs = True
                    print("Purpose translated to English for docs/*")
            elif purpose and _purpose_seems_non_english(purpose):
                print(
                    _c("Warning:", _YELLOW, sys.stderr)
                    + " --purpose appears non-English; keep docs/* in English when possible.",
                    file=sys.stderr,
                )

            if getattr(args, "detect", False):
                content = _run_detect(dest, project_path, content)

            with open(project_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        project_content = content

        if _can_write(project_rel) and not wizard_run and "(not configured)" in content:
            print("Run with --prompt to fill interactively.")

    if wizard_run:
        conv_path = os.path.join(dest, "docs", "CONVENTIONS.md")
        conv_rel = os.path.join("docs", "CONVENTIONS.md")
        if (
            _can_write(conv_rel)
            and _validate_managed_path(dest, conv_path)
            and os.path.isfile(conv_path)
        ):
            safe_defaults = (
                "## Safe Defaults\n\n"
                "- Prefer small, reversible changes\n"
                "- Ask before destructive actions\n"
                "- Provide copy-paste commands\n"
                "- State assumptions\n\n"
            )
            with open(conv_path, "r", encoding="utf-8") as f:
                conv_content = f.read()
            if "## Safe Defaults" not in conv_content:
                if "# Conventions\n" in conv_content:
                    conv_content = conv_content.replace(
                        "# Conventions\n",
                        f"# Conventions\n\n{safe_defaults}",
                        1,
                    )
                else:
                    conv_content = safe_defaults + conv_content
                with open(conv_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(conv_content)

    if getattr(args, "detect", False):
        conv_path = os.path.join(dest, "docs", "CONVENTIONS.md")
        conv_rel = os.path.join("docs", "CONVENTIONS.md")
        if (
            _can_write(conv_rel)
            and _validate_managed_path(dest, conv_path)
            and os.path.isfile(conv_path)
            and project_content
        ):
            with open(conv_path, "r", encoding="utf-8") as f:
                conv_content = f.read()
            conv_updated = _run_detect_conventions(project_content, conv_content)
            if translated_for_docs:
                conv_updated = _translate_text_to_english(conv_updated)
            if conv_updated != conv_content:
                with open(conv_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(conv_updated)
    elif translated_for_docs:
        conv_path = os.path.join(dest, "docs", "CONVENTIONS.md")
        conv_rel = os.path.join("docs", "CONVENTIONS.md")
        if (
            _can_write(conv_rel)
            and _validate_managed_path(dest, conv_path)
            and os.path.isfile(conv_path)
        ):
            with open(conv_path, "r", encoding="utf-8") as f:
                conv_content = f.read()
            conv_updated = _translate_text_to_english(conv_content)
            if conv_updated != conv_content:
                with open(conv_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(conv_updated)

    if _can_write("llms.txt"):
        refresh_llms_txt(dest)


def refresh_llms_txt(dest):
    """Regenerate llms.txt using project files."""
    import time

    start_time = time.perf_counter()
    dest = os.path.abspath(dest)
    llms_path = os.path.join(dest, "llms.txt")
    if not _validate_managed_path(dest, llms_path):
        return None
    content = _render_llms_content(dest)
    with open(llms_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return time.perf_counter() - start_time


def write_todo(dest, force=False):
    """Write a bootstrap TODO.md for a new project.

    Skips if the file already exists unless force is True.
    """
    path = os.path.join(dest, "docs", "TODO.md")
    if not _validate_managed_path(dest, path):
        return
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
    if not _validate_managed_path(dest, path):
        return
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
    created_dest = False
    if not os.path.exists(dest):
        os.makedirs(dest)
        created_dest = True
    copied, skipped = copy_template(dest, force=args.force, minimal=args.minimal)
    if not copied and not skipped:
        # Best-effort cleanup when this command created an empty project dir.
        if created_dest and os.path.isdir(dest):
            try:
                os.rmdir(dest)
            except OSError:
                pass
        print(
            _c("Error:", _RED, sys.stderr)
            + " no template files copied. Installation may be corrupt.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Customize generated files
    apply_updates(dest, args, writable_files=set(copied))
    skeleton_copied = []
    skeleton_skipped = []
    if getattr(args, "skeleton", None):
        skeleton_copied, skeleton_skipped = copy_skeleton(
            dest, args.skeleton, force=args.force
        )
    if not args.minimal:
        write_todo(dest, force=args.force or "docs/TODO.md" in copied)
        write_decisions(dest, force=args.force or "docs/DECISIONS.md" in copied)

    print(_c("Created project", _GREEN + _BOLD) + f" at {dest}")
    if copied:
        print(f"  Copied: {len(copied)} files")
    if skipped:
        print(f"  Skipped (already exist): {', '.join(skipped)}")
    if skeleton_copied:
        print(f"  Skeleton ({args.skeleton}): {len(skeleton_copied)} files")
    if skeleton_skipped:
        print(
            f"  Skeleton skipped (already exist): {', '.join(sorted(skeleton_skipped))}"
        )
    _print_next_steps(dest)


def cmd_init(args):
    # --yes disables the interactive wizard and implies --force.
    if getattr(args, "yes", False):
        args.prompt = False
        args.force = True

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

    apply_updates(dest, args, writable_files=set(copied))
    skeleton_copied = []
    skeleton_skipped = []
    if getattr(args, "skeleton", None):
        skeleton_copied, skeleton_skipped = copy_skeleton(
            dest, args.skeleton, force=args.force
        )

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
        _print_next_steps(dest)
    if skeleton_copied:
        print(f"Skeleton ({args.skeleton}): copied {len(skeleton_copied)} files")
    if skeleton_skipped:
        print(
            f"Skeleton ({args.skeleton}): skipped {len(skeleton_skipped)} file(s) (already exist)"
        )


def cmd_remove(args):
    dest = os.path.abspath(".")
    dry_run = args.dry_run
    archive = args.archive

    # Find which managed files exist.
    found = []
    missing = []
    unsafe = []
    for rel in REMOVABLE_FILES:
        path = os.path.join(dest, rel)
        if os.path.lexists(path):
            if not _validate_managed_path(dest, path):
                unsafe.append(rel)
                continue
            is_dir = os.path.isdir(path) and not os.path.islink(path)
            found.append((rel, is_dir))
        else:
            missing.append(rel)

    if not found:
        print("No agentinit-managed files found. Nothing to do.")
        if missing:
            print(f"  Already absent: {len(missing)} files")
        if unsafe:
            print(f"  Unsafe/skipped: {len(unsafe)} files")
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
    if unsafe:
        for rel in unsafe:
            print(f"  ! {rel} (unsafe path; skipped)")

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
        if os.path.islink(dirpath):
            continue
        if os.path.isdir(dirpath) and not os.listdir(dirpath):
            os.rmdir(dirpath)
            print(f"  Cleaned up empty directory: {d}/")


def cmd_status(args):
    """Show the status of agentinit context files in the current directory."""
    _cmd_status_impl(
        args,
        managed_files=MANAGED_FILES,
        minimal_managed_files=MINIMAL_MANAGED_FILES,
        resolves_within=_resolves_within,
    )


def cmd_add(args):
    """Add a modular agentic resource to the current project."""
    _cmd_add_impl(args, template_dir=TEMPLATE_DIR, resolves_within=_resolves_within)


def cmd_sync(args):
    """Sync vendor router files from AGENTS.md-oriented templates."""
    _cmd_sync_impl(args, template_dir=TEMPLATE_DIR, resolves_within=_resolves_within)


def cmd_lint(args):
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


def _maybe_enable_prompt(args):
    """Enable interactive prompt mode for scaffold commands when appropriate."""
    if args.command not in ("new", "init", "minimal"):
        return
    has_prefills = bool(getattr(args, "purpose", None))
    if getattr(args, "yes", False):
        args.prompt = False
    elif not args.prompt and not has_prefills and sys.stdin.isatty():
        args.prompt = True


def _dispatch_command(args, parser):
    """Dispatch parsed args to the selected command handler."""
    handlers = {
        "new": cmd_new,
        "init": cmd_init,
        "remove": cmd_remove,
        "status": cmd_status,
        "add": cmd_add,
        "lint": cmd_lint,
        "sync": cmd_sync,
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


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    _maybe_enable_prompt(args)
    _dispatch_command(args, parser)


if __name__ == "__main__":
    main()
