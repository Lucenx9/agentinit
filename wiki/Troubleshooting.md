# Troubleshooting

## Agent cannot find context files

AI agents typically only read files that are tracked in git.

```sh
# Check if files are tracked
git status

# Track the generated files
git add AGENTS.md CLAUDE.md GEMINI.md llms.txt docs/

# Check if files are gitignored
git status --ignored
```

If your `.gitignore` excludes any managed files, add explicit exceptions:

```gitignore
# Allow agent context files
!AGENTS.md
!CLAUDE.md
!GEMINI.md
!llms.txt
!docs/
```

## Router files are out of sync

If `agentinit sync --check` fails in CI:

```sh
# See what's different
agentinit sync --diff

# Regenerate routers
agentinit sync

# Commit the updated files
git add CLAUDE.md GEMINI.md .cursor/rules/project.mdc .github/copilot-instructions.md
git commit -m "Sync agent router files"
```

## Status check fails

If `agentinit status --check` fails:

```sh
# See the full report
agentinit status

# Run doctor for grouped fix suggestions
agentinit doctor
```

Common causes:

- **Missing files** -- Run `agentinit init` to regenerate them
- **Unfilled placeholders** -- Open `docs/PROJECT.md` and `docs/CONVENTIONS.md` and replace `(not configured)` with real values
- **Files over 300 lines** -- Move detailed content to separate files in `docs/` and use `@`-imports
- **Broken references** -- Check that files referenced in `AGENTS.md` actually exist

## Symlink warnings

agentinit skips managed file paths that resolve to symlinks pointing outside the project root. This is a security measure.

If you see "skipped: symlink" warnings:

- Replace the symlink with a regular file inside the repository
- Or remove the symlink and let agentinit create the file

## PEP 668 errors on Linux

On distro-managed Python installs (Debian, Ubuntu, Fedora), `pip install` may fail with an "externally managed environment" error.

**Fix:** Use `pipx` (recommended) or create a virtual environment:

```sh
# Option 1: pipx
pipx install agentinit

# Option 2: virtual environment
python3 -m venv .venv
. .venv/bin/activate
pip install agentinit
```

## `--detect` doesn't find my stack

`--detect` reads specific manifest files:

- `pyproject.toml` (Python)
- `package.json` (Node.js)
- `Cargo.toml` (Rust)
- `go.mod` (Go)

If your manifest file isn't in the project root, `--detect` won't find it. In that case, fill in `docs/PROJECT.md` manually.

## llms.txt shows wrong project name

`agentinit refresh-llms` detects the project name in this order:

1. `name` field in `pyproject.toml`
2. `name` field in `package.json`
3. Purpose text in `docs/PROJECT.md`
4. Directory name

If the wrong name appears, check your manifest files or set the Purpose field in `docs/PROJECT.md`.
