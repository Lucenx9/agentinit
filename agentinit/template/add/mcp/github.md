# MCP: GitHub Integration

## Setup

Add GitHub's official MCP server to Claude Code:

**Option A — Remote HTTP server (recommended, Claude Code 2.1.1+):**

```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
```

Then authenticate via `/mcp` inside Claude Code (OAuth flow in browser).

**Option B — Remote with Personal Access Token:**

```bash
claude mcp add-json github '{"type":"http","url":"https://api.githubcopilot.com/mcp","headers":{"Authorization":"Bearer YOUR_GITHUB_PAT"}}'
```

**Option C — Local Docker server:**

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
- Recommended scopes: `repo`, `read:org` (add write scopes only if needed)
- For GitHub Enterprise: set `GITHUB_HOST=https://your-domain.com`
