# Copilot Instructions

## Core instructions

- Install for development: `pip install -e . --group dev`
- Run tests: `python3 -m pytest tests/ -v`
- Run CLI: `agentinit --help`
- No third-party runtime dependencies allowed (stdlib only).
- Source of truth for project context: `AGENTS.md` → `docs/*`.
- Keep router files (CLAUDE.md, GEMINI.md, this file, .cursor/rules/) short; never duplicate docs/* content into them.
- Never overwrite user files (.gitignore, existing TODO.md) without explicit `--force`.
- Template files must never escape the destination directory (symlink and path-traversal checks required).
- Style: PEP 8, snake_case, UPPER_SNAKE_CASE for constants.
- Tests: pytest ≥8, use `tmp_path` + `monkeypatch.chdir`, no mocking of shutil/os.
- Commits: conventional format (`fix:`, `feat:`, `docs:`, `ci:`).

## Router

For full project context, read these files in order:

- `AGENTS.md` (primary router)
- `docs/PROJECT.md`
- `docs/CONVENTIONS.md`
- `docs/TODO.md`
- `docs/DECISIONS.md`
