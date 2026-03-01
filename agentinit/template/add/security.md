# Security Guardrails

## Mandatory Rules

1. **Never commit secrets.** No API keys, tokens, passwords, or private keys in source code. Use environment variables or a secrets manager.
2. **Validate all external input.** Sanitize user input, API parameters, file paths, and environment variables at system boundaries.
3. **No dangerous shell commands.** Never run `rm -rf /`, `DROP TABLE`, or destructive operations without explicit user confirmation.
4. **Principle of least privilege.** Request minimum permissions. Don't use root/admin when unnecessary.
5. **Pin dependencies.** Use lock files. Review new dependencies for known CVEs before adding.

## Code Patterns to Reject

- `eval()`, `exec()`, `Function()` with user-controlled input
- String concatenation for SQL queries (use parameterized queries)
- `innerHTML` or `dangerouslySetInnerHTML` with unsanitized data
- Hardcoded credentials or connection strings
- `chmod 777` or world-writable permissions
- Disabled SSL/TLS verification (`verify=False`, `rejectUnauthorized: false`)

## Before Merging

- [ ] No secrets in diff (check with `git diff --cached | grep -iE '(password|secret|token|api_key|private_key)'`)
- [ ] New dependencies audited (`npm audit`, `pip audit`, `cargo audit`)
- [ ] Input validation at every system boundary
- [ ] Error messages don't leak internal details to users
- [ ] File operations use absolute paths or validated relative paths (no traversal)

## Incident Response

If you discover a committed secret:

1. Rotate the credential immediately
2. Remove from git history (`git filter-repo` or BFG)
3. Add the pattern to `.gitignore` and pre-commit hooks
