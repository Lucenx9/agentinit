"""Profile detection helpers for scaffolded projects."""

from __future__ import annotations

import os

MINIMAL_PROFILE_MARKERS = (("AGENTS.md", "<!-- agentinit:profile=minimal -->"),)
LEGACY_MINIMAL_AGENTS_SNIPPETS = (
    "**Purpose:** Primary entry point for coding agents in minimal mode.",
    "**Context files (minimal profile):**",
)
LEGACY_MINIMAL_LLMS_SNIPPETS = (
    "[docs/STATE.md](docs/STATE.md): Current State & Focus (missing in this profile)",
    "[docs/TODO.md](docs/TODO.md): Pending Tasks (missing in this profile)",
    "[docs/DECISIONS.md](docs/DECISIONS.md): Architectural Log (missing in this profile)",
)
FULL_PROFILE_ONLY_PATHS = (
    "GEMINI.md",
    os.path.join("docs", "TODO.md"),
    os.path.join("docs", "DECISIONS.md"),
    os.path.join("docs", "STATE.md"),
    os.path.join(".cursor", "rules", "project.mdc"),
    os.path.join(".github", "copilot-instructions.md"),
    os.path.join(".claude", "rules", "coding-style.md"),
    os.path.join(".claude", "rules", "testing.md"),
    os.path.join(".claude", "rules", "repo-map.md"),
    ".contextlintrc.json",
)


def _read_text_if_file(path: str) -> str:
    """Return file contents or an empty string when the file is unavailable."""
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


def looks_like_minimal_profile(dest: str) -> bool:
    """Return True when scaffolded files indicate the minimal profile.

    Prefer an explicit hidden marker in newly generated templates. For older
    minimal scaffolds, fall back to a stricter legacy heuristic that checks for
    multiple exact template snippets and ensures full-profile-only files are
    absent.
    """
    for rel, marker in MINIMAL_PROFILE_MARKERS:
        if marker in _read_text_if_file(os.path.join(dest, rel)):
            return True

    if any(os.path.exists(os.path.join(dest, rel)) for rel in FULL_PROFILE_ONLY_PATHS):
        return False

    agents = _read_text_if_file(os.path.join(dest, "AGENTS.md"))
    llms = _read_text_if_file(os.path.join(dest, "llms.txt"))
    if not agents or not llms:
        return False

    return all(snippet in agents for snippet in LEGACY_MINIMAL_AGENTS_SNIPPETS) and all(
        snippet in llms for snippet in LEGACY_MINIMAL_LLMS_SNIPPETS
    )
