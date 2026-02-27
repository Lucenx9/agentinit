# agentinit

A tiny template repo that standardizes **project context / memory** for coding agents
across tools (Claude Code, Gemini CLI, GitHub Copilot, Cursor)
using a **router + source-of-truth** layout.

## Why this exists

Coding agents are more consistent when they always have:
- what the project is
- how to work in it (style, rules, testing)
- what’s being worked on right now
- what decisions are already made

`agentinit` gives you a minimal, version-controlled set of Markdown files
to keep that context stable and avoid duplicated instruction blocks.

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

## Install

Requires Python 3.10+. pipx is recommended for installing standalone Python CLIs in isolated environments.

```
# Install from GitHub (latest)
pipx install git+https://github.com/Lucenx9/agentinit.git@main

# Install a pinned release
pipx install git+https://github.com/Lucenx9/agentinit.git@v0.1.0

# Or run one-off without installing
pipx run --spec git+https://github.com/Lucenx9/agentinit.git@main agentinit --help
```

You can also install with pip (`pip install git+https://...`) or run directly from a clone:

```
git clone https://github.com/Lucenx9/agentinit.git
python -m agentinit --help
```

## Usage

### Create a new project

```
agentinit new myproject
```

You will be prompted for a one-line project purpose. Use `--yes` to skip the prompt (sets purpose to "TBD").

Flags:
- `--yes` / `-y` — skip prompts
- `--dir <path>` — create the project under a different parent directory
- `--force` — overwrite agentinit files if the directory already exists (user files are never deleted)

### Add to an existing project

```
cd your-project
agentinit init
```

Copies only missing template files. Safe to run multiple times (idempotent).

Flags:
- `--force` — overwrite existing agentinit files

### Remove agentinit files

```
agentinit remove --dry-run    # preview what would be removed
agentinit remove              # remove with confirmation prompt
agentinit remove --archive    # move to .agentinit-archive/ instead of deleting
agentinit remove --force      # skip confirmation prompt
```

### Manual setup (no CLI)

Copy these into your repo root:
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `docs/`, `.github/`, `.cursor/`

Then customize `docs/*` and commit.

## How to keep it healthy

- If guidance changes: update **docs/** first, not router files.
- Keep router files under ~20 lines.
- Log durable decisions in `docs/DECISIONS.md` (date · decision · rationale · alternatives).
- Use `docs/TODO.md` as the “current state” so new sessions start with the right focus.

## Validation

This template was validated in a sandbox worktree with Claude Code and Gemini CLI.
Both tools correctly routed via `AGENTS.md` → `docs/*` without guessing commands.

## Safe testing

Use `git worktree` to test changes in isolation:

```
git worktree add ../agentinit-test -b agentinit-test
cd ../agentinit-test
# test template changes
cd -
git worktree remove ../agentinit-test
git branch -D agentinit-test
```

## Planned

- `agentinit build` — validate pointers, enforce line limits, and sanity-check structure

## License

MIT
