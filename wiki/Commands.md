# Commands

Full reference for every agentinit command and flag.

Run `agentinit --help` or `agentinit <command> --help` for built-in usage.

## `init`

Add missing context files to the current directory. Existing files are preserved unless `--force` is used.

```sh
agentinit init [flags]
```

| Flag | Effect |
|------|--------|
| `--minimal` | Generate only `AGENTS.md`, `CLAUDE.md`, `llms.txt`, `docs/PROJECT.md`, `docs/CONVENTIONS.md` |
| `--detect` | Auto-detect stack and commands from manifest files (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`) |
| `--purpose "..."` | Pre-fill the Purpose field in `AGENTS.md` and `docs/PROJECT.md` |
| `--prompt` | Run the interactive setup wizard (default when on a TTY) |
| `--translate-purpose` | Translate non-English purpose text (Italian, Spanish, French) to English for `docs/` files |
| `--skeleton fastapi` | Copy starter project boilerplate after scaffolding context files |
| `--force` | Overwrite existing agentinit-managed files |
| `--yes` / `-y` | Alias for `--force`; skip all confirmation prompts |

## `minimal`

Shortcut for `init --minimal`. Accepts all the same flags as `init`.

```sh
agentinit minimal [flags]
```

## `new`

Create a new project directory and scaffold context files inside it.

```sh
agentinit new <name> [flags]
```

| Flag | Effect |
|------|--------|
| `--dir <path>` | Parent directory for the new project (default: current directory) |

All `init` flags (`--minimal`, `--detect`, `--purpose`, `--prompt`, `--skeleton`, `--force`, `--yes`) also apply.

## `remove`

Remove agentinit-managed files from the current directory. Non-managed files are never touched.

```sh
agentinit remove [flags]
```

| Flag | Effect |
|------|--------|
| `--dry-run` | Print what would be deleted without changing anything |
| `--archive` | Move files to `.agentinit-archive/<timestamp>/` instead of deleting |
| `--force` | Skip the confirmation prompt |

Empty parent directories (`docs/`, `.cursor/rules/`, `.claude/rules/`) are cleaned up after removal.

## `sync`

Regenerate vendor router files (`CLAUDE.md`, `GEMINI.md`, `.cursor/rules/project.mdc`, `.github/copilot-instructions.md`) from their templates. Only updates files that have drifted.

```sh
agentinit sync [flags]
```

| Flag | Effect |
|------|--------|
| `--check` | Exit with code 1 if any router file is out of sync (CI mode) |
| `--diff` | Show a unified diff for each out-of-sync file |
| `--minimal` | Sync only the minimal router set (`CLAUDE.md` only) |
| `--root <path>` | Project root directory (default: current directory) |

For minimal-profile projects, `sync` auto-detects the profile. Use `--minimal` to force it.

## `status`

Show which context files are present, missing, incomplete, or exceeding line budgets. Also runs contextlint checks.

```sh
agentinit status [flags]
```

| Flag | Effect |
|------|--------|
| `--check` | Exit with code 1 if any issues are found (CI mode) |
| `--minimal` | Check only the minimal file set |

Status checks include:
- Missing managed files
- Files still containing `(not configured)` placeholders
- Files exceeding the 300-line hard limit or 200-line warning threshold
- Broken `@`-references in `AGENTS.md`
- contextlint violations (broken refs, bloat, duplication)

## `doctor`

Run all available checks (status, sync drift, llms.txt freshness, contextlint) and print grouped fix suggestions.

```sh
agentinit doctor [flags]
```

| Flag | Effect |
|------|--------|
| `--minimal` | Check only the minimal file set |

## `refresh-llms`

Regenerate `llms.txt` from current project files. Alias: `refresh`.

```sh
agentinit refresh-llms [--root <path>]
```

The generated `llms.txt` includes:
- Project name (detected from `pyproject.toml`, `package.json`, or directory name)
- Project summary (from `docs/PROJECT.md` Purpose field)
- Key context files with relative links
- Hardened mandates extracted from `AGENTS.md`
- References to installed resources in `.agents/`

## `lint`

Run contextlint checks on agent context files.

```sh
agentinit lint [flags]
```

| Flag | Effect |
|------|--------|
| `--config <path>` | Path to `.contextlintrc.json` config file |
| `--format text\|json` | Output format (default: `text`) |
| `--no-dup` | Disable duplicate-block detection |
| `--root <path>` | Repository root to lint (default: current directory) |

## `add`

Install modular resources into the current project.

```sh
agentinit add <type> <name> [flags]
agentinit add <type> --list
```

| Type | Available resources | Install location |
|------|-------------------|-----------------|
| `skill` | `code-reviewer`, `testing`, `frontend-reviewer` | `.agents/skills/<name>/` or `.claude/skills/<name>/` |
| `mcp` | `github`, `postgres` | `.agents/mcp-<name>.md` |
| `security` | *(no name needed)* | `.agents/security.md` |
| `soul` | *(no name needed)* | `.agents/soul.md` |

| Flag | Effect |
|------|--------|
| `--list` | List available resources for the given type |
| `--force` | Overwrite if the resource already exists |

Each `add` command appends a reference line to the appropriate section in `AGENTS.md`.
