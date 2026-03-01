---
name: code-reviewer
description: This skill should be used when the user wants to "review code", "check this PR", "review my changes", "do a code review", or needs a thorough analysis of code quality, security, performance, and maintainability. Also use when the user asks to "find bugs", "check for issues", or "audit this code".
---

# Code Reviewer

Perform a deep code review on the staged or specified changes. Follow the checklist below systematically.

## Review Checklist

### Correctness

- Logic errors, off-by-one, null/undefined handling
- Edge cases: empty inputs, large inputs, concurrent access
- Error handling: are failures caught and reported clearly?

### Security

- No hardcoded secrets, tokens, or credentials
- Input validation at system boundaries (user input, API params)
- No SQL injection, XSS, command injection, or path traversal
- Dependencies: any known CVEs?

### Performance

- No N+1 queries or unbounded loops
- Large allocations or copies that could be avoided
- Missing indexes on queried fields

### Maintainability

- Functions under 40 lines, single responsibility
- Clear naming with no ambiguous abbreviations
- Tests cover the new behavior

## Output Format

For each finding, report:

```
[severity] file:line — description
  Suggestion: ...
```

Severities: `CRITICAL` | `WARNING` | `NIT`

Summarize with counts: X critical, Y warnings, Z nits.
If no issues found, respond with "LGTM — no issues found."
