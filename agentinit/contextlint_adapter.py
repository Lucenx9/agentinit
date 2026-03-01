"""Adapter: prefer external contextlint, fallback to vendored copy."""

from __future__ import annotations


def run_contextlint(args: list[str]) -> int:
    """Run contextlint CLI. Prefer external install, fallback to vendored."""
    try:
        from contextlint.cli import main  # type: ignore[import-not-found]
    except ImportError:
        from agentinit._contextlint.cli import main
    return main(args)


def get_checks_module():
    """Return the checks module (external or vendored) for programmatic use."""
    try:
        from contextlint import checks  # type: ignore[import-not-found]

        return checks
    except ImportError:
        from agentinit._contextlint import checks

        return checks
