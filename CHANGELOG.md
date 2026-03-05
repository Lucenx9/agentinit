# Changelog

## 0.3.6

- Align `agentinit status --check` line-budget hard failures with `contextlint` semantics:
  - treat `.contextlintrc.json` as warning-only when oversized (no hard fail);
  - keep hard failures focused on always-hot router/rules files.
- Add regression coverage to ensure oversized `.contextlintrc.json` does not fail `status --check`.
- Modernize FastAPI skeleton typing for Python `>=3.12`:
  - replace deprecated `typing.List` usage with built-in `list[...]`.

## 0.3.5

- Add optional purpose translation flow:
  - new `--translate-purpose` flag for `new`, `init`, and `minimal`;
  - auto-translate purpose to English for `docs/*` when `--detect` identifies Italian, Spanish, or French purpose text;
  - preserve original non-English purpose for `llms.txt` summary while using English title.
- Improve purpose-based Python setup detection:
  - choose `uv sync` for `uv`/`uvicorn`/modern FastAPI wording;
  - choose `poetry install` when purpose mentions Poetry;
  - fallback to `pip install -e .`.
- Add starter project scaffolding with `--skeleton fastapi`:
  - copies `pyproject.toml`, `main.py`, and basic tests (`tests/conftest.py`, `tests/test_todos.py`);
  - works after context scaffold in both `new` and `init` flows.
- Commands block marker now includes an explicit managed-note comment for detect/prompt updates.
- README updated with new flags and usage examples.

## 0.3.4

- Supercharge `llms.txt` generation:
  - automatic project summary now falls back to manifest detection (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`) when project context is missing/unfilled;
  - `## Key Files` keeps canonical links and profile-aware missing markers;
  - `## Hardened Mandates` now prioritizes the most critical `MUST ALWAYS` / `MUST NEVER` rules from `AGENTS.md`;
  - `## Skills & Routers` lists all `.agents/` resources with full relative links.
- Keep fast refresh UX: `agentinit refresh-llms` remains sub-second and tested.
- README update: explicitly documents that `llms.txt` now includes auto-summary and mandates.

## 0.3.3

- Harden `agentinit add` path handling:
  - reject unknown/traversal-like resource names early;
  - enforce source/destination path containment;
  - skip symlink destinations safely.
- Make `contextlint` config parsing resilient to invalid numeric values (fallback to defaults instead of crashing).
- Prevent duplicate `Safe Defaults` insertion when rerunning the interactive wizard.
- Avoid orphan project directories on `agentinit new` when templates are empty/corrupt.
- README alignment fixes:
  - correct `agentinit add --list` usage;
  - clarify minimal vs full scaffold behavior;
  - narrow Windsurf claim to discovery routing via `llms.txt`.

## 0.3.2

- Adopt 2026 agentic best practices for templates and routing.
- Add `llms.txt` standard to template and core managed files.
- Hardened agent mandates with imperative language (MUST/ALWAYS/NEVER).
- AI-optimized docs templates (STATE.md, TODO.md) with checkbox tasks and lessons learned.
- Update `repo-map` with explicit domain boundaries.
- Support `llms.txt` in all `init` and `new` commands (including minimal).

## 0.3.1

- New `agentinit add` command for injecting resources (soul, skill, mcp, security) into existing projects.
- Alias `--yes` / `-y` for `init --force` (non-interactive mode).
- README rewrite for clarity and progressive disclosure.
- Fix markdownlint errors in README and agent templates.

## 0.3.0

- Vendor contextlint: new `agentinit lint` command for checking bloat, broken refs, and duplication.
- `agentinit status --check` now includes contextlint checks (hard errors fail CI).
- New templates: `.claude/rules/` (coding-style, testing, repo-map) and `.contextlintrc.json`.
- Templates ship without `TBD` — freshly scaffolded projects pass `status --check` out-of-the-box.
- CI: `agentinit status --check` runs on all platforms (Linux, macOS, Windows).
- Tests: template packaging verification, lint JSON output, broken-ref detection via contextlint.

## 0.2.9

- Fix README accuracy (drop rejected `--json`, add missing `--detect` flag).

## 0.2.0

- Initial public release: scaffold, init, minimal, remove, status commands.
- Auto-detect stack from package.json, go.mod, Cargo.toml, pyproject.toml.
- Interactive wizard with `--prompt`, non-interactive with `--yes`.
- Router-first templates for Claude, Gemini, Copilot, and Cursor.
