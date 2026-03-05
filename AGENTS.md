# Agent Router

Scaffold tiny context files so AI coding agents stop guessing your setup.
Pure Python stdlib, no runtime dependencies.

Commands:

- Setup: `pip install -e . --group dev`
- Test: `python3 -m pytest tests/ -v`
- Lint/Format: `python3 -m ruff check agentinit tests cli && python3 -m ruff format --check agentinit tests cli` + markdownlint (CI)
- Run: `agentinit --help`

Rules:

1. Read `README.md` for project scope and usage.
2. Keep changes minimal and reversible.
3. Run tests before committing.
