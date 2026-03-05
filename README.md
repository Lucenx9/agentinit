# agentinit

![CI](https://github.com/Lucenx9/agentinit/actions/workflows/ci.yml/badge.svg) [![PyPI](https://img.shields.io/pypi/v/agentinit.svg)](https://pypi.org/project/agentinit/) [![Python Versions](https://img.shields.io/pypi/pyversions/agentinit.svg)](https://pypi.org/project/agentinit/)

<img src="https://raw.githubusercontent.com/Lucenx9/agentinit/main/assets/preview.png" width="900" alt="agentinit preview" />

Scaffold and maintain **agent context files** for modern coding assistants, with a deterministic, standard-library-only CLI.

`agentinit` creates a clean router-first setup around `AGENTS.md`, plus companion files for Claude, Cursor, Copilot, Gemini CLI, and `llms.txt`.

## Why agentinit 🎯

- **Single source of truth:** keep high-level rules in `AGENTS.md`.
- **Low drift workflow:** regenerate and verify router files with `sync --check`.
- **Lean context model:** keep short entry files and push detail into `docs/`.
- **No runtime dependencies:** pure Python stdlib.

## Quick Start 🚀

Requires **Python 3.10+**.

```sh
# Install (recommended)
pipx install agentinit

# Initialize in an existing repository
cd your-project
agentinit init --minimal
```

Minimal profile generates:

```text
your-project/
├── llms.txt
├── AGENTS.md
├── CLAUDE.md
└── docs/
    ├── PROJECT.md
    └── CONVENTIONS.md
```

Full profile (`agentinit init`) also includes `GEMINI.md`, `docs/STATE.md`, `docs/TODO.md`, `docs/DECISIONS.md`, Cursor/Copilot/Claude rule files, and `.contextlintrc.json`.

## Core Workflow 🧭

```sh
# 1) Bootstrap context files
agentinit init --detect --purpose "AI code review assistant"

# 2) Keep llms.txt aligned with project docs
agentinit refresh-llms

# 3) Add modular resources
agentinit add skill code-reviewer
agentinit add mcp github
agentinit add security

# 4) Validate quality gates
agentinit status --check
agentinit sync --check
agentinit lint
```

For minimal projects, both `status --check` and `sync --check` auto-detect the generated minimal profile. `status --minimal --check` and `sync --minimal --check` remain available if you want to force that mode explicitly.

### Command Reference

- `agentinit init` add missing context files in current directory
- `agentinit minimal` shortcut for `init --minimal`
- `agentinit new <project>` create a new project and scaffold context
- `agentinit refresh-llms` (alias: `refresh`) regenerate `llms.txt`
- `agentinit sync` reconcile router files from templates
- `agentinit status` show missing/incomplete files and line budgets
- `agentinit lint` run `contextlint` checks
- `agentinit add <type> <name>` install resources (`skill`, `mcp`, `security`, `soul`)
- `agentinit remove` remove or archive managed files

## CI Example ✅

Use both structure and drift checks:

```sh
agentinit sync --check
agentinit status --check
agentinit lint
```

## Tool Compatibility 🤝

`agentinit` is designed to work with common agentic workflows by generating:

- `AGENTS.md` as primary router
- `CLAUDE.md` for Claude Code memory/routing
- `.cursor/rules/project.mdc` for Cursor rule routing
- `.github/copilot-instructions.md` for GitHub Copilot context
- `GEMINI.md` for Gemini CLI context routing
- `llms.txt` as project discovery index

## Troubleshooting 🛠️

If your agent cannot find context files:

- track files in git (`git add AGENTS.md CLAUDE.md GEMINI.md llms.txt docs/`)
- verify ignored files (`git status --ignored`)
- regenerate derived files (`agentinit refresh-llms` and `agentinit sync`)
- replace managed symlinks with regular files inside the repo; unsafe managed paths are skipped by design

## Documentation 📚

Wiki (full usage and examples):

- [Wiki Home](https://github.com/Lucenx9/agentinit/wiki)
- [Quick Start](https://github.com/Lucenx9/agentinit/wiki/Quick-Start)
- [Commands](https://github.com/Lucenx9/agentinit/wiki/Commands)
- [Workflows](https://github.com/Lucenx9/agentinit/wiki/Workflows)
- [Troubleshooting](https://github.com/Lucenx9/agentinit/wiki/Troubleshooting)
- [FAQ](https://github.com/Lucenx9/agentinit/wiki/FAQ)
- [Contributing to the Wiki](https://github.com/Lucenx9/agentinit/wiki/Contributing-to-the-Wiki)

## Development 🧪

```sh
pip install -e . --group dev
python3 -m ruff check agentinit tests cli
python3 -m ruff format --check agentinit tests cli
python3 -m pytest tests/ -v
```

## License

MIT
