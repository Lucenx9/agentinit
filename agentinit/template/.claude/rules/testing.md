# Testing

- Write tests for new functionality and bug fixes.
- Test behavior, not implementation details.
- Keep tests independent — no shared mutable state between test cases.
- Use descriptive test names that explain the scenario and expected outcome.
- Prefer fast, focused unit tests; use integration tests sparingly.
- Run the full test suite before opening a pull request.
- Do not skip or disable failing tests without documenting why.
- Mock external services and I/O at the boundary, not deep inside the code.
