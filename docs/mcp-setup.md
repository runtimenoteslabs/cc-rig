# MCP Server Configuration Guide

cc-rig generates `.mcp.json` with server stubs matched to your template. This guide explains how to configure the connection details.

## What is MCP?

Model Context Protocol (MCP) lets Claude Code connect to external data sources — databases, APIs, file systems — through a standardized interface. cc-rig generates the configuration file; you supply the connection details.

## Generated Configuration

cc-rig creates `.mcp.json` in your project root. The servers included depend on your template:

| Template | MCP Servers |
|----------|-------------|
| FastAPI | filesystem, postgres |
| Django | filesystem, postgres |
| Flask | filesystem, postgres |
| Next.js | filesystem |
| Gin | filesystem, postgres |
| Echo | filesystem, postgres |
| Rust CLI | filesystem |

## Configuration Format

The `.mcp.json` file follows this structure:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "command-to-start-server",
      "args": ["arg1", "arg2"],
      "env": {
        "KEY": "value"
      }
    }
  }
}
```

## Setting Up PostgreSQL

For templates that include a postgres MCP server:

1. Install the MCP postgres server (if not bundled with Claude Code)
2. Update `.mcp.json` with your connection details:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-postgres"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/mydb"
      }
    }
  }
}
```

**Security note:** Never commit database credentials. Use environment variables or `.env` files (which cc-rig's block-env hook prevents Claude from writing to).

## Setting Up GitHub

To add GitHub API access:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

Set `GITHUB_TOKEN` in your shell environment, not in the config file.

## Adding Custom MCP Servers

Add any MCP-compatible server to `.mcp.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "path/to/server",
      "args": [],
      "env": {}
    }
  }
}
```

## Verifying MCP Setup

After configuring, restart Claude Code and check that servers connect:

```bash
claude
# Then ask: "What MCP servers are connected?"
```

## Sensitive Data

- **Never commit** `.mcp.json` with real credentials
- Use environment variable references (`${VAR}`) instead of hardcoded values
- cc-rig adds `.mcp.json` to the generated `.gitignore` by default
- The `block-env` hook prevents Claude from writing to sensitive files
