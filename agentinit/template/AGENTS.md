# Agent Instructions (AGENTS.md)

**Purpose:** Primary entry point for coding agents to understand the project structure and rules.

> **🚨 CORE MANDATES:**
>
> - **YOU MUST ALWAYS** read `docs/STATE.md`, `docs/TODO.md`, and `docs/DECISIONS.md` autonomously at the exact start of every session. Do not ask for permission.
> - **YOU MUST ALWAYS** update `docs/STATE.md` and `docs/TODO.md` autonomously before ending a task or session.
> - **YOU MUST ALWAYS** log new tools, dependencies, or conventions in `docs/DECISIONS.md`.

**Non-obvious conventions / landmines:**

- (Add project-specific warnings, anti-patterns, or strict rules here)
- ...

**Commands:**

- Canonical runnable commands live in `docs/PROJECT.md`.
- Keep Setup / Build / Test / Lint/Format / Run current there.

> If you introduce a tool or dependency (pytest, ruff, etc.), record it in `docs/DECISIONS.md` and update `docs/PROJECT.md` commands in the same PR.

**When unsure:**

- Ask for clarification / confirm assumptions before risky changes.
- Read the linked files in `docs/` for deeper context.

**Language:** You may chat in any language, but keep `docs/*` in English.

**Fallback:** If you're unsure what to do next, open `docs/STATE.md` first.

**Context files (load when relevant):**

- `docs/PROJECT.md` — Scope, stack, layout, constraints.
- `docs/CONVENTIONS.md` — Style, naming, testing, git workflow.
- `docs/TODO.md` — Active work, plans, assumptions.
- `docs/DECISIONS.md` — Past architectural choices and rationale.
- `docs/STATE.md` — Current focus, next steps, blockers (session handoff).
- `.claude/rules/` — Modular coding rules (style, testing, repo layout).

**Token discipline:**

- Keep this `AGENTS.md` file short (~60–120 lines).
- Move long explanations, architecture notes, and deep dives to `docs/`.
- Prefer linking to other files over inline dumps.
- Don't repeatedly re-read these files unless they changed.
