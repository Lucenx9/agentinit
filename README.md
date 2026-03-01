# agentinit

![CI](https://github.com/Lucenx9/agentinit/actions/workflows/ci.yml/badge.svg) [![PyPI](https://img.shields.io/pypi/v/agentinit.svg)](https://pypi.org/project/agentinit/) [![Python Versions](https://img.shields.io/pypi/pyversions/agentinit.svg)](https://pypi.org/project/agentinit/)

<img src="https://raw.githubusercontent.com/Lucenx9/agentinit/main/assets/preview.png" width="900" alt="agentinit preview" />

Scaffold tiny, router-first context files so your AI coding agents stop guessing your project setup, style rules, and test commands.

Pure Python standard library. No runtime dependencies. Does not touch your source code.
Works seamlessly with **Claude Code**, **Codex**, **Cursor**, **Copilot**, and **Gemini CLI**.

## 🚀 Start in 60 seconds

```sh
# 1. Install via pipx (recommended)
pipx install agentinit

# 2. Add minimal agent context to your project
cd your-project
agentinit init --minimal
```

### What it does

Instead of giant, token-heavy instruction files for every tool, `agentinit` creates a **router-first** structure. Top-level files stay tiny (~10 lines) and route every agent to `docs/` for the real context.

```text
your-project/
├── AGENTS.md              # The central hub for all agents
├── CLAUDE.md              # Claude Code router
└── docs/
    ├── PROJECT.md         # What this project is (you fill this)
    └── CONVENTIONS.md     # How to work in it (you fill this)
```

**Next steps:** Open `docs/PROJECT.md` and `docs/CONVENTIONS.md` and fill them in.

**Next session:** Tell your agent: _"follow the router for your tool (CLAUDE.md / GEMINI.md / etc) → AGENTS.md"_

---

## 🛠️ Add extras (Skills, MCP, Personality)

Agents can do more than just read conventions. You can inject modular resources directly into your project.

```sh
# View available resources
agentinit add --list

# Add specific capabilities
agentinit add skill code-reviewer
agentinit add mcp github
agentinit add security
agentinit add soul "Lucenx"
```

This creates modular files and automatically links them in your `AGENTS.md`:

```text
your-project/
├── .agents/
│   ├── security.md
│   ├── soul.md
│   ├── mcp-github.md
│   └── skills/
│       └── code-reviewer/
│           └── SKILL.md
└── AGENTS.md              # Automatically updated!
```

_(Adding resources is safe: it skips existing files to avoid duplicates. Use `--force` to overwrite.)_

---

## 🚦 Keep your context clean (Status & CI)

Token limits matter. `agentinit` includes a status checker and linter to prevent context bloat, broken links, and missing information.

```sh
# View line budgets, broken references, and missing details
agentinit status

# Perfect for CI (exits non-zero on hard violations)
agentinit status --check
```

---

## 🤖 AI Prompt: Fill the docs fast

Don't want to write `PROJECT.md` and `CONVENTIONS.md` yourself? After running `agentinit init`, paste this prompt to your favorite AI agent:

> Read the entire repository. Fill in `docs/PROJECT.md` and `docs/CONVENTIONS.md` using **only** facts found in the repo (package files, configs, source code, CI). Do not invent commands. If information is missing, write `TODO: <what's needed>`. Do not modify any other files.

Review the result, fix the TODOs, and commit!

---

<details>
<summary><b>📚 Advanced Usage & Commands</b></summary>

### Core Commands

- `agentinit new <project>` — Create a new directory and scaffold files.
- `agentinit init` — Add missing files to an existing directory.
- `agentinit minimal` — Shortcut for `init --minimal`.
- `agentinit add <type> <name>` — Add modular resources (skills, mcp, security, soul).
- `agentinit status` — Check health, line budgets, and broken links.
- `agentinit lint` — Run `contextlint` to find duplicate text across files.
- `agentinit remove` — Safely remove or archive agent files.

### Common Flags (init / new / minimal)

- `--yes` or `-y` — Skip the interactive wizard and overwrite existing files (same as `--force`).
- `--minimal` — Create only the 4 core files (AGENTS.md, CLAUDE.md, and docs).
- `--detect` — Auto-detect stack and commands from package files (e.g., `package.json`, `pyproject.toml`).
- `--purpose "<text>"` — Prefill the project purpose non-interactively.

### Linting Options

```sh
# Human-readable output
agentinit lint

# Machine-readable JSON for CI
agentinit lint --format json
```

### Removing Files

```sh
agentinit remove --dry-run    # Preview what will happen
agentinit remove              # Remove with confirmation
agentinit remove --archive    # Move to .agentinit-archive/ instead of deleting
```

</details>

<details>
<summary><b>💡 Why Router-First?</b></summary>

- **Saves Tokens:** Re-typing 400 tokens per session across 20 sessions/month wastes 8k+ tokens.
- **Single Source of Truth:** Update a convention once in `docs/`, and Cursor, Copilot, and Claude all see it.
- **Prevents Hallucinations:** Agents stop guessing your test command or trying to use the wrong linting tool.
- **Faster Onboarding:** Human developers benefit from reading `PROJECT.md` just as much as the AI does.

</details>

<details>
<summary><b>⚙️ Installation & Development</b></summary>

Requires **Python 3.10+**.

```sh
# Install (pipx is recommended for CLI apps)
pipx install agentinit

# Update
pipx upgrade agentinit

# Install without pipx
pip install agentinit
```

### Color Output

Colored output is enabled on terminals. It disables automatically in CI or when piping. Force disable it with:

```sh
NO_COLOR=1 agentinit init
```

### Development

```sh
pip install -e . --group dev
python3 -m pytest tests/ -v
```

</details>

## License

MIT
