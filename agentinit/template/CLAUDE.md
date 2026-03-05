# Claude Router

**Token Discipline:** Keep this file short. Prefer `@...` imports over pasted policy text.

@AGENTS.md
@docs/PROJECT.md
@docs/CONVENTIONS.md
@docs/TODO.md
@docs/DECISIONS.md
@docs/STATE.md
@.claude/rules/coding-style.md
@.claude/rules/testing.md
@.claude/rules/repo-map.md

Treat `AGENTS.md` as the single source of truth for mandatory rules and use the imported docs as working memory.

**Startup:** If `docs/PROJECT.md` or `docs/CONVENTIONS.md` still contain placeholders, replace them with concise factual content before other work.

**Maintenance:** Keep doc updates in the same PR as code changes. Touch `docs/STATE.md` only when priorities or handoff notes changed.

Do not duplicate policy text here. Use this file purely as an index to the deeper context in `docs/`.
