"""Generation, validation, and config save (Screens 8-10)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cc_rig.clean import _remove_empty_dirs, cleanup_files, load_manifest
from cc_rig.config.project import ProjectConfig
from cc_rig.config.schema import validate_config_warnings
from cc_rig.generators.orchestrator import generate_all
from cc_rig.ui.display import format_file_list, heading, success, warning
from cc_rig.ui.prompts import IO, confirm
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
    # Check for existing configuration
    old_manifest = load_manifest(output_dir)
    if old_manifest is not None:
        old_workflow = old_manifest.get("workflow_preset", "unknown")
        old_count = len(old_manifest.get("files", []))
        if not confirm(
            f"Existing cc-rig configuration found ({old_workflow}, {old_count} files). Overwrite?",
            default=True,
            io=io,
        ):
            io.say("Cancelled.")
            return 0

    # Check for existing CLAUDE.md
    skip_claude_md = False
    existing_claude_md = output_dir / "CLAUDE.md"
    if existing_claude_md.exists():
        io.say("")
        io.say(f"  Existing CLAUDE.md found at {output_dir}/CLAUDE.md")
        io.say("  Backup will be saved to .cc-rig-backup/CLAUDE.md.bak")
        if not confirm("Overwrite existing CLAUDE.md?", default=False, io=io):
            skip_claude_md = True

    io.say(heading("Generating project files..."))
    io.say("")

    # Generate
    manifest = generate_all(config, output_dir, skip_claude_md=skip_claude_md)
    files = manifest["files"]

    io.say(format_file_list(files))
    io.say(f"\n  {len(files)} files generated.\n")

    # Clean up orphaned files from previous configuration
    if old_manifest is not None:
        _cleanup_orphans(output_dir, old_manifest, manifest, io)

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

    # Config warnings (non-fatal)
    config_warnings = validate_config_warnings(config)
    for cw in config_warnings:
        io.say(f"  {warning(cw)}")
    if config_warnings:
        io.say("")

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
    git_files = [".claude/"]
    if not skip_claude_md:
        git_files.append("CLAUDE.md")
    if config.default_mcps:
        git_files.append(".mcp.json")
    git_files.append(".cc-rig.json")
    file_list = " ".join(git_files)
    io.say(
        f"    git add {file_list} "
        "&& git commit -m 'Add Claude Code config'"
    )
    io.say("    claude          # start Claude Code")
    io.say("    cc-rig doctor   # check project health")

    if config.features.memory:
        io.say("")
        io.say(
            "  Memory files (memory/) accumulate project knowledge over time "
            "and are preserved during clean if you've edited them."
        )

    if config.recommended_skills:
        io.say("")
        io.say(
            f"  {len(config.recommended_skills)} skills auto-installed for your stack."
            " Manage with: cc-rig skills list | cc-rig skills catalog"
        )

    io.say("")
    io.say("  Share with teammates:")
    io.say("    cc-rig init --config .cc-rig.json")
    io.say("")

    return 0


def _cleanup_orphans(
    output_dir: Path,
    old_manifest: dict[str, Any],
    new_manifest: dict[str, Any],
    io: IO,
) -> None:
    """Remove files from the old manifest that aren't in the new one."""
    orphans = sorted(set(old_manifest.get("files", [])) - set(new_manifest.get("files", [])))
    if not orphans:
        return

    old_metadata: dict[str, dict[str, Any]] = old_manifest.get("file_metadata", {})
    result = cleanup_files(output_dir, orphans, old_metadata)
    _remove_empty_dirs(output_dir, result)

    removed = len(result.removed)
    restored = len(result.restored)
    preserved = len(result.skipped_user_modified) + len(result.skipped_preexisting)
    total = removed + restored + preserved
    if total > 0:
        parts = []
        if removed:
            parts.append(f"{removed} removed")
        if restored:
            parts.append(f"{restored} restored")
        if preserved:
            parts.append(f"{preserved} preserved")
        detail = ", ".join(parts)
        io.say(f"  Cleaned up {total} orphaned file(s) from previous configuration: {detail}.\n")


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

    return items


def _auto_save_personal(config: ProjectConfig, io: IO) -> None:
    """Auto-save config to ~/.cc-rig/configs/ for personal reuse."""
    try:
        from cc_rig.config.manager import save_config

        dest = save_config(config)
        io.say(f"  Config saved: {dest}")
    except OSError as exc:
        io.say(f"  Warning: could not save config: {exc}")
