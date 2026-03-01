# Repo Layout

- `docs/` — Project documentation (PROJECT.md, CONVENTIONS.md, TODO.md, etc.).
- `AGENTS.md` — Primary agent instructions, commands, and conventions.
- `CLAUDE.md` — Router file; keep short and point to AGENTS.md and docs/.
- `.claude/rules/` — Modular rule files loaded by Claude (style, testing, layout).

When adding new top-level directories or significant structural changes,
update this file and `docs/PROJECT.md` to keep the map accurate.
