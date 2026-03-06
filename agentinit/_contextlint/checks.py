"""Core lint checks for AI agent context files."""

from __future__ import annotations

import fnmatch
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOFT_WARN_LINES = 200
HARD_FAIL_LINES = 300
ROUTER_WARN_LINES = 50

# Root-level files always injected into every AI prompt.
ALWAYS_HOT_FILES: list[str] = [
    ".cursorrules",
    ".github/copilot-instructions.md",
    ".windsurfrules",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "codex.md",
    "opencode.md",
]

# Glob patterns (relative to repo root) for always-hot rule directories.
ALWAYS_HOT_GLOBS: list[str] = [
    ".claude/rules/**/*.md",
    ".cursor/rules/**/*.mdc",
    ".windsurf/rules/**/*.md",
    ".windsurf/rules/**/*.mdc",
]

# Flat set for quick "is this file hot?" lookups.
ALWAYS_HOT: set[str] = set(ALWAYS_HOT_FILES)

# Router files should be short and point to canonical docs.
ROUTER_FILES: set[str] = {"CLAUDE.md", "GEMINI.md"}

# Directory names to skip during discovery.
_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "dist",
        "build",
        ".venv",
        "venv",
        "__pycache__",
    }
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_CONFIG_NAMES = (".contextlintrc.json", ".contextlintrc")


def _to_int_or_default(value: object, default: int) -> int:
    """Parse *value* as int; return *default* when invalid."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _string_list(value: object) -> list[str]:
    """Return only string items from list-like config values."""
    if not isinstance(value, (list, tuple, set)):
        return []
    return [item for item in value if isinstance(item, str)]


def _find_config_path(root: Path, config_path: Path | None) -> Path | None:
    """Return explicit config path or first existing default config path."""
    if config_path is not None:
        return config_path if config_path.is_file() else None
    for name in _CONFIG_NAMES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def _load_config_data(path: Path | None) -> dict[str, object] | None:
    """Read and parse config JSON as a dict."""
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _apply_nested_config(cfg: Config, data: dict[str, object]) -> None:
    """Apply nested config format sections to *cfg*."""
    lb = data.get("line_budget", {})
    if isinstance(lb, dict):
        cfg.default_warn = _to_int_or_default(lb.get("default_warn"), SOFT_WARN_LINES)
        cfg.default_error = _to_int_or_default(lb.get("default_error"), HARD_FAIL_LINES)
        cfg.router_warn_lines = _to_int_or_default(
            lb.get("router_warn"), ROUTER_WARN_LINES
        )
        per_file = lb.get("per_file", {})
        if isinstance(per_file, dict):
            parsed_per_file: dict[str, int] = {}
            for k, v in per_file.items():
                parsed = _to_int_or_default(v, -1)
                if parsed >= 0:
                    parsed_per_file[k] = parsed
            cfg.per_file_error = parsed_per_file

    ig = data.get("ignore", {})
    if isinstance(ig, dict):
        cfg.ignore_paths = set(_string_list(ig.get("paths", [])))
        cfg.ignore_refs = set(_string_list(ig.get("refs", [])))
        for f in _string_list(ig.get("files", [])):  # legacy alias
            cfg.ignore_paths.add(f)

    disc = data.get("discovery", {})
    if isinstance(disc, dict):
        cfg.extra_globs = _string_list(disc.get("extra_globs", []))
        cfg.disable_default_discovery = bool(disc.get("disable_defaults", False))


def _apply_legacy_config(cfg: Config, data: dict[str, object]) -> None:
    """Apply flat legacy config format to *cfg*."""
    cfg.default_warn = _to_int_or_default(data.get("soft_warn_lines"), SOFT_WARN_LINES)
    cfg.default_error = _to_int_or_default(data.get("hard_fail_lines"), HARD_FAIL_LINES)
    cfg.router_warn_lines = _to_int_or_default(
        data.get("router_warn_lines"), ROUTER_WARN_LINES
    )
    legacy_ignore = data.get("ignore", [])
    cfg.ignore_paths = set(_string_list(legacy_ignore))


@dataclass
class Config:
    # Line budget
    default_warn: int = SOFT_WARN_LINES
    default_error: int = HARD_FAIL_LINES
    per_file_error: dict[str, int] = field(default_factory=dict)
    router_warn_lines: int = ROUTER_WARN_LINES
    # Ignore
    ignore_paths: set[str] = field(default_factory=set)  # fnmatch patterns → skip file
    ignore_refs: set[str] = field(default_factory=set)  # skip these ref targets
    # Discovery
    extra_globs: list[str] = field(default_factory=list)
    disable_default_discovery: bool = False


def load_config(root: Path, config_path: Path | None = None) -> Config:
    """Load config from *.contextlintrc.json* (or legacy *.contextlintrc*)."""
    path = _find_config_path(root, config_path)
    data = _load_config_data(path)
    if data is None:
        return Config()

    cfg = Config()
    is_nested = any(k in data for k in ("line_budget", "ignore", "discovery"))
    if is_nested:
        _apply_nested_config(cfg, data)
    else:
        _apply_legacy_config(cfg, data)

    return cfg


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


@dataclass
class Diagnostic:
    path: str
    message: str
    hard: bool = False  # True → exit 1
    lineno: int = 0  # 0 = not applicable


@dataclass
class LintResult:
    diagnostics: list[Diagnostic] = field(default_factory=list)
    file_sizes: dict[str, int] = field(default_factory=dict)  # rel → line count

    @property
    def has_hard(self) -> bool:
        return any(d.hard for d in self.diagnostics)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def _rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def _iter_glob(root: Path, pattern: str) -> list[Path]:
    """Glob *pattern* under *root*, skipping *_EXCLUDE_DIRS* directories."""
    results: list[Path] = []
    for p in sorted(root.glob(pattern)):
        if not p.is_file():
            continue
        try:
            parts = p.relative_to(root).parts
        except ValueError:
            continue
        if any(part in _EXCLUDE_DIRS for part in parts[:-1]):
            continue
        results.append(p)
    return results


def _is_ignored(rel: str, ignore_paths: set[str]) -> bool:
    rel_posix = rel.replace(os.sep, "/")
    return any(fnmatch.fnmatch(rel_posix, pat) for pat in ignore_paths)


def _collect_default_discovery(root: Path, add: Callable[[Path, bool], None]) -> None:
    """Collect built-in always-hot files and docs markdown files."""
    for name in ALWAYS_HOT_FILES:
        p = root / name
        if p.is_file():
            add(p, hot=True)

    for pattern in ALWAYS_HOT_GLOBS:
        for f in _iter_glob(root, pattern):
            add(f, hot=True)

    docs_dir = root / "docs"
    if docs_dir.is_dir():
        for f in _iter_glob(root, "docs/**/*.md"):
            add(f, hot=False)


def _collect_extra_discovery(
    root: Path, patterns: list[str], add: Callable[[Path, bool], None]
) -> None:
    """Collect files discovered via user-provided glob patterns."""
    for pattern in patterns:
        for f in _iter_glob(root, pattern):
            add(f, hot=False)


def _apply_ignore_filter(
    root: Path, found: list[Path], hot_rels: set[str], ignore_paths: set[str]
) -> tuple[list[Path], set[str]]:
    """Filter discovered files and hot paths by ignore patterns."""
    if not ignore_paths:
        return found, hot_rels
    filtered_files = [f for f in found if not _is_ignored(_rel(f, root), ignore_paths)]
    filtered_hot = {r for r in hot_rels if not _is_ignored(r, ignore_paths)}
    return filtered_files, filtered_hot


def _discover_context_files(root: Path, config: Config) -> tuple[list[Path], set[str]]:
    """Return *(files, hot_rels)* — both sorted/deterministic.

    *hot_rels* is the set of relative paths that are always-hot (subject to
    the hard line-budget limit).
    """
    seen: set[Path] = set()
    found: list[Path] = []
    hot_rels: set[str] = set()

    def _add(p: Path, hot: bool = False) -> None:
        if p not in seen:
            seen.add(p)
            found.append(p)
        if hot:
            try:
                hot_rels.add(_rel(p, root))
            except ValueError:
                pass

    if not config.disable_default_discovery:
        _collect_default_discovery(root, _add)

    _collect_extra_discovery(root, config.extra_globs, _add)

    found.sort(key=lambda p: _rel(p, root))
    found, hot_rels = _apply_ignore_filter(root, found, hot_rels, config.ignore_paths)
    return found, hot_rels


def _is_hot_rel(rel: str) -> bool:
    """Return True when *rel* is treated as always-hot context."""
    rel_posix = rel.replace(os.sep, "/")
    if rel_posix in ALWAYS_HOT:
        return True
    return any(fnmatch.fnmatch(rel_posix, pattern) for pattern in ALWAYS_HOT_GLOBS)


def _select_context_files(
    root: Path, files: list[Path], hot_rels: set[str], selected_paths: set[str]
) -> tuple[list[Path], set[str]]:
    """Restrict discovered files to an explicit relative-path allowlist."""
    selected = {path.replace(os.sep, "/") for path in selected_paths}
    filtered_files = [
        fpath for fpath in files if _rel(fpath, root).replace(os.sep, "/") in selected
    ]
    seen = {_rel(fpath, root).replace(os.sep, "/") for fpath in filtered_files}

    for rel in sorted(selected):
        candidate = root / rel
        if rel not in seen and candidate.is_file():
            filtered_files.append(candidate)

    filtered_files.sort(key=lambda p: _rel(p, root))
    filtered_hot = {rel for rel in selected if rel in hot_rels or _is_hot_rel(rel)}
    return filtered_files, filtered_hot


def discover_context_files(root: Path, config: Config | None = None) -> list[Path]:
    """Public API: return all context files under *root* in deterministic order."""
    root = root.resolve()
    if config is None:
        config = load_config(root)
    files, _ = _discover_context_files(root, config)
    return files


# ---------------------------------------------------------------------------
# Check 1 — line budget
# ---------------------------------------------------------------------------


def _check_line_budget(
    root: Path,
    files: list[Path],
    hot_rels: set[str],
    result: LintResult,
    config: Config,
) -> None:
    for fpath in files:
        rel = _rel(fpath, root)
        try:
            lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        count = len(lines)
        result.file_sizes[rel] = count

        hot = rel in hot_rels
        in_docs = rel.startswith("docs/") or rel.startswith("docs" + os.sep)
        error_limit = config.per_file_error.get(rel, config.default_error)

        if hot and count >= error_limit:
            result.diagnostics.append(
                Diagnostic(
                    rel, f"{count} lines (hard limit is {error_limit})", hard=True
                )
            )
        elif count >= config.default_warn:
            if in_docs:
                result.diagnostics.append(
                    Diagnostic(
                        rel,
                        f"{count} lines — consider splitting (docs/ files never fail)",
                    )
                )
            elif hot:
                result.diagnostics.append(
                    Diagnostic(
                        rel, f"{count} lines (soft warn at {config.default_warn})"
                    )
                )
            else:
                result.diagnostics.append(
                    Diagnostic(rel, f"{count} lines — consider trimming")
                )


# ---------------------------------------------------------------------------
# Check 2 — broken references
# ---------------------------------------------------------------------------

_MD_LINK_RE = re.compile(r"\[.*?\]\(([^)]+)\)")
# @token — broad capture; _looks_like_path() then filters out @username mentions
_AT_IMPORT_RE = re.compile(r"(?<![A-Za-z0-9])@([\w./-]+)")
_STANDALONE_PATH_RE = re.compile(
    r"^[\s\-*_>`]*"
    r"[`*_]*"
    r"(\.{0,2}/?"
    r"[A-Za-z0-9_\-./]+"
    r")"
    r"[`*_]*"
    r"[\s]*$"
)
_SKIP_RE = re.compile(r"^(https?://|mailto:|#)")


def _looks_like_path(s: str) -> bool:
    """Heuristic: has a slash or ends with a known file extension."""
    if "/" in s:
        return True
    return bool(re.search(r"\.\w{1,6}$", s))


def _extract_refs_from_line(line: str) -> list[str]:
    """Extract markdown links, @imports, and standalone path candidates."""
    refs: list[str] = []

    refs.extend(m.group(1) for m in _MD_LINK_RE.finditer(line))

    for m in _AT_IMPORT_RE.finditer(line):
        token = m.group(1)
        if _looks_like_path(token):
            refs.append(token)

    sm = _STANDALONE_PATH_RE.match(line)
    if sm:
        candidate = sm.group(1)
        if _looks_like_path(candidate):
            refs.append(candidate)

    return refs


def _normalize_ref(ref: str) -> str:
    """Normalize raw reference by stripping in-line anchors."""
    return ref.split("#", 1)[0]


def _should_skip_ref(ref: str, seen: set[str], config: Config) -> bool:
    """Return True when *ref* should not be validated."""
    if not ref:
        return True
    if _SKIP_RE.match(ref):
        return True
    if ref in config.ignore_refs or Path(ref).name in config.ignore_refs:
        return True
    if ref in seen:
        return True
    return False


def _resolve_ref_target(root: Path, fpath: Path, ref: str) -> Path:
    """Resolve *ref* from file context, preserving repo-root semantics for /paths."""
    ref_path = Path(ref)
    if ref_path.is_absolute():
        return (root / ref.lstrip("/\\")).resolve()
    return (fpath.parent / ref).resolve()


def _check_refs_in_file(
    root: Path, fpath: Path, rel_name: str, result: LintResult, config: Config
) -> None:
    try:
        raw = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return

    root_resolved = root.resolve()
    seen: set[str] = set()

    for lineno, line in enumerate(raw, 1):
        for raw_ref in _extract_refs_from_line(line):
            ref = _normalize_ref(raw_ref)
            if _should_skip_ref(ref, seen, config):
                continue
            seen.add(ref)

            target = _resolve_ref_target(root, fpath, ref)
            try:
                target.relative_to(root_resolved)
            except ValueError:
                result.diagnostics.append(
                    Diagnostic(
                        rel_name,
                        f"ref '{ref}' escapes repo root — ignored",
                        hard=False,
                        lineno=lineno,
                    )
                )
                continue

            if not target.exists():
                result.diagnostics.append(
                    Diagnostic(
                        rel_name, f"broken ref → {ref}", hard=True, lineno=lineno
                    )
                )


def _check_broken_refs(
    root: Path, files: list[Path], result: LintResult, config: Config
) -> None:
    for fpath in files:
        _check_refs_in_file(root, fpath, _rel(fpath, root), result, config)


# ---------------------------------------------------------------------------
# Check 3 — router sanity (CLAUDE.md, GEMINI.md)
# ---------------------------------------------------------------------------

_POINTER_RE = re.compile(r"(AGENTS\.md|docs/)", re.IGNORECASE)


def _check_router_sanity(root: Path, result: LintResult, config: Config) -> None:
    for name in sorted(ROUTER_FILES):
        fpath = root / name
        if not fpath.is_file():
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        count = len(text.splitlines())
        if count > config.router_warn_lines:
            result.diagnostics.append(
                Diagnostic(
                    name,
                    f"{count} lines — router files should be short (<={config.router_warn_lines})",
                )
            )

        if not _POINTER_RE.search(text):
            result.diagnostics.append(
                Diagnostic(name, "no pointer to AGENTS.md or docs/ — add one")
            )


# ---------------------------------------------------------------------------
# Check 4 — duplicate blocks across files
# ---------------------------------------------------------------------------

_DUP_MIN_LINES = 4


def _build_duplicate_windows(
    root: Path, files: list[Path]
) -> dict[str, list[tuple[int, str]]]:
    """Build per-file normalized windows used for duplicate detection."""
    file_windows: dict[str, list[tuple[int, str]]] = {}
    for fpath in files:
        rel = _rel(fpath, root)
        try:
            raw = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        norm: list[tuple[int, str]] = [
            (i, line.strip()) for i, line in enumerate(raw, 1) if line.strip()
        ]
        if len(norm) < _DUP_MIN_LINES:
            continue

        windows: list[tuple[int, str]] = []
        for i in range(len(norm) - _DUP_MIN_LINES + 1):
            start_lineno = norm[i][0]
            block = "\n".join(text for _, text in norm[i : i + _DUP_MIN_LINES])
            windows.append((start_lineno, block))
        file_windows[rel] = windows
    return file_windows


def _build_duplicate_index(
    file_windows: dict[str, list[tuple[int, str]]],
) -> dict[str, list[tuple[str, int]]]:
    """Build fingerprint index from per-file windows."""
    fp_to_locs: dict[str, list[tuple[str, int]]] = {}
    for rel, windows in file_windows.items():
        emitted: set[str] = set()
        for lineno, fp in windows:
            if fp not in emitted:
                emitted.add(fp)
                fp_to_locs.setdefault(fp, []).append((rel, lineno))
    return fp_to_locs


def _check_duplicates(root: Path, files: list[Path], result: LintResult) -> None:
    file_windows = _build_duplicate_windows(root, files)
    fp_to_locs = _build_duplicate_index(file_windows)

    reported: set[frozenset[str]] = set()
    for _, locs in sorted(fp_to_locs.items()):  # sort for determinism
        files_set = {rel for rel, _ in locs}
        if len(files_set) < 2:
            continue
        pair = frozenset(files_set)
        if pair in reported:
            continue
        reported.add(pair)

        # First occurrence per file.
        first: dict[str, int] = {}
        for rel, lineno in locs:
            if rel not in first or lineno < first[rel]:
                first[rel] = lineno

        sorted_files = sorted(first)
        primary = sorted_files[0]
        others = [f"{f}:{first[f]}" for f in sorted_files[1:]]
        result.diagnostics.append(
            Diagnostic(
                primary,
                f"duplicate block found also in {', '.join(others)} — consider consolidating",
                hard=False,
                lineno=first[primary],
            )
        )


# ---------------------------------------------------------------------------
# Check 5 — top offenders summary
# ---------------------------------------------------------------------------


def top_offenders(result: LintResult, n: int = 3) -> list[tuple[str, int]]:
    """Return the *n* largest context files by line count."""
    items = sorted(result.file_sizes.items(), key=lambda x: x[1], reverse=True)
    return items[:n]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_checks(
    root: Path,
    config: Config | None = None,
    check_dup: bool = True,
    selected_paths: set[str] | None = None,
) -> LintResult:
    """Run all checks against *root* and return a :class:`LintResult`."""
    root = root.resolve()
    if config is None:
        config = load_config(root)
    files, hot_rels = _discover_context_files(root, config)
    if selected_paths is not None:
        files, hot_rels = _select_context_files(root, files, hot_rels, selected_paths)
    result = LintResult()

    _check_line_budget(root, files, hot_rels, result, config)
    _check_broken_refs(root, files, result, config)
    _check_router_sanity(root, result, config)
    if check_dup:
        _check_duplicates(root, files, result)

    return result
