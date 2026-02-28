# agentinit

## Purpose

CLI tool that scaffolds standardized agent context/memory files (AGENTS.md, docs/*)
into any project, so coding agents (Claude Code, Gemini CLI, Copilot, Cursor) share
a single source of truth for project knowledge.

## Stack

- Runtime: Python >=3.10 (CPython)
- Language: Python 3
- Build: setuptools (pyproject.toml)
- CI: GitHub Actions (smoke tests, markdownlint, lychee link checker)

## Commands

- Setup: `pip install -e . --group dev`
- Test: `python3 -m pytest tests/ -v`
- Lint/Format: markdownlint via CI (no local lint configured)
- Run: `agentinit --help`

## Layout

- `AGENTS.md`: Primary router.
- `docs/`: Source-of-truth context and memory files.
- `agentinit/`: Python package (cli.py + template/).
- `agentinit/template/`: Scaffold files copied into new projects.
- `tests/`: pytest test suite.
- `cli/agentinit.py`: Legacy shim (not installed via package).

## Constraints

- Must work on Python 3.10+ with no third-party runtime dependencies.
- Template files must never escape the destination directory (symlink/path-traversal checks).
- .gitignore is never overwritten, even with --force.
