# Changelog

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
