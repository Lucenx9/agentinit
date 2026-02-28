# Decisions Template

Use one ADR-lite entry per durable decision.

## Entry Format

- Date: YYYY-MM-DD
- Decision: Short statement
- Rationale: Why this choice was made
- Alternatives: Options considered and why they were not selected

## Entries

### 2026-02-27

- Date: 2026-02-27
- Decision: Use AGENTS.md as the primary router and source of truth.
- Rationale: Centralizes guidance and prevents duplication across agent-specific files.
- Alternatives: Per-agent full instructions; rejected due to drift risk and maintenance overhead.

### 2026-02-28

- Date: 2026-02-28
- Decision: Add an opt-in `--minimal` scaffolding mode for `init` and `new`.
- Rationale: Some projects want lower token usage and only need core router/context files.
- Alternatives: Keep full scaffold only; rejected because it forces extra files users do not always need.
