# Claude Router

**Token Discipline:** Keep this file short. Move details to `docs/`.

@AGENTS.md
@docs/PROJECT.md
@docs/CONVENTIONS.md
@docs/TODO.md
@docs/DECISIONS.md
@docs/STATE.md
@.claude/rules/coding-style.md
@.claude/rules/testing.md
@.claude/rules/repo-map.md

Treat `AGENTS.md` as the single source of truth for all mandatory rules (`MUST ALWAYS` / `MUST NEVER`).

**Startup:** If `docs/PROJECT.md` or `docs/CONVENTIONS.md` contain unfilled placeholders, fill them concisely (facts-only) before starting other work.

**Maintenance:** If you introduce or change commands, conventions, or decisions, update the corresponding docs in the same PR. Update `docs/STATE.md` only if priorities/next steps changed.

Do not duplicate policy text here. Use this file purely as an index to the deeper context in `docs/`.
