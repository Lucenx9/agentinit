# Agent Router

This repository standardizes context/memory files for coding agents.
AGENTS.md is the source of truth; avoid copying policy text into other router files.

Context files (load when relevant to the task):

- docs/PROJECT.md — scope, stack, layout, constraints
- docs/CONVENTIONS.md — style, naming, testing, git workflow
- docs/TODO.md — active work, plans, assumptions
- docs/DECISIONS.md — past architectural choices and rationale

Commands (TBD):

- Setup: TBD
- Build: TBD
- Test: TBD
- Lint/Format: TBD
- Run: TBD

Rules:

1. Read the relevant docs/* file before making changes in that area.
2. Log active plans and assumptions in docs/TODO.md.
3. Record durable choices in docs/DECISIONS.md.
4. Update docs/PROJECT.md when scope, stack, or layout changes.
5. If something is missing, update docs/* instead of adding text here.
