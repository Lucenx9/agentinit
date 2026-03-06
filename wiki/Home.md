# agentinit Wiki

**agentinit** scaffolds and maintains context files for AI coding agents. It generates a structured set of files that Claude Code, Cursor, GitHub Copilot, and Gemini CLI read automatically, using a router-first architecture centered on `AGENTS.md`.

For installation and a quick overview, see the [README](https://github.com/Lucenx9/agentinit#readme).

## Pages

- **[Quick Start](Quick-Start.md)** -- Step-by-step setup for new and existing projects
- **[Commands](Commands.md)** -- Full reference for every command and flag
- **[Architecture](Architecture.md)** -- Router-first design, profiles, templates, and generated files
- **[Workflows](Workflows.md)** -- CI integration, team workflows, and maintenance patterns
- **[Troubleshooting](Troubleshooting.md)** -- Common problems and solutions
- **[FAQ](FAQ.md)** -- Frequently asked questions
- **[Contributing](Contributing.md)** -- Development setup, testing, and how to contribute

## Key concepts

| Concept | Meaning |
| --- | --- |
| **Router file** | A thin vendor-specific file (e.g. `CLAUDE.md`) that imports `AGENTS.md` via `@`-references |
| **Source of truth** | `AGENTS.md` -- the single file where you define project rules |
| **Profile** | Either `minimal` (5 files) or `full` (16+ files); controls what gets generated |
| **Managed file** | A file created and maintained by agentinit; safe to regenerate |
| **Context file** | Any file that provides instructions or context to an AI coding agent |
| **Sync** | Regenerating router files from templates to match the current `AGENTS.md` |
| **Drift** | When a managed router file no longer matches its template |
