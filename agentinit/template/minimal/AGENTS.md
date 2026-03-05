# Agent Instructions (AGENTS.md)

**Purpose:** Primary entry point for coding agents in minimal mode.

> **🚨 CORE MANDATES:**
>
> - **YOU MUST ALWAYS** read `docs/PROJECT.md` and `docs/CONVENTIONS.md` at the start of every session.
> - **YOU MUST ALWAYS** keep commands and conventions aligned across `AGENTS.md`, `docs/PROJECT.md`, and `docs/CONVENTIONS.md`.
> - **YOU MUST NEVER** invent stack details. If unknown, mark as `(not configured)` until confirmed.

**Commands:**

- Canonical runnable commands live in `docs/PROJECT.md`.
- Keep Setup / Build / Test / Lint/Format / Run current there.

**When unsure:**

- Ask for clarification before risky or destructive changes.
- Prefer small, reversible edits.

**Context files (minimal profile):**

- `docs/PROJECT.md` — Scope, stack, layout, constraints.
- `docs/CONVENTIONS.md` — Style, naming, testing, git workflow.
- `llms.txt` — Discovery index for AI tools.

**Token discipline:**

- Keep this file short.
- Move project details to `docs/`.
