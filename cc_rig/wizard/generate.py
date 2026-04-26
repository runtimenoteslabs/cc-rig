"""Generation, validation, and config save (Screens 8-10)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cc_rig.clean import _remove_empty_dirs, cleanup_files, load_manifest
from cc_rig.config.project import ProjectConfig
from cc_rig.config.schema import validate_config_warnings
from cc_rig.generators.orchestrator import generate_all
from cc_rig.generators.playbook import WORKFLOW_CHAINS
from cc_rig.ui.display import format_file_list, heading, strip_ansi, success, warning
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


class _TeeIO:
    """IO wrapper that captures output to an internal buffer."""

    def __init__(self, inner: IO) -> None:
        self._inner = inner
        self._lines: list[str] = []

    def say(self, *args: Any, **kwargs: Any) -> None:
        self._inner.say(*args, **kwargs)
        self._lines.append(" ".join(str(a) for a in args))

    def ask(self, prompt: str) -> str:
        return self._inner.ask(prompt)

    @property
    def is_tty(self) -> bool:
        return self._inner.is_tty

    def get_log(self) -> str:
        return "\n".join(self._lines)


def _save_generation_log(output_dir: Path, raw_log: str) -> None:
    """Write generation log to .claude/cc-rig-init.log with a root symlink."""
    log_dir = output_dir / ".claude"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "cc-rig-init.log"
    log_file.write_text(strip_ansi(raw_log), encoding="utf-8")

    # Create symlink at project root for discoverability
    symlink = output_dir / "cc-rig-init.log"
    try:
        if symlink.is_symlink() or symlink.exists():
            symlink.unlink()
        symlink.symlink_to(Path(".claude") / "cc-rig-init.log")
    except OSError:
        pass  # Skip on Windows without admin or other failures


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

    # Wrap IO to capture output for the generation log
    tee = _TeeIO(io)

    tee.say(heading("Generating project files..."))
    tee.say("")

    # Generate
    manifest = generate_all(config, output_dir, skip_claude_md=skip_claude_md)
    files = manifest["files"]

    tee.say(format_file_list(files))
    tee.say(f"\n  {len(files)} files generated.\n")

    # Clean up orphaned files from previous configuration
    if old_manifest is not None:
        _cleanup_orphans(output_dir, old_manifest, manifest, tee)

    # Validate
    tee.say(heading("Validating output..."))
    result = validate_output(config, output_dir, manifest)

    if result.errors:
        for issue in result.errors:
            tee.say(f"  ERROR: {issue.check}: {issue.message}")
        tee.say(f"\n  {len(result.errors)} error(s) found.")
        _save_generation_log(output_dir, tee.get_log())
        return 1

    if result.warnings:
        for issue in result.warnings:
            tee.say(f"  {warning(issue.message)}")

    tee.say(f"  {success('All checks passed.')}\n")

    # Config warnings (non-fatal)
    config_warnings = validate_config_warnings(config)
    for cw in config_warnings:
        tee.say(f"  {warning(cw)}")
    if config_warnings:
        tee.say("")

    # Auto-save config to personal directory
    _auto_save_personal(config, tee)

    # Files that need user attention
    attention = _needs_attention(config)
    if attention:
        tee.say(heading("Needs your attention"))
        tee.say("")
        for item in attention:
            tee.say(f"  {warning(item)}")
        tee.say("")

    # Value summary
    chain = WORKFLOW_CHAINS.get(config.workflow, "/plan -> implement -> /review -> commit")
    agent_count = len(config.agents)
    plugin_count = len(config.recommended_plugins)
    hook_count = len(config.hooks)
    command_count = len(config.commands)

    tee.say(heading(f"Generated {len(files)} files for {config.workflow} + {config.framework}"))
    tee.say("")
    tee.say(f"  Your workflow:  {chain}")
    tee.say(f"  Your agents:    {agent_count}")
    tee.say(f"  Your plugins:   {plugin_count}")
    tee.say(f"  Your hooks:     {hook_count}")
    tee.say(f"  Your commands:  {command_count}")
    tee.say("  Cache savings:  static-first CLAUDE.md + 4 cache guardrails")
    tee.say("")
    tee.say("  In any session, /cc-rig guides you:")
    tee.say("    /cc-rig          dashboard with your workflow and quick recipes")
    tee.say("    /cc-rig recipes  step-by-step guides for bugs, features, refactors")
    tee.say("    /cc-rig savings  how much cc-rig saved you on tokens")
    tee.say("")

    # Next steps
    tee.say("  Next steps:")
    tee.say(f"    cd {output_dir}")
    git_files = [".claude/"]
    if not skip_claude_md:
        git_files.append("CLAUDE.md")
    git_files.append("PLAYBOOK.md")
    if config.default_mcps:
        git_files.append(".mcp.json")
    git_files.append(".cc-rig.json")
    file_list_str = " ".join(git_files)
    tee.say(f"    git add {file_list_str} && git commit -m 'Add Claude Code config'")
    tee.say("    claude          # start Claude Code")
    tee.say("    cc-rig doctor   # check project health")
    tee.say("")

    # Save generation log
    _save_generation_log(output_dir, tee.get_log())
    log_path = output_dir / ".claude" / "cc-rig-init.log"
    io.say(f"  Log saved: {log_path}")
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
