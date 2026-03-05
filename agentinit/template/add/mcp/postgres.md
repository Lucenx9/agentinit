# MCP: PostgreSQL Integration

## Setup

Add a PostgreSQL MCP server to Claude Code:

Store the DSN in an environment variable instead of embedding credentials in shell history:

```bash
export DATABASE_URL="postgresql://readonly:pass@localhost:5432/mydb"
```

**Option A — Third-party server example (Bytebase DBHub):**

```bash
claude mcp add --transport stdio postgres \
  -- npx -y @bytebase/dbhub \
  --dsn "$DATABASE_URL"
```

**Option B — Archived MCP reference server (compatibility only):**

```bash
claude mcp add --transport stdio postgres \
  -- npx -y @modelcontextprotocol/server-postgres \
  "$DATABASE_URL"
```

The official MCP reference servers repository is archived, so treat `@modelcontextprotocol/server-postgres` as a legacy example rather than the default choice.

## Available Operations

Once connected, you can:

- **Query:** Run read-only SQL queries against your database
- **Schema:** Inspect table schemas, columns, indexes, and constraints
- **Explore:** List tables, views, and relationships

## Usage Examples

- "Show me the schema for the users table"
- "List all tables in the public schema"
- "Find users who signed up in the last 7 days"
- "Show indexes on the orders table"

## Security Notes

- **Use a read-only database user** — create a dedicated role with SELECT-only permissions
- Never use production credentials in development
- Prefer environment variables or a secret manager over inline credentials
- Evaluate maintenance posture before adopting third-party MCP servers in production
- Consider using connection pooling (PgBouncer) for shared environments
