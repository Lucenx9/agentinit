"""Argument parser builder for agentinit CLI."""

import argparse
import importlib.metadata


def build_parser(skeleton_choices, add_resource_types):
    parser = argparse.ArgumentParser(
        prog="agentinit",
        description="Scaffold agent context files into a project.",
    )
    try:
        _version = importlib.metadata.version("agentinit")
    except importlib.metadata.PackageNotFoundError:
        _version = "dev"
    parser.add_argument(
        "--version",
        action="version",
        version=_version,
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
        help="Create only AGENTS.md, CLAUDE.md, llms.txt, docs/PROJECT.md, and docs/CONVENTIONS.md.",
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
    p_new.add_argument(
        "--translate-purpose",
        action="store_true",
        help="Translate non-English Purpose text to English for docs/*.",
    )
    p_new.add_argument(
        "--skeleton",
        choices=skeleton_choices,
        help="Copy starter boilerplate after context files (e.g. fastapi).",
    )

    # agentinit init
    p_init = sub.add_parser(
        "init", help="Add missing agent context files to the current directory."
    )
    p_init.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip interactive wizard and overwrite existing files (alias for --force).",
    )
    p_init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing agentinit files (including TODO/DECISIONS).",
    )
    p_init.add_argument(
        "--minimal",
        action="store_true",
        help="Create only AGENTS.md, CLAUDE.md, llms.txt, docs/PROJECT.md, and docs/CONVENTIONS.md.",
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
    p_init.add_argument(
        "--translate-purpose",
        action="store_true",
        help="Translate non-English Purpose text to English for docs/*.",
    )
    p_init.add_argument(
        "--skeleton",
        choices=skeleton_choices,
        help="Copy starter boilerplate after context files (e.g. fastapi).",
    )

    # agentinit minimal  (shortcut for init --minimal)
    p_minimal = sub.add_parser("minimal", help="Shortcut for 'init --minimal'.")
    p_minimal.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip interactive wizard and overwrite existing files (alias for --force).",
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
    p_minimal.add_argument(
        "--translate-purpose",
        action="store_true",
        help="Translate non-English Purpose text to English for docs/*.",
    )
    p_minimal.add_argument(
        "--skeleton",
        choices=skeleton_choices,
        help="Copy starter boilerplate after context files (e.g. fastapi).",
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

    # agentinit add
    p_add = sub.add_parser("add", help="Add modular agentic resources.")
    p_add.add_argument(
        "type",
        choices=add_resource_types,
        help="Resource type to add.",
    )
    p_add.add_argument("name", nargs="?", default=None, help="Resource name.")
    p_add.add_argument(
        "--list", action="store_true", help="List available resources of this type."
    )
    p_add.add_argument(
        "--force", action="store_true", help="Overwrite if the resource already exists."
    )

    # agentinit lint
    p_lint = sub.add_parser(
        "lint",
        help="Run contextlint checks on agent context files.",
    )
    p_lint.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Path to .contextlintrc.json config file.",
    )
    p_lint.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    p_lint.add_argument(
        "--no-dup",
        action="store_true",
        default=False,
        help="Disable duplicate-block detection.",
    )
    p_lint.add_argument(
        "--root",
        default=None,
        help="Repository root to lint (default: current directory).",
    )

    # agentinit refresh-llms
    p_refresh = sub.add_parser(
        "refresh-llms",
        aliases=["refresh"],
        help="Regenerate llms.txt from project files (fast, existing files only).",
    )
    p_refresh.add_argument(
        "--root",
        default=None,
        help="Project root (default: current directory).",
    )

    # agentinit sync
    p_sync = sub.add_parser(
        "sync",
        help="Sync vendor router files from AGENTS.md-oriented templates.",
    )
    p_sync.add_argument(
        "--check",
        action="store_true",
        help="Exit with code 1 if router files are out of sync (CI mode).",
    )
    p_sync.add_argument(
        "--minimal",
        action="store_true",
        help="Sync only the minimal router set (or force minimal mode).",
    )
    p_sync.add_argument(
        "--root",
        default=None,
        help="Project root (default: current directory).",
    )

    return parser
