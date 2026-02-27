# agentinit

Template repository for standardizing Markdown context and memory files used by coding agents.

## Pattern
- Primary router and source of truth: `AGENTS.md`
- Supporting context: `docs/PROJECT.md`, `docs/CONVENTIONS.md`, `docs/TODO.md`, `docs/DECISIONS.md`
- Agent-specific router stubs point back to `AGENTS.md` and `docs/*`

## Included files
- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.github/copilot-instructions.md`
- `.cursor/rules/project.mdc`
- `docs/PROJECT.md`
- `docs/CONVENTIONS.md`
- `docs/TODO.md`
- `docs/DECISIONS.md`

Use this as a starting point, then fill the TBD sections in `docs/*`.
