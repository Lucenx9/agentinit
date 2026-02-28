# agentinit

![CI](https://github.com/Lucenx9/agentinit/actions/workflows/ci.yml/badge.svg)

Scaffold tiny context files so your AI tools stop asking the same setup questions.
(Supports Claude Code, Codex, Cursor, Copilot, and Gemini CLI.)

## Why this exists

Coding agents are more consistent when they always have:

- what the project is
- how to work in it (style, rules, testing)
- what's being worked on right now
- what decisions are already made

`agentinit` gives you a minimal, version-controlled set of Markdown files
to keep that context stable and avoid duplicated instruction blocks.

## Save tokens fast (Minimal mode, 2 minutes)

```sh
# Existing repo/folder:
agentinit init --minimal

# New project:
agentinit new myproject --yes --minimal
```

Then fill only `docs/PROJECT.md` and `docs/CONVENTIONS.md`.

Next time, tell your agent: follow `CLAUDE.md` / `AGENTS.md`.

### I just want to save tokens

- Minimal mode creates only 4 files: `AGENTS.md`, `CLAUDE.md`, `docs/PROJECT.md`, `docs/CONVENTIONS.md`.
- You only need to fill `docs/PROJECT.md` and `docs/CONVENTIONS.md`.
- Use `--purpose` to prefill Purpose without prompts, or `--prompt` to run a short interactive wizard.
- Keep reading this README only if you want advanced usage.

### Token savings (rough estimate)

- Tokens saved ≈ tokens you usually re-type per session × number of sessions.
- If you re-type ~200–400 tokens and do 10–20 sessions/month: ~2k–8k tokens/month.
- Actual savings depend on your workflow and which tool loads which files.

## Who is this for?

Anyone who uses AI coding agents and wants them to behave consistently
across sessions and tools. If you've ever had an agent guess your test
command, ignore your style rules, or forget what the project does — this
is what agentinit fixes.

## What it does (and doesn't)

**Does:**

- Creates a small set of Markdown files (`AGENTS.md`, `docs/*`, tool-specific routers).
- Gives every agent the same starting context: project purpose, conventions, active work, past decisions.
- Works with Claude Code, Gemini CLI, GitHub Copilot, and Cursor out of the box.

**Doesn't:**

- Run your agents for you.
- Require any runtime dependency — it's pure Python stdlib.
- Touch your source code, configs, or `.gitignore` contents (`.gitignore` is never overwritten).

## Quickstart (60 seconds)

```sh
# 1. Install (stable)
pipx install git+https://github.com/Lucenx9/agentinit.git@v0.2.3

# Or bleeding edge:
# pipx install git+https://github.com/Lucenx9/agentinit.git@main

# 2. Scaffold a new project
agentinit new myproject --yes
cd myproject

# 3. Fill in the docs with your project's real info
#    (see "Fill the docs fast" below for an AI-assisted shortcut)
$EDITOR docs/PROJECT.md docs/CONVENTIONS.md

# 4. Commit and you're done
git init && git add -A && git commit -m "init: add agent context files"
```

For an existing project, run `agentinit init` in the repo root instead of `agentinit new`.

## Fill the docs fast (AI prompt)

After scaffolding, paste this prompt into Claude Code, Cursor, or Gemini CLI
to auto-populate `docs/PROJECT.md` and `docs/CONVENTIONS.md`:

> Read the entire repository. Then fill in `docs/PROJECT.md` and
> `docs/CONVENTIONS.md` using **only** information you find in the repo
> (package files, existing configs, source code, CI workflows, etc.).
> Do not invent commands or assumptions. Where information is missing
> or ambiguous, write `TODO: <what's needed>` so the developer can fill
> it in later. Do not modify any other files.

Review the result, fix any TODOs, and commit.

## Design principles

- **One source of truth:** keep durable project context in `docs/*`.
- **Small routers:** keep entry-point files short (don't paste long policies everywhere).
- **Cross-tool friendly:** each tool gets its own small entry file that points to the same `docs/*`.
- **Low bloat:** prefer updating `docs/*` over growing router files.

## Install

Requires Python 3.10+.

```sh
# With pipx (recommended, stable)
pipx install git+https://github.com/Lucenx9/agentinit.git@v0.2.3

# With pip
pip install git+https://github.com/Lucenx9/agentinit.git@v0.2.3

# Or run one-off without installing
pipx run --spec git+https://github.com/Lucenx9/agentinit.git@v0.2.3 agentinit --help

# Bleeding edge (latest on main)
# pipx install git+https://github.com/Lucenx9/agentinit.git@main
```

## Usage

### Create a new project

```sh
agentinit new myproject
```

Purpose defaults to "TBD". You can set it with `--purpose "my purpose"`,
or run `--prompt` to launch a short interactive wizard (requires a TTY).

Flags:

- `--yes` / `-y` — skip prompts
- `--dir <path>` — create the project under a different parent directory
- `--force` — overwrite agentinit files (including TODO/DECISIONS) if the directory already exists
- `--minimal` — create only core files (AGENTS.md, CLAUDE.md, docs/PROJECT.md, docs/CONVENTIONS.md)
- `--purpose "<text>"` — prefill Purpose without prompts
- `--prompt` — run a short interactive wizard (requires a TTY)

### Add to an existing project

```sh
cd your-project
agentinit init
```

Copies only missing template files. Safe to run multiple times (idempotent).

Flags:

- `--force` — overwrite existing agentinit files (including TODO/DECISIONS)
- `--minimal` — create only core files (AGENTS.md, CLAUDE.md, docs/PROJECT.md, docs/CONVENTIONS.md)
- `--purpose "<text>"` — prefill Purpose without prompts
- `--prompt` — run a short interactive wizard (requires a TTY)

### Quick minimal scaffold

```sh
agentinit minimal
```

Shortcut for `agentinit init --minimal`. Accepts the same flags (`--force`, `--purpose`, `--prompt`).

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
| ---- | ------- |
| `AGENTS.md` | Primary router — all agents start here |
| `docs/PROJECT.md` | Project purpose, stack, commands, layout, constraints |
| `docs/CONVENTIONS.md` | Style, naming, testing, git workflow |
| `docs/TODO.md` | Active work (in progress / next / blocked / done) |
| `docs/DECISIONS.md` | ADR-lite decision log |

### Tool-specific routers

| File | Tool |
| ---- | ---- |
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

## Updating (pipx)

```sh
# From PyPI / GitHub (installed with pipx)
pipx upgrade agentinit

# From a Git install pinned to main
pipx install --force git+https://github.com/Lucenx9/agentinit.git@main
```

## Development

```sh
pip install -e . --group dev
python3 -m pytest tests/ -v
```

<details>
<summary>Maintainers</summary>

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

</details>

## Planned

- `agentinit build` — validate pointers, enforce line limits, and sanity-check structure

## License

MIT
