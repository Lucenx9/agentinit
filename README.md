# agentinit

![CI](https://github.com/Lucenx9/agentinit/actions/workflows/ci.yml/badge.svg)

A tiny CLI that scaffolds **project context files** for coding agents
(Claude Code, Gemini CLI, GitHub Copilot, Cursor)
using a **router + source-of-truth** layout.

## Why this exists

Coding agents are more consistent when they always have:

- what the project is
- how to work in it (style, rules, testing)
- what's being worked on right now
- what decisions are already made

`agentinit` gives you a minimal, version-controlled set of Markdown files
to keep that context stable and avoid duplicated instruction blocks.

## Design principles

- **One source of truth:** keep durable project context in `docs/*`.
- **Small routers:** keep entry-point files short (don't paste long policies everywhere).
- **Cross-tool friendly:** each tool gets its own small entry file that points to the same `docs/*`.
- **Low bloat:** prefer updating `docs/*` over growing router files.

## Install

Requires Python 3.10+.

```sh
# With pipx (recommended)
pipx install git+https://github.com/Lucenx9/agentinit.git@main

# With pip
pip install git+https://github.com/Lucenx9/agentinit.git@main

# Or run one-off without installing
pipx run --spec git+https://github.com/Lucenx9/agentinit.git@main agentinit --help
```

## Usage

### Create a new project

```sh
agentinit new myproject
```

You will be prompted for a one-line project purpose. Use `--yes` to skip the prompt (sets purpose to "TBD").

Flags:

- `--yes` / `-y` — skip prompts
- `--dir <path>` — create the project under a different parent directory
- `--force` — overwrite agentinit files (including TODO/DECISIONS) if the directory already exists

### Add to an existing project

```sh
cd your-project
agentinit init
```

Copies only missing template files. Safe to run multiple times (idempotent).

Flags:

- `--force` — overwrite existing agentinit files (including TODO/DECISIONS)

### Remove agentinit files

```sh
agentinit remove --dry-run    # preview what would be removed
agentinit remove              # remove with confirmation prompt
agentinit remove --archive    # move to .agentinit-archive/ instead of deleting
agentinit remove --force      # skip confirmation prompt
```

## Generated files

### Source of truth

| File | Purpose |
|------|---------|
| `AGENTS.md` | Primary router — all agents start here |
| `docs/PROJECT.md` | Project purpose, stack, commands, layout, constraints |
| `docs/CONVENTIONS.md` | Style, naming, testing, git workflow |
| `docs/TODO.md` | Active work (in progress / next / blocked / done) |
| `docs/DECISIONS.md` | ADR-lite decision log |

### Tool-specific routers

| File | Tool |
|------|------|
| `CLAUDE.md` | Claude Code |
| `GEMINI.md` | Gemini CLI |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.cursor/rules/project.mdc` | Cursor |

Each router points to `AGENTS.md` → `docs/*`. Keep them short.

## How to keep it healthy

- If guidance changes: update **docs/** first, not router files.
- Keep router files under ~20 lines.
- Log durable decisions in `docs/DECISIONS.md` (date · decision · rationale · alternatives).
- Use `docs/TODO.md` as the "current state" so new sessions start with the right focus.

### Manual setup (no CLI)

Copy these into your repo root:

- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `docs/`, `.github/`, `.cursor/`

Then customize `docs/*` and commit.

## Development

```sh
pip install -e . --group dev
python3 -m pytest tests/ -v
```

## Maintainers

### Release

- Tags follow `vX.Y.Z` (e.g. `v0.2.0`).
- Tag a commit on `main`, then publish a GitHub Release from the Releases UI.

### Safe testing

Use `git worktree` to test changes in isolation:

```sh
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
