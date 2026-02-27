# agentinit

A tiny template repo that standardizes **project context / memory** for coding agents across tools
(Claude Code, Gemini CLI, GitHub Copilot, Cursor) using a **router + source-of-truth** layout.

## Why this exists

Coding agents are more consistent when they always have:
- what the project is
- how to work in it (style, rules, testing)
- what’s being worked on right now
- what decisions are already made

`agentinit` gives you a minimal, version-controlled set of Markdown files to keep that context stable
and avoid duplicated instruction blocks.

## Design principles

- **One source of truth:** keep durable project context in `docs/*`.
- **Small routers:** keep entry-point files short (don’t paste long policies everywhere).
- **Cross-tool friendly:** each tool gets its own small entry file that points to the same `docs/*`.
- **Low bloat:** prefer updating `docs/*` over growing router files.

## Repository layout

### Canonical context
- `AGENTS.md` — canonical router for this template (kept short)
- `docs/PROJECT.md` — project purpose, constraints, layout, key commands (TBD placeholders)
- `docs/CONVENTIONS.md` — style, naming, testing, git workflow (TBD placeholders)
- `docs/TODO.md` — active work (in progress / next / blocked / done)
- `docs/DECISIONS.md` — ADR-lite decision log

### Tool-specific entry points
- `CLAUDE.md` — Claude Code router (points to `AGENTS.md`)
- `GEMINI.md` — Gemini CLI router (points to `AGENTS.md`; may import if supported)
- `.github/copilot-instructions.md` — Copilot repo instructions (no imports; keep essentials inline)
- `.cursor/rules/project.mdc` — Cursor rules (frontmatter + pointers)

## Quick start

### Option A — Use this repo as a template
1. Create a new repo from this template (or copy the files into your repo).
2. Fill the **TBD** sections in:
   - `docs/PROJECT.md`
   - `docs/CONVENTIONS.md`
3. Keep `docs/TODO.md` updated each session.

### Option B — Copy into an existing repository
Copy these into your repo root:
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `docs/`, `.github/`, `.cursor/`

Then:
- customize `docs/*`
- commit everything

## How to keep it healthy

- If guidance changes: update **docs/** first, not router files.
- Keep router files under ~20 lines.
- Log durable decisions in `docs/DECISIONS.md` (date · decision · rationale · alternatives).
- Use `docs/TODO.md` as the “current state” so new sessions start with the right focus.

## Planned

- `agentinit init` — scaffold these files into any project (minimal/recommended presets)
- `agentinit build` — validate pointers, enforce line limits, and sanity-check structure

## License

MIT
