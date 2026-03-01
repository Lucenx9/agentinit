# Repo Layout

- `docs/` — Project documentation (PROJECT.md, CONVENTIONS.md, TODO.md, etc.).
- `AGENTS.md` — Primary agent instructions.
- `CLAUDE.md` — Router file for Claude Code.
- `.claude/rules/` — Modular rule files.

## Domain Boundaries

- **Source Code:** (e.g., `src/` - where the main business logic lives)
- **Tests:** (e.g., `tests/` - must mirror the structure of `src/`)
- **Assets:** (e.g., `public/` or `assets/` - static files)

When adding new top-level directories or significant structural changes, update this file and `docs/PROJECT.md` to keep the map accurate.
