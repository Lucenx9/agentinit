---
name: frontend-reviewer
description: This skill should be used when the user wants to "review frontend code", "check my React component", "review this UI", "audit accessibility", or needs a frontend-specific code review covering accessibility, performance, and UX patterns. Also use for "check a11y", "review styles", or "review this page".
---

# Frontend Reviewer

Perform a frontend-specific code review on UI components and pages. Cover accessibility, performance, and UX patterns.

## Review Checklist

### Accessibility (a11y)

- Interactive elements have accessible names (aria-label, visible text)
- Images have meaningful alt text (or alt="" for decorative)
- Color contrast meets WCAG AA (4.5:1 for text)
- Keyboard navigation works — no mouse-only interactions
- Focus management on route changes and modals

### Performance

- No unnecessary re-renders (missing memo, unstable references in deps)
- Images are lazy-loaded and properly sized
- Bundle impact: new dependencies justified and tree-shakeable?
- No layout shifts (explicit width/height on media)

### UX Patterns

- Loading states for async operations
- Error states with actionable messages
- Empty states for lists and search results
- Optimistic updates where appropriate

### Code Quality

- Components under 150 lines; extract sub-components if larger
- Business logic separated from presentation
- Styles scoped or using project convention (modules, Tailwind, etc.)
- No inline styles unless truly dynamic

## Output Format

```text
[severity] file:line — description
  Suggestion: ...
```

Severities: `CRITICAL` | `WARNING` | `NIT`

Summarize with counts: X critical, Y warnings, Z nits.
