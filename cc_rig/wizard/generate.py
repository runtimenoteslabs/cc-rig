"""Generation, validation, and config save (Screens 8-10)."""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.orchestrator import generate_all
from cc_rig.ui.display import format_file_list, heading, success, warning
from cc_rig.ui.prompts import IO
from cc_rig.validator import validate_output

# MCP servers that require user-provided credentials.
_MCP_NEEDS_CREDS: dict[str, str] = {
    "github": "GITHUB_PERSONAL_ACCESS_TOKEN",
    "postgres": "POSTGRES_CONNECTION_STRING",
    "slack": "SLACK_BOT_TOKEN",
    "linear": "LINEAR_API_KEY",
    "sentry": "SENTRY_AUTH_TOKEN",
}


def run_generation(
    config: ProjectConfig,
    output_dir: Path,
    io: IO,
) -> int:
    """Generate files, validate, save config. Returns exit code."""
    io.say(heading("Generating project files..."))
    io.say("")

    # Generate
    manifest = generate_all(config, output_dir)
    files = manifest["files"]

    io.say(format_file_list(files))
    io.say(f"\n  {len(files)} files generated.\n")

    # Validate
    io.say(heading("Validating output..."))
    result = validate_output(config, output_dir, manifest)

    if result.errors:
        for issue in result.errors:
            io.say(f"  ERROR: {issue.check}: {issue.message}")
        io.say(f"\n  {len(result.errors)} error(s) found.")
        return 1

    if result.warnings:
        for issue in result.warnings:
            io.say(f"  {warning(issue.message)}")

    io.say(f"  {success('All checks passed.')}\n")

    # Auto-save config to personal directory
    _auto_save_personal(config, io)

    # Files that need user attention
    attention = _needs_attention(config)
    if attention:
        io.say(heading("Needs your attention"))
        io.say("")
        for item in attention:
            io.say(f"  {warning(item)}")
        io.say("")

    # Summary
    io.say(heading("Done!"))
    io.say("")
    io.say(f"  Output: {output_dir}")
    io.say(f"  Config: {output_dir / '.cc-rig.json'}")
    io.say("")
    io.say("  Next steps:")
    io.say(f"    cd {output_dir}")
    io.say("    claude          # start Claude Code")
    io.say("    cc-rig doctor   # check project health")
    io.say("")

    return 0


def _needs_attention(config: ProjectConfig) -> list[str]:
    """Return list of actionable items the user should address."""
    items: list[str] = []

    # MCP servers with placeholder credentials
    cred_servers = [name for name in config.default_mcps if name in _MCP_NEEDS_CREDS]
    if cred_servers:
        names = ", ".join(cred_servers)
        items.append(f".mcp.json — add credentials for: {names}")

    # Stub skills that need filling in
    items.append(".claude/skills/project-patterns/SKILL.md — add your team's conventions")
    items.append(".claude/skills/deployment-checklist/SKILL.md — add deploy steps")

    return items


def _auto_save_personal(config: ProjectConfig, io: IO) -> None:
    """Auto-save config to ~/.cc-rig/configs/ for personal reuse."""
    try:
        from cc_rig.config.manager import save_config

        dest = save_config(config)
        io.say(f"  Config saved: {dest}")
    except OSError as exc:
        io.say(f"  Warning: could not save config: {exc}")
