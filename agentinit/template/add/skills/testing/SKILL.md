---
name: testing
description: This skill should be used when the user wants to "write tests", "add test coverage", "generate tests", "improve tests", or needs help creating unit tests, integration tests, or test fixtures. Also use when the user says "test this function", "cover edge cases", or "add missing tests".
---

# Testing

You **MUST** analyze the specified code and generate or improve tests. You **MUST ALWAYS** follow existing project patterns for test framework, naming, and file structure.

## Approach

1. **Identify testable behavior** — public API, edge cases, error paths
2. **Follow existing patterns** — match the project's test framework, naming, and structure
3. **Write focused tests** — one assertion per test when practical

## Test Categories

### Unit Tests (default)

- Test pure functions and isolated modules
- Mock external dependencies at the boundary
- Cover: happy path, edge cases, error cases

### Integration Tests (when requested)

- Test module interactions and API endpoints
- Use realistic fixtures, not trivial data
- Clean up side effects (DB, files, env vars)

## Rules (YOU MUST NEVER VIOLATE THESE)

- **Naming:** `test_<behavior>_<scenario>` (e.g., `test_login_rejects_expired_token`)
- **YOU MUST NEVER** introduce shared mutable state between tests.
- **YOU MUST NEVER** use sleep/polling — use deterministic waits or mocks.
- **Assert behavior, not implementation** — avoid testing private methods.
- **Keep tests fast** — unit tests under 100ms each.

## Output

- Place tests next to source or in `tests/` following project convention.
- Include a brief comment explaining non-obvious test setups.
- You **MUST** run the test suite and report results after writing the tests.
