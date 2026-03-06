"""Scaffold and project file operations shared by CLI commands."""

from __future__ import annotations

import os
import shutil
import sys
import time
from argparse import Namespace
from collections.abc import Callable, Mapping, Sequence, Set
from dataclasses import dataclass
from datetime import date, datetime
from typing import TextIO

from agentinit._llms import _render_llms_content as _render_llms_content_impl
from agentinit._project_updates import apply_updates as _apply_project_updates

Colorize = Callable[[str, str, TextIO | None], str]
PrintNextSteps = Callable[[str], None]
ResolvesWithin = Callable[[str, str], bool]


@dataclass(frozen=True)
class ConsolePalette:
    """ANSI style fragments used by the CLI wrappers."""

    bold: str
    green: str
    yellow: str
    cyan: str
    red: str


@dataclass(frozen=True)
class ScaffoldConfig:
    """Static CLI configuration used by scaffold operations."""

    template_dir: str
    skeletons_dir: str
    managed_files: Sequence[str]
    minimal_managed_files: Sequence[str]
    minimal_template_overrides: Mapping[str, str]
    removable_files: Sequence[str]
    cleanup_dirs: Sequence[str]
    skeleton_ignored_dir_names: Set[str]
    skeleton_ignored_file_names: Set[str]
    skeleton_ignored_file_suffixes: tuple[str, ...]


class ScaffoldOps:
    """Encapsulate scaffold behavior while keeping cli.py thin."""

    def __init__(
        self,
        config: ScaffoldConfig,
        *,
        colorize: Colorize,
        print_next_steps: PrintNextSteps,
        resolves_within: ResolvesWithin,
        palette: ConsolePalette,
    ) -> None:
        self.config = config
        self._colorize = colorize
        self._print_next_steps = print_next_steps
        self._resolves_within = resolves_within
        self._palette = palette

    def _warn_skip(self, rel: str, message: str) -> None:
        print(
            self._colorize(message.format(rel=rel), self._palette.yellow, sys.stderr),
            file=sys.stderr,
        )

    def _error_prefix(self) -> str:
        return self._colorize("Error:", self._palette.red, sys.stderr)

    def _warning_prefix(self) -> str:
        return self._colorize("Warning:", self._palette.yellow, sys.stderr)

    def _note_prefix(self) -> str:
        return self._colorize("Note:", self._palette.yellow, sys.stderr)

    def _created_prefix(self) -> str:
        return self._colorize(
            "Created project", self._palette.green + self._palette.bold
        )

    def _template_source_for(self, rel: str, minimal: bool) -> str:
        if minimal and rel in self.config.minimal_template_overrides:
            override = os.path.join(
                self.config.template_dir, self.config.minimal_template_overrides[rel]
            )
            if os.path.exists(override):
                return override
        return os.path.join(self.config.template_dir, rel)

    def _should_skip_skeleton_dir(self, dirname: str) -> bool:
        return dirname in self.config.skeleton_ignored_dir_names or dirname.endswith(
            ".egg-info"
        )

    def _should_skip_skeleton_file(self, filename: str) -> bool:
        if filename in self.config.skeleton_ignored_file_names:
            return True
        return filename.endswith(self.config.skeleton_ignored_file_suffixes)

    def _relpath_from(self, dest: str, path: str) -> str:
        try:
            return os.path.relpath(path, dest)
        except ValueError:
            return path

    def validate_managed_path(self, dest: str, path: str) -> bool:
        """Return True when a managed path stays inside the project root."""
        dest_real = os.path.realpath(dest)
        rel = self._relpath_from(dest, path)
        parent = os.path.dirname(path) or dest

        if not self._resolves_within(dest_real, parent):
            self._warn_skip(
                rel,
                "Warning: managed path parent resolves outside project, skipping: {rel}",
            )
            return False
        if os.path.lexists(path) and os.path.islink(path):
            self._warn_skip(rel, "Warning: managed path is a symlink, skipping: {rel}")
            return False
        if not self._resolves_within(dest_real, path):
            self._warn_skip(
                rel,
                "Warning: managed path resolves outside project, skipping: {rel}",
            )
            return False
        return True

    def _skip_existing_destination(
        self, rel: str, dst: str, force: bool, skipped: list[str]
    ) -> bool:
        if not os.path.lexists(dst):
            return False
        if os.path.islink(dst):
            self._warn_skip(rel, "Warning: destination is a symlink, skipping: {rel}")
            skipped.append(rel)
            return True
        if os.path.isdir(dst):
            self._warn_skip(rel, "Warning: destination is a directory, skipping: {rel}")
            skipped.append(rel)
            return True
        if rel == ".gitignore":
            skipped.append(rel)
            if force:
                print(
                    self._note_prefix()
                    + " .gitignore already exists, leaving it untouched.",
                    file=sys.stderr,
                )
            return True
        if not force:
            skipped.append(rel)
            return True
        return False

    def _copy_template_file(
        self, src: str, dst: str, rel: str, force: bool, skipped: list[str]
    ) -> bool:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(src, dst)
        except PermissionError:
            if not force:
                print(
                    self._warning_prefix() + f" permission denied, skipping: {rel}",
                    file=sys.stderr,
                )
                skipped.append(rel)
                return False
            os.chmod(dst, 0o644)
            shutil.copy2(src, dst)
        return True

    def copy_template(
        self, dest: str, force: bool = False, minimal: bool = False
    ) -> tuple[list[str], list[str]]:
        """Copy template files into dest."""
        copied: list[str] = []
        skipped: list[str] = []
        dest_real = os.path.realpath(dest)
        files_to_copy = (
            self.config.minimal_managed_files if minimal else self.config.managed_files
        )
        for rel in files_to_copy:
            src = self._template_source_for(rel, minimal)
            dst = os.path.join(dest, rel)
            if not os.path.exists(src):
                continue
            if not self._resolves_within(dest_real, os.path.dirname(dst)):
                self._warn_skip(
                    rel,
                    "Warning: destination parent resolves outside project, skipping: {rel}",
                )
                skipped.append(rel)
                continue
            if self._skip_existing_destination(rel, dst, force, skipped):
                continue
            if not self._resolves_within(dest_real, dst):
                self._warn_skip(
                    rel,
                    "Warning: destination resolves outside project, skipping: {rel}",
                )
                skipped.append(rel)
                continue
            if self._copy_template_file(src, dst, rel, force, skipped):
                copied.append(rel)
        return copied, skipped

    def copy_skeleton(
        self, dest: str, skeleton: str, force: bool = False
    ) -> tuple[list[str], list[str]]:
        """Copy a skeleton tree into dest."""
        copied: list[str] = []
        skipped: list[str] = []
        skeleton_root = os.path.join(self.config.skeletons_dir, skeleton)
        if not os.path.isdir(skeleton_root):
            print(
                self._error_prefix() + f" unknown skeleton: {skeleton!r}",
                file=sys.stderr,
            )
            sys.exit(1)

        dest_real = os.path.realpath(dest)
        for root, dirnames, files in os.walk(skeleton_root):
            dirnames[:] = sorted(
                name for name in dirnames if not self._should_skip_skeleton_dir(name)
            )
            files.sort()
            rel_root = os.path.relpath(root, skeleton_root)
            for filename in files:
                if self._should_skip_skeleton_file(filename):
                    continue
                rel = os.path.normpath(os.path.join(rel_root, filename)).replace(
                    "\\", "/"
                )
                if rel == ".":
                    rel = filename
                src = os.path.join(root, filename)
                dst = os.path.join(dest, rel)
                if not self._resolves_within(dest_real, os.path.dirname(dst)):
                    skipped.append(rel)
                    continue
                if os.path.lexists(dst):
                    if os.path.islink(dst) or os.path.isdir(dst) or not force:
                        skipped.append(rel)
                        continue
                if not self._resolves_within(dest_real, dst):
                    skipped.append(rel)
                    continue
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                copied.append(rel)
        return copied, skipped

    def _render_llms_content(self, dest: str) -> str:
        return _render_llms_content_impl(dest, self.config.template_dir)

    def apply_updates(
        self, dest: str, args: Namespace, *, writable_files: set[str] | None = None
    ) -> None:
        """Apply purpose and wizard data to project files."""
        _apply_project_updates(
            dest,
            args,
            validate_managed_path=self.validate_managed_path,
            refresh_llms_txt=self.refresh_llms_txt,
            error_prefix=self._error_prefix,
            warning_prefix=self._warning_prefix,
            writable_files=writable_files,
        )

    def refresh_llms_txt(self, dest: str) -> float | None:
        """Regenerate llms.txt using project files."""
        start_time = time.perf_counter()
        dest = os.path.abspath(dest)
        llms_path = os.path.join(dest, "llms.txt")
        if not self.validate_managed_path(dest, llms_path):
            return None
        content = self._render_llms_content(dest)
        with open(llms_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return time.perf_counter() - start_time

    def write_todo(self, dest: str, force: bool = False) -> None:
        """Write a bootstrap TODO.md for a new project."""
        path = os.path.join(dest, "docs", "TODO.md")
        if not self.validate_managed_path(dest, path):
            return
        if os.path.exists(path) and not force:
            print(
                self._warning_prefix()
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

    def write_decisions(self, dest: str, force: bool = False) -> None:
        """Write DECISIONS.md with the first ADR-lite entry."""
        path = os.path.join(dest, "docs", "DECISIONS.md")
        if not self.validate_managed_path(dest, path):
            return
        if os.path.exists(path) and not force:
            print(
                self._warning_prefix()
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

    def _ensure_template_dir(self) -> None:
        if os.path.isdir(self.config.template_dir):
            return
        print(
            self._error_prefix()
            + " template directory not found. Installation may be corrupt.",
            file=sys.stderr,
        )
        sys.exit(1)

    def cmd_new(self, args: Namespace) -> None:
        if getattr(args, "yes", False):
            args.prompt = False

        basename = os.path.basename(os.path.normpath(args.name))
        if not basename or basename in (".", ".."):
            print(
                self._error_prefix() + f" invalid project name: {args.name!r}",
                file=sys.stderr,
            )
            print("The project name must not resolve to '.' or '..'.", file=sys.stderr)
            sys.exit(1)

        if args.dir:
            dest = os.path.join(args.dir, args.name)
        else:
            dest = os.path.join(".", args.name)
        dest = os.path.abspath(dest)

        if os.path.exists(dest) and not os.path.isdir(dest):
            print(
                self._error_prefix()
                + f" destination exists and is not a directory: {dest}",
                file=sys.stderr,
            )
            sys.exit(1)

        if os.path.exists(dest) and not args.force:
            print(
                self._error_prefix() + f" directory already exists: {dest}",
                file=sys.stderr,
            )
            print("Use --force to overwrite agentinit files.", file=sys.stderr)
            sys.exit(1)

        self._ensure_template_dir()

        created_dest = False
        if not os.path.exists(dest):
            try:
                os.makedirs(dest)
            except OSError as exc:
                print(
                    self._error_prefix()
                    + f" failed to create project directory: {dest} ({exc})",
                    file=sys.stderr,
                )
                sys.exit(1)
            created_dest = True

        copied, skipped = self.copy_template(
            dest, force=args.force, minimal=args.minimal
        )
        if not copied and not skipped:
            if created_dest and os.path.isdir(dest):
                try:
                    os.rmdir(dest)
                except OSError:
                    pass
            print(
                self._error_prefix()
                + " no template files copied. Installation may be corrupt.",
                file=sys.stderr,
            )
            sys.exit(1)

        self.apply_updates(dest, args, writable_files=set(copied))
        skeleton_copied: list[str] = []
        skeleton_skipped: list[str] = []
        if getattr(args, "skeleton", None):
            skeleton_copied, skeleton_skipped = self.copy_skeleton(
                dest, args.skeleton, force=args.force
            )
        if not args.minimal:
            self.write_todo(dest, force=args.force or "docs/TODO.md" in copied)
            self.write_decisions(
                dest, force=args.force or "docs/DECISIONS.md" in copied
            )

        print(self._created_prefix() + f" at {dest}")
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
        self._print_next_steps(dest)

    def cmd_init(self, args: Namespace) -> None:
        if getattr(args, "yes", False):
            args.prompt = False
            args.force = True

        dest = os.path.abspath(".")
        self._ensure_template_dir()

        copied, skipped = self.copy_template(
            dest, force=args.force, minimal=args.minimal
        )
        if not copied and not skipped:
            print(
                self._error_prefix()
                + " no template files copied. Installation may be corrupt.",
                file=sys.stderr,
            )
            sys.exit(1)

        self.apply_updates(dest, args, writable_files=set(copied))
        skeleton_copied: list[str] = []
        skeleton_skipped: list[str] = []
        if getattr(args, "skeleton", None):
            skeleton_copied, skeleton_skipped = self.copy_skeleton(
                dest, args.skeleton, force=args.force
            )

        if copied:
            print(
                f"{self._colorize('Copied', self._palette.green)} {len(copied)} files:"
            )
            for rel in copied:
                print(f"  {self._colorize('+', self._palette.green)} {rel}")
        if skipped:
            print(
                f"{self._colorize('Skipped', self._palette.yellow)} {len(skipped)} files (already exist):"
            )
            for rel in skipped:
                print(f"  {self._colorize('~', self._palette.yellow)} {rel}")
        if not copied:
            print("All agentinit files already present. Nothing to copy.")
        else:
            self._print_next_steps(dest)
        if skeleton_copied:
            print(f"Skeleton ({args.skeleton}): copied {len(skeleton_copied)} files")
        if skeleton_skipped:
            print(
                f"Skeleton ({args.skeleton}): skipped {len(skeleton_skipped)} file(s) (already exist)"
            )

    def cmd_remove(self, args: Namespace) -> None:
        dest = os.path.abspath(".")
        dry_run = args.dry_run
        archive = args.archive

        found: list[tuple[str, bool]] = []
        missing: list[str] = []
        unsafe: list[str] = []
        for rel in self.config.removable_files:
            path = os.path.join(dest, rel)
            if os.path.lexists(path):
                if not self.validate_managed_path(dest, path):
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

        action = "archive" if archive else "remove"
        for rel, is_dir in found:
            if is_dir:
                print(
                    f"  {self._colorize('!', self._palette.yellow)} {rel} (directory; will skip)"
                )
                continue
            if archive:
                print(f"  {self._colorize('→', self._palette.cyan)} {rel}")
            else:
                print(f"  {self._colorize('×', self._palette.red)} {rel}")
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

        if not args.force:
            actionable = sum(1 for _, is_dir in found if not is_dir)
            if not sys.stdin.isatty():
                print(
                    self._error_prefix()
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

        if archive:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            archive_dir = os.path.join(dest, ".agentinit-archive", ts)
            archived = 0
            for rel, is_dir in found:
                if is_dir:
                    print(
                        self._warning_prefix()
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
                except OSError as exc:
                    print(
                        self._error_prefix() + f" failed to archive {rel}: {exc}",
                        file=sys.stderr,
                    )
                    continue
            print(f"Archived {archived} file(s) to .agentinit-archive/{ts}/")
        else:
            removed = 0
            for rel, is_dir in found:
                if is_dir:
                    print(
                        self._warning_prefix()
                        + f" managed path is a directory, skipping remove: {rel}",
                        file=sys.stderr,
                    )
                    continue
                try:
                    os.remove(os.path.join(dest, rel))
                    removed += 1
                except OSError as exc:
                    print(
                        self._error_prefix() + f" failed to remove {rel}: {exc}",
                        file=sys.stderr,
                    )
                    continue
            print(f"Removed {removed} file(s).")

        for rel in self.config.cleanup_dirs:
            dirpath = os.path.join(dest, rel)
            if os.path.islink(dirpath):
                continue
            if os.path.isdir(dirpath) and not os.listdir(dirpath):
                os.rmdir(dirpath)
                print(f"  Cleaned up empty directory: {rel}/")
