# Quick Start

## Prerequisites

- Python 3.10 or later
- An existing project directory (or use `agentinit new` to create one)

## Install

```sh
# Recommended: install in an isolated environment
pipx install agentinit

# Alternative: install with pip
pip install agentinit
```

## Initialize an existing project

```sh
cd your-project
agentinit init
```

This generates the full set of context files. You'll see output listing each created file.

For smaller projects, use minimal mode:

```sh
agentinit init --minimal
```

## Create a new project from scratch

```sh
agentinit new my-project
```

This creates the `my-project/` directory and scaffolds context files inside it.

To also copy a starter project boilerplate:

```sh
agentinit new my-api --skeleton fastapi
```

## Auto-detect your stack

If your project already has a `pyproject.toml`, `package.json`, `Cargo.toml`, or `go.mod`, agentinit can fill in the commands section automatically:

```sh
agentinit init --detect
```

This reads your manifest files and populates `docs/PROJECT.md` with the correct setup, build, test, lint, and run commands.

## Set a project purpose

Provide a purpose description to pre-fill the Purpose field in `AGENTS.md` and `docs/PROJECT.md`:

```sh
agentinit init --detect --purpose "REST API for managing user subscriptions"
```

For non-interactive environments (CI, scripts), combine with `--yes`:

```sh
agentinit init --detect --purpose "REST API" --yes
```

## Interactive wizard

On a TTY, agentinit runs an interactive wizard by default. It asks for your project purpose and lets you confirm before writing files. You can explicitly request it:

```sh
agentinit init --prompt
```

Or skip it entirely:

```sh
agentinit init --yes
```

## After scaffolding

1. **Fill in `docs/PROJECT.md`** with your project's stack, commands, and layout.
2. **Fill in `docs/CONVENTIONS.md`** with your team's style, naming, testing, and git workflow standards.
3. **Track files in git** so your AI agents can find them:

```sh
git add AGENTS.md CLAUDE.md GEMINI.md llms.txt docs/
```

4. **Start your AI coding agent.** It will read `AGENTS.md` (or the vendor-specific router) automatically and follow your project rules.

## What was generated

See the [Architecture](Architecture) page for a detailed explanation of every generated file, the router-first design, and how minimal vs full profiles differ.
