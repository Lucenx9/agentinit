# MCP: PostgreSQL Integration

## Setup

Add a PostgreSQL MCP server to Claude Code:

**Option A — Using dbhub (recommended):**

```bash
claude mcp add --transport stdio postgres \
  -- npx -y @bytebase/dbhub \
  --dsn "postgresql://user:password@localhost:5432/dbname"
```

**Option B — Using the MCP reference server:**

```bash
claude mcp add --transport stdio postgres \
  -- npx -y @modelcontextprotocol/server-postgres \
  "postgresql://user:password@localhost:5432/dbname"
```

Replace the connection string with your actual database credentials.

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
- Store connection strings in environment variables, not in code:
  ```bash
  export DATABASE_URL="postgresql://readonly:pass@localhost:5432/mydb"
  ```
- Consider using connection pooling (PgBouncer) for shared environments
