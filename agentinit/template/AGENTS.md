# Agent Instructions

**Purpose:** (not configured)

> **🚨 CORE MANDATES:**
>
> - **YOU MUST ALWAYS** read `docs/STATE.md`, `docs/TODO.md`, and `docs/DECISIONS.md` autonomously at the start of every session.
> - **YOU MUST ALWAYS** update `docs/STATE.md` and `docs/TODO.md` before ending a task or session.
> - **YOU MUST ALWAYS** log new tools, dependencies, or conventions in `docs/DECISIONS.md`.

**Commands:**

- Canonical runnable commands live in `docs/PROJECT.md`.
- Keep Setup / Build / Test / Lint/Format / Run current there.

> If you introduce a tool or dependency, record it in `docs/DECISIONS.md` and update `docs/PROJECT.md` commands in the same PR.

**Non-obvious conventions / gotchas:**

- (not configured)

**When unsure:**

- Ask for clarification before risky or destructive changes.
- Prefer small, reversible edits.
- Read the linked files in `docs/` for deeper context.

**Context files (load when relevant):**

- `docs/PROJECT.md` — Scope, stack, layout, constraints.
- `docs/CONVENTIONS.md` — Style, naming, testing, git workflow.
- `docs/TODO.md` — Active work, plans, assumptions.
- `docs/DECISIONS.md` — Past architectural choices and rationale.
- `docs/STATE.md` — Current focus, next steps, blockers (session handoff).

**Token discipline:**

- Move long explanations, architecture notes, and deep dives to `docs/`.
- Prefer linking to other files over inline dumps.
