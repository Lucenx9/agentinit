# MCP: GitHub Integration

## Setup

GitHub maintains an official MCP server in `github/github-mcp-server`.
For Claude Code, this template uses PAT-based setup because GitHub documents it as the portable path across MCP hosts when OAuth support varies by host.

**Option A — Remote HTTP server:**

```bash
claude mcp add-json github '{"type":"http","url":"https://api.githubcopilot.com/mcp/","headers":{"Authorization":"Bearer YOUR_GITHUB_PAT"}}'
```

**Option B — Local Docker server:**

```bash
claude mcp add github \
  -e GITHUB_PERSONAL_ACCESS_TOKEN=YOUR_GITHUB_PAT \
  -- docker run -i --rm \
  -e GITHUB_PERSONAL_ACCESS_TOKEN \
  ghcr.io/github/github-mcp-server
```

## Available Operations

Once connected, you can:

- **Issues:** Create, list, search, update, and comment on issues
- **Pull Requests:** Create PRs, review diffs, add comments, merge
- **Repositories:** Search repos, get file contents, list branches
- **Search:** Search code, issues, and PRs across repositories

## Usage Examples

- "Create an issue titled 'Fix login bug' with label 'bug'"
- "List open PRs that need review"
- "Search for TODO comments across the repo"
- "Get the diff for PR #42"

## Security Notes

- Use a fine-grained personal access token with minimum required permissions
- Never commit the token — use environment variables or a secrets manager
- GitHub token permissions should match the operations you actually need (read-only unless writes are required)
- If you target GitHub Enterprise Server, verify the supported host and auth settings in the server docs before rollout
