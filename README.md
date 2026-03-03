# agentinit

![CI](https://github.com/Lucenx9/agentinit/actions/workflows/ci.yml/badge.svg) [![PyPI](https://img.shields.io/pypi/v/agentinit.svg)](https://pypi.org/project/agentinit/) [![Python Versions](https://img.shields.io/pypi/pyversions/agentinit.svg)](https://pypi.org/project/agentinit/)

<img src="https://raw.githubusercontent.com/Lucenx9/agentinit/main/assets/preview.png" width="900" alt="agentinit preview" />

Scaffold **hardened, router-first** context files so your AI coding agents stop guessing and start delivering.

Pure Python standard library. No runtime dependencies. Generates 2026-ready manifests for **Claude Code**, **Cursor**, **Copilot**, and **Gemini CLI**. `llms.txt` also provides discovery-friendly routing for other tools (for example, **Windsurf**).

`llms.txt` now includes auto-summary and mandates.

## 🚀 Start in 60 seconds

```sh
# 1. Install via pipx (recommended)
pipx install agentinit

# 2. Initialize hardened context in your project
cd your-project
agentinit init --minimal
```

## 📘 Documentation

Use the wiki for full, example-driven docs:

- [Wiki Home](https://github.com/Lucenx9/agentinit/wiki)
- [Quick Start](https://github.com/Lucenx9/agentinit/wiki/Quick-Start)
- [Commands](https://github.com/Lucenx9/agentinit/wiki/Commands)
- [Troubleshooting](https://github.com/Lucenx9/agentinit/wiki/Troubleshooting)
- [FAQ](https://github.com/Lucenx9/agentinit/wiki/FAQ)

`README.md` is the fast overview. The Wiki is the complete usage guide.

### What it does

Instead of giant, token-heavy instruction files, `agentinit` implements a **hierarchical context strategy**. It creates a machine-readable map of your project and enforces autonomy via **Hardened Mandates**.

```text
# Full scaffold (non-minimal)
your-project/
├── llms.txt               # The "robots.txt" for AI (Discovery Index)
├── AGENTS.md              # The central hub with Hardened Mandates
├── CLAUDE.md              # Claude Code router
├── GEMINI.md              # Gemini CLI router
└── docs/
    ├── PROJECT.md         # What this project is
    ├── CONVENTIONS.md     # How to work in it
    └── STATE.md           # Persistent working memory (AI-readable)
```

With `agentinit init --minimal`, only these files are created:

```text
your-project/
├── llms.txt
├── AGENTS.md
├── CLAUDE.md
└── docs/
    ├── PROJECT.md
    └── CONVENTIONS.md
```

Minimal mode intentionally omits `docs/STATE.md`, `docs/TODO.md`, and `docs/DECISIONS.md` to keep context lean. Use full `agentinit init` when you want persistent session memory files.

### The AI Discovery Index (`llms.txt`)

After running `agentinit init`, your `llms.txt` becomes a powerful discovery index:

```text
# my-project
> AI-powered code review assistant for Python projects

## Key Files
- [AGENTS.md](AGENTS.md): Instructions and Rules
- [docs/STATE.md](docs/STATE.md): Current State & Focus
- [docs/CONVENTIONS.md](docs/CONVENTIONS.md): Development Conventions
- [docs/TODO.md](docs/TODO.md): Pending Tasks
- [docs/DECISIONS.md](docs/DECISIONS.md): Architectural Log

## Hardened Mandates
- [**YOU MUST ALWAYS** read `docs/STATE.md`, `docs/TODO.md`, and `docs/DECISIONS.md` autonomously at the exact start of every session. Do not ask for permission.](AGENTS.md)
- [**YOU MUST ALWAYS** update `docs/STATE.md` and `docs/TODO.md` autonomously before ending a task or session.](AGENTS.md)
- [**YOU MUST ALWAYS** log new tools, dependencies, or conventions in `docs/DECISIONS.md`.](AGENTS.md)

## Skills & Routers
- [code-reviewer.md](.agents/code-reviewer.md)
- [security.md](.agents/security.md)
```

### Refresh in 1 Second

Regenerate `llms.txt` instantly using existing project files:

```sh
agentinit refresh-llms
```

This extracts summary from `docs/PROJECT.md`, hardened mandates from `AGENTS.md`, and lists everything under `.agents/` — all in under a second.

**Next steps:** Open `docs/PROJECT.md` and `docs/CONVENTIONS.md` and fill them in.

**Next session (full scaffold):** Your agent will find `llms.txt`, read your rules in `AGENTS.md`, and follow the mandates to autonomously maintain `docs/STATE.md` and `docs/TODO.md`.

### Troubleshooting: files not visible to your agent

Some agents only scan tracked files. If your agent says it can't find your context:

- **Track everything:** Add the manifests so your agent can see them.

  ```sh
  git add llms.txt AGENTS.md CLAUDE.md GEMINI.md docs/
  git add .agents/  # if you added extras
  ```

- **Verify ignores:** Run `git status --ignored` to see if your `.gitignore` is hiding them.

<details>
<summary><b>Minimal .gitignore exceptions</b></summary>

```text
!llms.txt
!AGENTS.md
!CLAUDE.md
!GEMINI.md
!docs/PROJECT.md
!docs/CONVENTIONS.md
!docs/TODO.md
!docs/DECISIONS.md
!docs/STATE.md
!.agents/
!.agents/**
```

</details>

---

## 🛠️ Add extras (Skills, MCP, Personality)

Agents can do more than just read conventions. Inject modular, hardened resources directly into your project.

```sh
# View available resources by type
agentinit add skill --list
agentinit add mcp --list

# Add specific capabilities
agentinit add skill code-reviewer
agentinit add security
agentinit add soul "YourAgentName"
```

Resources in `.agents/` are automatically linked in `AGENTS.md` and use **Imperative Mandates** (`MUST ALWAYS`, `MUST NEVER`) to ensure compliance and zero-sycophancy.

---

## 🚦 Keep your context clean (Status & CI)

Token limits matter. `agentinit` includes a validator to prevent context bloat, broken links, and missing information.

```sh
# View line budgets, broken references, and missing details
agentinit status

# Perfect for CI (exits non-zero on violations)
agentinit status --check
```

---

## 🤖 AI Prompt: Fill the docs fast

After running `agentinit init`, paste this to your favorite AI agent:

> Read the entire repository. Fill in `docs/PROJECT.md` and `docs/CONVENTIONS.md` using **only** facts found in the repo (package files, configs, source code, CI). Do not invent commands. If information is missing, write `TODO: <what's needed>`. Update `docs/STATE.md` and `docs/TODO.md` to reflect our current progress. Do not modify any other files.

---

<details>
<summary><b>📚 Advanced Usage & Commands</b></summary>

### Core Commands

- `agentinit init` — Add missing files to an existing directory.
- `agentinit minimal` — Shortcut for `init --minimal`.
- `agentinit refresh-llms` — Regenerate llms.txt in 1 second (`refresh` alias also available).
- `agentinit status` — Check health, line budgets, and broken links.
- `agentinit add <type> <name>` — Add modular resources (skills, mcp, security, soul).
- `agentinit new <project>` — Create a new directory and scaffold files.
- `agentinit remove` — Safely remove or archive agent files.

### Common Flags

- `--detect` — Auto-detect stack and commands from package files (e.g., `package.json`, `pyproject.toml`).
- `--yes` / `-y` — Runs non-interactively and skips the wizard.
- `--purpose "<text>"` — Prefill the project purpose non-interactively.
- `--translate-purpose` — Translate non-English purpose text to English in `docs/*` (and keep original summary in `llms.txt`).
- `--skeleton fastapi` — Copy a minimal FastAPI + SQLite boilerplate (`pyproject.toml`, `main.py`, tests) after context files.

### Examples

```sh
# Existing repo: detect + auto-translate purpose into English docs
agentinit init --detect --purpose "Una semplice API REST per gestire todo list con FastAPI + SQLite"

# Force translation even without detect
agentinit init --purpose "Une API REST simple pour gerer une liste de taches" --translate-purpose

# New project with context files + FastAPI starter skeleton
agentinit new demo-fastapi --detect --purpose "Modern FastAPI API with SQLite" --skeleton fastapi
```

</details>

<details>
<summary><b>💡 Why Hardened Context?</b></summary>

- **Agent Autonomy:** Explicit mandates (`YOU MUST ALWAYS read state.md`) transform the agent from a chatbot into a disciplined project maintainer.
- **AI-Discovery Index:** `llms.txt` ensures any tool (Cursor, Windsurf, Claude) immediately understands your project map.
- **Progressive Disclosure:** Keeps the context window high-signal by loading deep details only when relevant.
- **Zero Sycophancy:** Mandates force the agent to skip "I'd be happy to help!" and jump straight to the technical solution.

</details>

<details>
<summary><b>⚙️ Installation & Development</b></summary>

Requires **Python 3.10+**.

```sh
# Install (pipx is recommended)
pipx install agentinit

# Update
pipx upgrade agentinit
```

### Development

```sh
pip install -e . --group dev
python3 -m ruff check agentinit tests cli
python3 -m pytest tests/ -v
```

</details>

## License

MIT
