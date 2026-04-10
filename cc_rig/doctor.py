"""Health check for cc-rig projects.

Validates generated output against the saved config and manifest.
Supports --fix for safe auto-remediation of common issues.
"""

from __future__ import annotations

import json
import re
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.memory import MEMORY_FILE_TEMPLATES
from cc_rig.validator import ValidationResult, validate_output

# How many days before session-log is considered stale.
_SESSION_LOG_STALE_DAYS = 7


class DoctorResult:
    """Collects issues found during health check."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.fixes: list[str] = []
        self.info: list[str] = []

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def run_doctor(
    project_dir: Path,
    fix: bool = False,
    check_compat: bool = False,
) -> DoctorResult:
    """Run health checks on a cc-rig project.

    Args:
        project_dir: Root of the project (where .cc-rig.json lives).
        fix: If True, attempt safe auto-fixes.

    Returns:
        DoctorResult with errors, warnings, and fixes applied.
    """
    result = DoctorResult()

    # ── Check 1: .cc-rig.json exists ──────────────────────────────
    config_path = project_dir / ".cc-rig.json"
    if not config_path.exists():
        result.errors.append("No .cc-rig.json found — not a cc-rig project.")
        return result

    try:
        config_data = json.loads(config_path.read_text())
        config = ProjectConfig.from_dict(config_data)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        result.errors.append(f".cc-rig.json is invalid: {exc}")
        return result

    # ── Fast path: --check-compat only ────────────────────────────
    if check_compat:
        _check_cc_version(result, config=config)
        return result

    # ── Check 2: Manifest exists ──────────────────────────────────
    manifest_path = project_dir / ".claude" / ".cc-rig-manifest.json"
    manifest: dict[str, Any] | None = None
    if not manifest_path.exists():
        result.warnings.append("Manifest (.cc-rig-manifest.json) not found.")
    else:
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            result.errors.append("Manifest contains invalid JSON.")

    # ── Check 3: Run validator checks ─────────────────────────────
    validation = validate_output(config, project_dir, manifest)
    _merge_validation(validation, result)

    # ── Check 4: Hook script permissions ──────────────────────────
    _check_hook_permissions(project_dir, result, fix)

    # ── Check 5: Session-log staleness ────────────────────────────
    _check_session_log_staleness(project_dir, config, result)

    # ── Check 6: Orphaned files ───────────────────────────────────
    if manifest:
        _check_orphaned_files(project_dir, manifest, result)

    # ── Check 7: Missing memory files (fixable) ──────────────────
    if config.features.memory:
        _check_and_fix_memory(project_dir, result, fix)

    # ── Check 8: Claude Code version ───────────────────────────
    _check_cc_version(result, config=config)

    # ── Check 9: LSP plugin binaries ─────────────────────────
    _check_plugin_binaries(config, result)

    # ── Check 10: Process skills installed ──────────────────
    if config.process_skills:
        _check_process_skills(config, project_dir, result)

    # ── Check 11: CLAUDE.md cache-friendliness ────────────
    _check_claude_md_cache_friendliness(project_dir, result)

    # ── Check 12: Cache health from session JSONL ─────────
    _check_cache_health(project_dir, result)

    # ── Check 13: JSONL accounting integrity ──────────────
    _check_jsonl_accounting(project_dir, result)

    # ── Check 14: RTK output compression ─────────────────
    _check_rtk(project_dir, result)

    # ── Check 15: Squeez output compression ─────────────
    _check_squeez(project_dir, result)

    return result


def _merge_validation(validation: ValidationResult, result: DoctorResult) -> None:
    """Convert validator issues into doctor result entries."""
    for issue in validation.errors:
        loc = f" ({issue.file})" if issue.file else ""
        result.errors.append(f"[{issue.check}] {issue.message}{loc}")
    for issue in validation.warnings:
        loc = f" ({issue.file})" if issue.file else ""
        result.warnings.append(f"[{issue.check}] {issue.message}{loc}")


def _check_hook_permissions(
    project_dir: Path,
    result: DoctorResult,
    fix: bool,
) -> None:
    """Check that hook shell scripts are executable."""
    hooks_dir = project_dir / ".claude" / "hooks"
    if not hooks_dir.exists():
        return

    for script in hooks_dir.glob("*.sh"):
        st = script.stat()
        is_executable = bool(st.st_mode & stat.S_IXUSR)
        if not is_executable:
            if fix:
                script.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                result.fixes.append(f"Fixed permissions: {script.name}")
            else:
                result.warnings.append(
                    f"Hook script not executable: {script.name} (fix with --fix)"
                )


def _check_session_log_staleness(
    project_dir: Path,
    config: ProjectConfig,
    result: DoctorResult,
) -> None:
    """Warn if session-log.md hasn't been updated recently."""
    if not config.features.memory:
        return

    session_log = project_dir / "memory" / "session-log.md"
    if not session_log.exists():
        return  # Handled by memory file check

    # Check file modification time
    mtime = datetime.fromtimestamp(session_log.stat().st_mtime, tz=timezone.utc)
    age_days = (datetime.now(tz=timezone.utc) - mtime).days
    if age_days > _SESSION_LOG_STALE_DAYS:
        result.warnings.append(f"Session log is {age_days} days old — consider updating.")


# Files created by Claude Code itself (not by cc-rig) — never report as orphaned.
_CC_NATIVE_FILES = {
    ".claude/.cc-rig-manifest.json",
}

# Filename patterns that are CC-native (checked by basename).
_CC_NATIVE_PREFIXES = (".cache", ".tmp")


def _check_orphaned_files(
    project_dir: Path,
    manifest: dict[str, Any],
    result: DoctorResult,
) -> None:
    """Find files in .claude/ not tracked by manifest."""
    manifest_files = set(manifest.get("files", []))

    # Check .claude/ directory for untracked files
    claude_dir = project_dir / ".claude"
    if not claude_dir.exists():
        return

    for path in claude_dir.rglob("*"):
        if path.is_file():
            rel = str(path.relative_to(project_dir))
            if rel in manifest_files:
                continue
            if rel in _CC_NATIVE_FILES:
                continue
            if path.name.startswith(_CC_NATIVE_PREFIXES):
                continue
            result.warnings.append(f"Orphaned file (not in manifest): {rel}")


def _check_cc_version(
    result: DoctorResult,
    config: ProjectConfig | None = None,
) -> None:
    """Check Claude Code version compatibility."""
    from cc_rig.config.cc_version import check_feature_compat, detect_cc_version

    cc = detect_cc_version()
    for w in cc.warnings:
        result.warnings.append(w)

    # Feature compatibility checks (when config is available)
    if config is not None and cc.version is not None:
        for w in check_feature_compat(cc.version, config):
            result.warnings.append(w)


def _check_and_fix_memory(
    project_dir: Path,
    result: DoctorResult,
    fix: bool,
) -> None:
    """Check for missing memory files and optionally create them."""
    memory_dir = project_dir / "memory"

    for filename, template in MEMORY_FILE_TEMPLATES.items():
        filepath = memory_dir / filename
        if not filepath.exists():
            if fix:
                memory_dir.mkdir(parents=True, exist_ok=True)
                filepath.write_text(template)
                result.fixes.append(f"Created missing memory file: {filename}")
            # Note: missing memory files are already caught by validator V19


def _check_plugin_binaries(config: ProjectConfig, result: DoctorResult) -> None:
    """Check that LSP plugin binaries are available on PATH."""
    for plugin in config.recommended_plugins:
        if plugin.requires_binary:
            if not shutil.which(plugin.requires_binary):
                result.warnings.append(
                    f"Plugin {plugin.name!r} requires {plugin.requires_binary!r} "
                    f"but it was not found on PATH. LSP features may not activate."
                )


def _check_process_skills(config: ProjectConfig, output_dir: Path, result: DoctorResult) -> None:
    """Check that process skills are installed for the workflow."""
    for skill_name in config.process_skills:
        skill_dir = output_dir / ".claude" / "skills" / skill_name
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            result.warnings.append(
                f"Process skill {skill_name!r} (workflow={config.workflow}) "
                f"not found at {skill_md}. Run cc-rig init to install."
            )


# Patterns that indicate dynamic content in the static zone of CLAUDE.md.
_DATE_RE = re.compile(r"\b20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b")
_TIMESTAMP_MARKER_RE = re.compile(r"(?i)(updated|modified|generated)\s*[:=]")


def _check_claude_md_cache_friendliness(
    project_dir: Path,
    result: DoctorResult,
) -> None:
    """Warn if CLAUDE.md has dynamic content in its static (cacheable) zone."""
    claude_md = project_dir / "CLAUDE.md"
    if not claude_md.exists():
        return

    try:
        lines = claude_md.read_text().splitlines()
    except OSError:
        return

    # Find the boundary between static and dynamic zones.
    boundary = len(lines)
    for i, line in enumerate(lines):
        if line.strip().startswith("## Current Context"):
            boundary = i
            break

    # If no "## Current Context" found, treat the top 80% as the static zone.
    if boundary == len(lines) and lines:
        boundary = int(len(lines) * 0.8)

    static_zone = lines[:boundary]

    for i, line in enumerate(static_zone, start=1):
        if _TIMESTAMP_MARKER_RE.search(line):
            result.warnings.append(
                f"CLAUDE.md line {i}: timestamp marker in static section. "
                f"Move to Current Context or CLAUDE.local.md to avoid cache breaks."
            )
            break  # One warning is enough
        if _DATE_RE.search(line):
            result.warnings.append(
                f"CLAUDE.md line {i}: date in static section. "
                f"Move to Current Context or CLAUDE.local.md to avoid cache breaks."
            )
            break


def _get_session_dir(project_dir: Path) -> Path:
    """Derive the Claude Code session directory for a project.

    Claude Code stores session JSONL files in ~/.claude/projects/<encoded-path>/.
    The path encoding replaces '/' with '-' and strips the leading '/'.
    """
    encoded = str(project_dir.resolve()).replace("/", "-").lstrip("-")
    return Path.home() / ".claude" / "projects" / f"-{encoded}"


def _check_cache_health(
    project_dir: Path,
    result: DoctorResult,
) -> None:
    """Check prompt cache hit ratio from the most recent session JSONL."""
    session_dir = _get_session_dir(project_dir)
    if not session_dir.is_dir():
        return

    # Find the most recent JSONL file.
    jsonl_files = sorted(session_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not jsonl_files:
        return

    latest = jsonl_files[-1]
    cache_read = 0
    cache_creation = 0

    try:
        with open(latest) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "assistant":
                    continue
                usage = (entry.get("message") or {}).get("usage") or {}
                cache_read += usage.get("cache_read_input_tokens", 0)
                cache_creation += usage.get("cache_creation_input_tokens", 0)
    except OSError:
        return

    total = cache_read + cache_creation
    if total == 0:
        return

    ratio = cache_read / total
    if ratio < 0.40:
        result.warnings.append(
            f"Cache health: {ratio:.0%} cache hit ratio in most recent session "
            f"(target: >40%). See agent_docs/cache-friendly-workflow.md."
        )


def _check_jsonl_accounting(
    project_dir: Path,
    result: DoctorResult,
) -> None:
    """Report JSONL accounting integrity for the most recent session.

    Detects duplicate PRELIM entries from extended thinking by looking for
    consecutive assistant entries with identical cache token pairs.
    Reports raw data as info (not a warning).
    """
    session_dir = _get_session_dir(project_dir)
    if not session_dir.is_dir():
        return

    jsonl_files = sorted(session_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not jsonl_files:
        return

    latest = jsonl_files[-1]

    # Parse JSONL, tracking consecutive assistant cache key runs.
    # Non-assistant entries break runs (they represent different API calls).
    raw_count = 0
    deduped_count = 0
    prev_cache_key: Optional[tuple[int, int]] = None

    try:
        with open(latest) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "assistant":
                    # Non-assistant entry breaks the current run.
                    if prev_cache_key is not None:
                        deduped_count += 1
                        prev_cache_key = None
                    continue
                usage = (entry.get("message") or {}).get("usage") or {}
                cache_key = (
                    usage.get("cache_creation_input_tokens", 0),
                    usage.get("cache_read_input_tokens", 0),
                )
                raw_count += 1
                if prev_cache_key is not None and cache_key == prev_cache_key:
                    # Same run: this replaces the pending entry (skip).
                    pass
                else:
                    # New run: flush previous, start new.
                    if prev_cache_key is not None:
                        deduped_count += 1
                    prev_cache_key = cache_key
        # Flush final pending entry.
        if prev_cache_key is not None:
            deduped_count += 1
    except OSError:
        return

    if raw_count == 0:
        return

    ratio = raw_count / deduped_count if deduped_count > 0 else 0.0
    skipped = raw_count - deduped_count

    msg = f"JSONL accounting: {raw_count} entries, {deduped_count} after dedup ({ratio:.2f}x)."
    if skipped > 0:
        msg += f" {skipped} PRELIM entries detected."
    result.info.append(msg)


def _check_rtk(
    project_dir: Path,
    result: DoctorResult,
) -> None:
    """Check if RTK (tool output compression) is installed and configured.

    RTK is optional and complementary. Info-level only, never a warning.
    """
    rtk_path = shutil.which("rtk")
    if not rtk_path:
        return  # Optional tool, skip silently

    # Get version
    version = "unknown"
    try:
        proc = subprocess.run(
            ["rtk", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            version = proc.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass

    # Check if hook is wired in project or global settings.json
    hook_configured = _rtk_hook_configured(project_dir)

    if hook_configured:
        result.info.append(f"RTK ({version}) detected, Bash output compression active.")
    else:
        result.info.append(
            f"RTK ({version}) installed but hook not configured. "
            "Run `rtk init -g` to enable Bash output compression."
        )


def _rtk_hook_configured(project_dir: Path) -> bool:
    """Check if RTK's PreToolUse hook is registered in settings.json."""
    return _hook_command_contains(project_dir, "PreToolUse", "rtk")


def _check_squeez(
    project_dir: Path,
    result: DoctorResult,
) -> None:
    """Check if squeez (token compression) is installed and configured.

    Squeez is optional and complementary. Info-level only, never a warning.
    """
    squeez_path = shutil.which("squeez")
    if not squeez_path:
        return  # Optional tool, skip silently

    # Get version
    version = "unknown"
    try:
        proc = subprocess.run(
            ["squeez", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            version = proc.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass

    hook_configured = _hook_command_contains(project_dir, "PreToolUse", "squeez")

    if hook_configured:
        result.info.append(f"squeez ({version}) detected, Bash output compression active.")
    else:
        result.info.append(
            f"squeez ({version}) installed but hook not configured. "
            "Run `squeez install` to enable Bash output compression."
        )


def _hook_command_contains(project_dir: Path, event: str, needle: str) -> bool:
    """Check if any hook command for the given event contains the needle string."""
    candidates = [
        project_dir / ".claude" / "settings.json",
        Path.home() / ".claude" / "settings.json",
    ]
    for settings_path in candidates:
        if not settings_path.exists():
            continue
        try:
            data = json.loads(settings_path.read_text())
            hooks = data.get("hooks", {}).get(event, [])
            for entry in hooks:
                if isinstance(entry, dict):
                    for h in entry.get("hooks", []):
                        cmd = h.get("command", "") if isinstance(h, dict) else ""
                        if needle in cmd:
                            return True
                    cmd = entry.get("command", "")
                    if needle in cmd:
                        return True
        except (json.JSONDecodeError, OSError):
            continue
    return False
