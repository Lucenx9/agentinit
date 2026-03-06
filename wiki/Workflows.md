# Workflows

## CI pipeline

Add agentinit checks to your CI to prevent documentation drift.

### GitHub Actions

```yaml
name: Agent Context
on: [push, pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install agentinit
      - name: Check router sync
        run: agentinit sync --check
      - name: Check file completeness
        run: agentinit status --check
      - name: Lint context files
        run: agentinit lint
```

### What each check does

| Command | Catches |
|---------|---------|
| `sync --check` | Router files that have drifted from their templates |
| `status --check` | Missing files, unfilled placeholders, files over 300 lines, broken `@`-references |
| `lint` | Broken refs, content bloat, duplicated blocks across files |

All three commands exit with code 0 on success and code 1 on failure.

## Keeping files in sync

After editing `AGENTS.md` or `docs/` files:

```sh
# Regenerate router files
agentinit sync

# Regenerate llms.txt
agentinit refresh-llms
```

Run `agentinit doctor` to check everything at once and see grouped fix suggestions.

## Adding resources over time

As your project grows, add modular resources:

```sh
# Add a code review skill
agentinit add skill code-reviewer

# Add GitHub MCP integration guide
agentinit add mcp github

# Add security guardrails
agentinit add security
```

Each command copies the resource file and appends a reference in `AGENTS.md`.

## Team onboarding

When a new team member clones the repository, the context files are already in git. Their AI coding agent reads `AGENTS.md` (or the vendor-specific router) and follows the project rules immediately.

If context files were not tracked:

```sh
# Regenerate everything
agentinit init

# Or just the routers
agentinit sync
```

## Removing agentinit

To remove all managed files:

```sh
# Preview what will be deleted
agentinit remove --dry-run

# Archive instead of deleting
agentinit remove --archive

# Delete immediately
agentinit remove --force
```

Non-managed files are never touched. Empty directories (`docs/`, `.cursor/rules/`, etc.) are cleaned up after removal.

## Profile migration

To upgrade from minimal to full profile:

```sh
# Re-run init without --minimal to add the remaining files
agentinit init
```

This adds the missing full-profile files without overwriting existing ones.
