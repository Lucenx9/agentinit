# agentinit

![CI](https://github.com/Lucenx9/agentinit/actions/workflows/ci.yml/badge.svg) [![PyPI](https://img.shields.io/pypi/v/agentinit.svg)](https://pypi.org/project/agentinit/) [![Python Versions](https://img.shields.io/pypi/pyversions/agentinit.svg)](https://pypi.org/project/agentinit/)

<img src="https://raw.githubusercontent.com/Lucenx9/agentinit/main/assets/preview.png" width="900" alt="agentinit preview" />

Scaffold **hardened, router-first** context files so your AI coding agents stop guessing and start delivering.

Pure Python standard library. No runtime dependencies. Generates 2026-ready manifests for **Claude Code**, **Cursor**, **Copilot**, **Gemini CLI**, and **Windsurf**.

## 🚀 Start in 60 seconds

```sh
# 1. Install via pipx (recommended)
pipx install agentinit

# 2. Initialize hardened context in your project
cd your-project
agentinit init --minimal
```

### What it does

Instead of giant, token-heavy instruction files, `agentinit` implements a **hierarchical context strategy**. It creates a machine-readable map of your project and enforces autonomy via **Hardened Mandates**.

```text
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

**Next steps:** Open `docs/PROJECT.md` and `docs/CONVENTIONS.md` and fill them in.

**Next session:** Your agent will find `llms.txt`, read your rules in `AGENTS.md`, and follow the mandates to autonomously maintain `docs/STATE.md` and `docs/TODO.md`.

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
# View available resources
agentinit add --list

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
- `agentinit status` — Check health, line budgets, and broken links.
- `agentinit add <type> <name>` — Add modular resources (skills, mcp, security, soul).
- `agentinit new <project>` — Create a new directory and scaffold files.
- `agentinit remove` — Safely remove or archive agent files.

### Common Flags

- `--detect` — Auto-detect stack and commands from package files (e.g., `package.json`, `pyproject.toml`).
- `--yes` / `-y` — Runs non-interactively and skips the wizard.
- `--purpose "<text>"` — Prefill the project purpose non-interactively.

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
python3 -m pytest tests/ -v
```

</details>

## License

MIT
