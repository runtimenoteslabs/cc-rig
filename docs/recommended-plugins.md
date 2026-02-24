# Recommended Plugins and Extensions

cc-rig generates native Claude Code configuration files. These plugins and extensions complement a cc-rig setup.

## MCP Servers

cc-rig generates `.mcp.json` with server stubs for your stack. Popular MCP servers:

| Server | Purpose | Install |
|--------|---------|---------|
| [filesystem](https://github.com/anthropics/claude-code) | File system access (built-in) | Built into Claude Code |
| [postgres](https://github.com/anthropics/claude-code) | PostgreSQL read-only queries | Configured in .mcp.json |
| [sqlite](https://github.com/anthropics/claude-code) | SQLite database access | Configured in .mcp.json |
| [github](https://github.com/anthropics/claude-code) | GitHub API integration | Configured in .mcp.json |

See [docs/mcp-setup.md](mcp-setup.md) for configuration details.

## IDE Extensions

cc-rig generates files that work with Claude Code in any environment:

- **VS Code** — Claude Code extension (official)
- **JetBrains** — Claude Code plugin
- **Terminal** — `claude` CLI directly

## Complementary Tools

| Tool | Purpose | Relationship to cc-rig |
|------|---------|----------------------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | AI coding assistant | cc-rig generates config for Claude Code |
| [SuperClaude](https://github.com/NickJBain/super-claude) | Alternative Claude Code enhancer | cc-rig is an alternative approach |
| [pytest](https://docs.pytest.org/) | Python testing | cc-rig configures test commands for pytest |
| [ruff](https://docs.astral.sh/ruff/) | Python linting/formatting | cc-rig configures lint/format hooks for ruff |

## Plugin Installation Pattern

cc-rig does not download or install plugins. It generates configuration that references them. To use a plugin:

1. Install the plugin separately (pip, npm, etc.)
2. Run `cc-rig init` — it will detect and configure for installed tools
3. Or manually update `.mcp.json` / `.claude/settings.json`
