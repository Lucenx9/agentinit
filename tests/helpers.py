"""Shared test helpers for CLI argparse namespace construction."""

import argparse


def make_args(**kwargs):
    """Build an argparse.Namespace with sensible defaults for cmd_new."""
    defaults = {
        "name": "proj",
        "dir": None,
        "force": False,
        "yes": True,
        "purpose": None,
        "prompt": False,
        "minimal": False,
        "translate_purpose": False,
        "skeleton": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_init_args(**kwargs):
    defaults = {
        "force": False,
        "yes": False,
        "minimal": False,
        "purpose": None,
        "prompt": False,
        "detect": False,
        "translate_purpose": False,
        "skeleton": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_remove_args(**kwargs):
    defaults = {"force": True, "dry_run": False, "archive": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_status_args(**kwargs):
    defaults = {"check": False, "minimal": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_lint_args(**kwargs):
    defaults = {"config": None, "format": "text", "no_dup": False, "root": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_add_args(**kwargs):
    defaults = {"type": "skill", "name": "code-reviewer", "list": False, "force": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_doctor_args(**kwargs):
    defaults = {"minimal": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_sync_args(**kwargs):
    defaults = {"check": False, "diff": False, "root": None, "minimal": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def fill_tbd(root, files):
    """Replace all TBD markers in the given managed files."""
    from pathlib import Path

    root = Path(root)
    for rel in files:
        path = root / rel
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            path.write_text(content.replace("TBD", "done"), encoding="utf-8")
