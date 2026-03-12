# Changelog

## Unreleased

## [0.3.14] - 2026-03-12

### Fixed

- Make `docs/PROJECT.md` environment updates idempotent when rerunning the interactive wizard.
- Refresh generated `llms.txt` during `agentinit init` even when the file already exists, while leaving custom `llms.txt` files untouched.


## [0.3.13] - 2026-03-06

### Added

- `agentinit doctor` command: runs all checks (missing files, TBD content, line budgets, sync drift, llms.txt freshness, contextlint) and prints actionable fix commands with a quick-fix summary.
- `agentinit sync --diff`: show unified diffs for out-of-sync router files; works standalone or combined with `--check`.

### Changed

- Rewrite README with expanded documentation: installation, quick start, full/minimal modes, how-it-works diagram, CI integration, modular resources, and supported tools table.
- Deduplicate test helpers: move shared `fill_tbd` to `tests/helpers.py`; add missing `detect`/`yes` defaults to `make_init_args`; add `make_doctor_args` and update `make_sync_args` with `diff` support.
- Fix misleading test file docstrings (all previously said "Tests for agentinit.cli").
- Add wiki documentation for architecture, commands, workflows, FAQ, troubleshooting, and contributing.

## [0.3.12] - 2026-03-06

### Changed

- Add `pytest-cov` to dev dependencies and configure coverage reporting in CI.
- Add `license-files` to `pyproject.toml` per PEP 639.
- Deduplicate scaffold argument definitions in parser via shared helper (~90 lines removed).
- Fix Italian comment in publish workflow.

## [0.3.11] - 2026-03-06

### Fixed

- CLI edge cases and contextlint filtering:
  - `agentinit new --force` now fails cleanly when the target already exists as a file;
  - `agentinit add mcp` / `add security` update the intended `AGENTS.md` section without matching headings inside fenced code blocks first;
  - `agentinit status --minimal --check` limits `contextlint` to the minimal core files instead of unrelated docs;
  - `contextlint` validates list-like config fields instead of treating strings as per-character iterables.

### Changed

- Refactor scaffold internals without changing CLI behavior:
  - extract scaffold and project-document update logic from `agentinit.cli` into focused internal modules;
  - keep `agentinit.cli` as a thin entrypoint with stable wrappers for existing tests and console scripts.
- Development docs now recommend creating a virtual environment before editable installs on systems that enforce PEP 668.

## [0.3.10] - 2026-03-05

### Fixed

- Harden starter skeleton copying:
  - skip transient cache directories, build artifacts, and `.egg-info` content when copying scaffold skeletons;
  - add regression coverage for filtered skeleton files.

## [0.3.9] - 2026-03-05

### Fixed

- Harden minimal-profile autodetection for `status --check` and `sync --check`.

### Changed

- Remove duplicate context warnings from shipped templates.

## [0.3.8] - 2026-03-05

### Fixed

- Harden managed-file handling for scaffold and refresh flows.

### Changed

- Verify and refresh template guidance against primary sources.
- Align root `CLAUDE.md` and `GEMINI.md` with the import-based router templates.
- Add shared minimal-profile detection helpers used by status and sync checks.

## [0.3.7] - 2026-03-05

### Changed

- Refactor the CLI into focused internal modules while preserving the public command surface.
- Split the test suite into targeted CLI/scaffold/status groups with shared helpers.
- Strengthen CI gates and refresh the README/development guidance.

## [0.3.6] - 2026-03-05

### Fixed

- Align `agentinit status --check` line-budget hard failures with `contextlint` semantics:
  - treat `.contextlintrc.json` as warning-only when oversized (no hard fail);
  - keep hard failures focused on always-hot router/rules files.
- Add regression coverage to ensure oversized `.contextlintrc.json` does not fail `status --check`.

### Changed

- Modernize FastAPI skeleton typing for Python `>=3.12`:
  - replace deprecated `typing.List` usage with built-in `list[...]`.

## [0.3.5] - 2026-03-03

### Added

- Optional purpose translation flow:
  - new `--translate-purpose` flag for `new`, `init`, and `minimal`;
  - auto-translate purpose to English for `docs/*` when `--detect` identifies Italian, Spanish, or French purpose text;
  - preserve original non-English purpose for `llms.txt` summary while using English title.
- Starter project scaffolding with `--skeleton fastapi`:
  - copies `pyproject.toml`, `main.py`, and basic tests (`tests/conftest.py`, `tests/test_todos.py`);
  - works after context scaffold in both `new` and `init` flows.

### Changed

- Improve purpose-based Python setup detection:
  - choose `uv sync` for `uv`/`uvicorn`/modern FastAPI wording;
  - choose `poetry install` when purpose mentions Poetry;
  - fallback to `pip install -e .`.
- Commands block marker now includes an explicit managed-note comment for detect/prompt updates.
- README updated with new flags and usage examples.

## [0.3.4] - 2026-03-03

### Changed

- Supercharge `llms.txt` generation:
  - automatic project summary now falls back to manifest detection (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`) when project context is missing/unfilled;
  - `## Key Files` keeps canonical links and profile-aware missing markers;
  - `## Hardened Mandates` now prioritizes the most critical `MUST ALWAYS` / `MUST NEVER` rules from `AGENTS.md`;
  - `## Skills & Routers` lists all `.agents/` resources with full relative links.
- Keep fast refresh UX: `agentinit refresh-llms` remains sub-second and tested.
- README update: explicitly documents that `llms.txt` now includes auto-summary and mandates.

## [0.3.3] - 2026-03-03

### Fixed

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

## [0.3.2] - 2026-03-01

### Added

- `llms.txt` standard to template and core managed files.
- Support `llms.txt` in all `init` and `new` commands (including minimal).

### Changed

- Adopt 2026 agentic best practices for templates and routing.
- Hardened agent mandates with imperative language (MUST/ALWAYS/NEVER).
- AI-optimized docs templates (STATE.md, TODO.md) with checkbox tasks and lessons learned.
- Update `repo-map` with explicit domain boundaries.

## [0.3.1] - 2026-03-01

### Added

- New `agentinit add` command for injecting resources (soul, skill, mcp, security) into existing projects.
- Alias `--yes` / `-y` for `init --force` (non-interactive mode).

### Changed

- README rewrite for clarity and progressive disclosure.

### Fixed

- Fix markdownlint errors in README and agent templates.

## [0.3.0] - 2026-03-01

### Added

- Vendor contextlint: new `agentinit lint` command for checking bloat, broken refs, and duplication.
- `agentinit status --check` now includes contextlint checks (hard errors fail CI).
- New templates: `.claude/rules/` (coding-style, testing, repo-map) and `.contextlintrc.json`.
- CI: `agentinit status --check` runs on all platforms (Linux, macOS, Windows).
- Tests: template packaging verification, lint JSON output, broken-ref detection via contextlint.

### Changed

- Templates ship without `TBD` — freshly scaffolded projects pass `status --check` out-of-the-box.

## [0.2.9] - 2026-03-01

### Fixed

- Fix README accuracy (drop rejected `--json`, add missing `--detect` flag).

## [0.2.0] - 2026-02-28

### Added

- Initial public release: scaffold, init, minimal, remove, status commands.
- Auto-detect stack from package.json, go.mod, Cargo.toml, pyproject.toml.
- Interactive wizard with `--prompt`, non-interactive with `--yes`.
- Router-first templates for Claude, Gemini, Copilot, and Cursor.
