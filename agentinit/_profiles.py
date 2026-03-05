"""Profile detection helpers for scaffolded projects."""

from __future__ import annotations

import os

MINIMAL_PROFILE_MARKERS = (
    ("AGENTS.md", "(minimal profile)"),
    ("llms.txt", "(missing in this profile)"),
)


def looks_like_minimal_profile(dest: str) -> bool:
    """Return True when scaffolded files indicate the minimal profile."""
    for rel, marker in MINIMAL_PROFILE_MARKERS:
        path = os.path.join(dest, rel)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                if marker in f.read():
                    return True
        except (OSError, UnicodeDecodeError):
            continue
    return False
