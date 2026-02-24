"""Generate .mcp.json with MCP server configurations."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from cc_rig.config.project import ProjectConfig

# ── MCP server definitions ─────────────────────────────────────────
# Each MCP server: (command, args, env placeholder dict)

_MCP_SERVERS: dict[str, dict] = {
    "github": {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-github",
        ],
        "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-github-token>",
        },
    },
    "postgres": {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-postgres",
        ],
        "env": {
            "POSTGRES_CONNECTION_STRING": ("postgresql://user:password@localhost:5432/dbname"),
        },
    },
    "playwright": {
        "command": "npx",
        "args": [
            "-y",
            "@anthropic/mcp-playwright",
        ],
        "env": {},
    },
    "slack": {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-slack",
        ],
        "env": {
            "SLACK_BOT_TOKEN": "<your-slack-bot-token>",
        },
    },
    "linear": {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-linear",
        ],
        "env": {
            "LINEAR_API_KEY": "<your-linear-api-key>",
        },
    },
    "sentry": {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-sentry",
        ],
        "env": {
            "SENTRY_AUTH_TOKEN": "<your-sentry-auth-token>",
            "SENTRY_ORG": "<your-sentry-org>",
        },
    },
    "filesystem": {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            ".",
        ],
        "env": {},
    },
}


def generate_mcp(
    config: ProjectConfig,
    output_dir: Path,
) -> list[str]:
    """Generate .mcp.json with MCP server entries from config.

    Each server entry uses the standard MCP server schema with
    command, args, and env fields.

    Returns list of relative file paths written.
    """
    if not config.default_mcps:
        return []

    mcp_config: dict[str, dict] = {"mcpServers": {}}

    for mcp_name in config.default_mcps:
        server_def = _MCP_SERVERS.get(mcp_name)
        if server_def is None:
            # Unknown MCP — create a minimal placeholder
            mcp_config["mcpServers"][mcp_name] = {
                "command": "npx",
                "args": ["-y", f"@mcp/{mcp_name}"],
                "env": {},
            }
        else:
            mcp_config["mcpServers"][mcp_name] = copy.deepcopy(server_def)

    output_dir.mkdir(parents=True, exist_ok=True)
    mcp_path = output_dir / ".mcp.json"
    mcp_path.write_text(json.dumps(mcp_config, indent=2) + "\n")

    return [".mcp.json"]
