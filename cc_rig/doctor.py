"""Health check for cc-rig projects.

Validates generated output against the saved config and manifest.
Supports --fix for safe auto-remediation of common issues.
"""

from __future__ import annotations

import json
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def run_doctor(
    project_dir: Path,
    fix: bool = False,
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
    _check_cc_version(result)

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
    ".claude/settings.local.json",
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


def _check_cc_version(result: DoctorResult) -> None:
    """Check Claude Code version compatibility."""
    from cc_rig.config.cc_version import detect_cc_version

    cc = detect_cc_version()
    for w in cc.warnings:
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
