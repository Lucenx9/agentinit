# agentinit

![CI](https://github.com/Lucenx9/agentinit/actions/workflows/ci.yml/badge.svg) [![PyPI](https://img.shields.io/pypi/v/agentinit.svg)](https://pypi.org/project/agentinit/) [![Python Versions](https://img.shields.io/pypi/pyversions/agentinit.svg)](https://pypi.org/project/agentinit/)

<img src="https://raw.githubusercontent.com/Lucenx9/agentinit/main/assets/preview.png" width="900" alt="agentinit preview" />

Scaffold tiny context files so your AI coding agents stop guessing your setup.
Pure Python stdlib, no runtime dependencies, nothing touches your source code.

Works with Claude Code, Codex, Cursor, Copilot, and Gemini CLI.

If you've ever had an agent guess your test command, ignore your style rules,
or forget what the project does — `agentinit` creates a small set of Markdown
files that give every agent the same starting context, every session.

## Save tokens fast (Minimal mode, 2 minutes)

```sh
# Existing repo/folder:
agentinit init --minimal

# New project:
agentinit new myproject --yes --minimal
```

Then fill only `docs/PROJECT.md` and `docs/CONVENTIONS.md`.

Next time, tell your agent: follow `CLAUDE.md` / `AGENTS.md`.

What you get:

```text
your-project/
├── AGENTS.md              # entry point for all agents
├── CLAUDE.md              # Claude Code router
└── docs/
    ├── PROJECT.md         # what this project is (fill this)
    └── CONVENTIONS.md     # how to work in it (fill this)
```

- On a terminal, a short interactive wizard runs automatically — use `--yes` to skip it.
- Use `--purpose "..."` to prefill Purpose non-interactively (e.g. in CI).
- Keep reading only if you want full mode or advanced usage.

### Token savings (rough estimate)

- Tokens saved ≈ tokens you usually re-type per session × number of sessions.
- If you re-type ~200–400 tokens and do 10–20 sessions/month: ~2k–8k tokens/month.
- Actual savings depend on your workflow and which tool loads which files.

## Quickstart (60 seconds)

```sh
# 1. Install (stable)
pipx install agentinit

# Or bleeding edge:
# pipx install git+https://github.com/Lucenx9/agentinit.git@main

# 2. Scaffold a new project
agentinit new myproject --yes
cd myproject

# 3. Open these files in your code editor (VSCode, Cursor, etc.)
#    and fill them in with your project's real info.
#    (see "Fill the docs fast" below for an AI-assisted shortcut)

# 4. Commit and you're done
git init && git add -A && git commit -m "init: add agent context files"
```

For an existing project, run `agentinit init` in the repo root instead of `agentinit new`.

### Fill the docs fast (AI prompt)

After scaffolding, paste this into your agent to auto-populate the docs:

> Read the entire repository. Then fill in `docs/PROJECT.md` and
> `docs/CONVENTIONS.md` using **only** information you find in the repo
> (package files, existing configs, source code, CI workflows, etc.).
> Do not invent commands or assumptions. Where information is missing
> or ambiguous, write `TODO: <what's needed>` so the developer can fill
> it in later. Do not modify any other files.

Review the result, fix any TODOs, and commit.

## Install

Requires Python 3.10+.

```sh
# With pipx (recommended, stable)
pipx install agentinit

# With pip
pip install agentinit

# Or run one-off without installing
pipx run agentinit --help

# Bleeding edge (latest on main)
# pipx install git+https://github.com/Lucenx9/agentinit.git@main
```

## Usage

### Create a new project

```sh
agentinit new myproject
```

On a terminal, a short interactive wizard asks for purpose, environment,
constraints, and commands. Use `--yes` to skip it, or `--purpose "..."` to
prefill non-interactively.

Flags:

- `--yes` / `-y` — skip the interactive wizard
- `--dir <path>` — create the project under a different parent directory
- `--force` — overwrite agentinit files (including TODO/DECISIONS) if the directory already exists
- `--minimal` — create only core files (AGENTS.md, CLAUDE.md, docs/PROJECT.md, docs/CONVENTIONS.md)
- `--purpose "<text>"` — prefill Purpose non-interactively
- `--prompt` — force the interactive wizard (even if stdin is not a TTY)

### Add to an existing project

```sh
cd your-project
agentinit init
```

Copies only missing template files. Safe to run multiple times (idempotent).
The interactive wizard runs by default on a terminal; pass `--yes` to skip it.

Flags:

- `--yes` / `-y` — skip the interactive wizard
- `--force` — overwrite existing agentinit files (including TODO/DECISIONS)
- `--minimal` — create only core files (AGENTS.md, CLAUDE.md, docs/PROJECT.md, docs/CONVENTIONS.md)
- `--purpose "<text>"` — prefill Purpose non-interactively
- `--prompt` — force the interactive wizard (even if stdin is not a TTY)

### Quick minimal scaffold

```sh
agentinit minimal
```

Shortcut for `agentinit init --minimal`. Accepts the same flags (`--yes`, `--force`, `--purpose`, `--prompt`).

### Remove agentinit files

```sh
agentinit remove --dry-run    # preview what would be removed
agentinit remove              # remove with confirmation prompt
agentinit remove --archive    # move to .agentinit-archive/ instead of deleting
agentinit remove --force      # skip confirmation prompt
```

<details>
<summary>Generated files and maintenance tips</summary>

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

### Keeping it healthy

- If guidance changes: update **docs/** first, not router files.
- Keep router files under ~20 lines.
- Log durable decisions in `docs/DECISIONS.md` (date · decision · rationale · alternatives).
- Use `docs/TODO.md` as the "current state" so new sessions start with the right focus.

### Manual setup (no CLI)

Copy into your repo root: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `docs/`, `.github/`, `.cursor/` — then customize `docs/*` and commit.

</details>

## Updating (pipx)

```sh
# From PyPI / GitHub (installed with pipx)
pipx upgrade agentinit

# From a Git install pinned to main
pipx install --force git+https://github.com/Lucenx9/agentinit.git@main
```

## Color output

Output is colored by default on terminals. Color is automatically disabled when
piping, redirecting, or in CI. You can also disable it explicitly:

```sh
NO_COLOR=1 agentinit init
```

Respects the [NO_COLOR](https://no-color.org/) standard and `TERM=dumb`.

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

- `agentinit status` — show which files are present, missing, or still TBD; `--check` for CI
- `--json` output mode for scripting and CI pipelines
- `agentinit build` — validate pointers, enforce line limits, and sanity-check structure

## License

MIT
