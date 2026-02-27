"""Post-generation validation. Runs after all generators complete."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from cc_rig.config.project import ProjectConfig
from cc_rig.config.schema import VALID_CC_EVENTS


@dataclass
class ValidationIssue:
    """A single validation finding."""

    check: str
    message: str
    severity: str  # "error" or "warning"
    file: str = ""


@dataclass
class ValidationResult:
    """Result of running all validation checks."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def validate_output(
    config: ProjectConfig,
    output_dir: Path,
    manifest: dict | None = None,
) -> ValidationResult:
    """Validate generated output. Returns ValidationResult."""
    result = ValidationResult()

    # Collect manifest-tracked files for scoped checks.
    manifest_files: list[str] = manifest.get("files", []) if manifest else []

    _check_claude_md(output_dir, config, result)
    _check_json_files(output_dir, manifest_files, result)
    _check_settings_hooks(output_dir, result)
    _check_hook_scripts(output_dir, result)
    _check_no_empty_files(output_dir, manifest_files, result)
    _check_no_placeholders(output_dir, manifest_files, result)
    _check_agent_files(output_dir, config, result)
    _check_command_files(output_dir, config, result)
    _check_memory_files(output_dir, config, result)
    _check_claude_local(output_dir, result)
    if manifest:
        _check_manifest(output_dir, manifest, result)

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iter_manifest_files(
    output_dir: Path,
    manifest_files: list[str],
    suffix: str = "",
) -> list[str]:
    """Yield manifest-tracked files that exist on disk.

    When *manifest_files* is empty (no manifest provided), falls back to
    scanning cc-rig managed directories only — never the full project tree.
    Optional *suffix* filters by file extension (e.g. ".json", ".md").
    """
    if manifest_files:
        results = []
        for rel in manifest_files:
            if suffix and not rel.endswith(suffix):
                continue
            if (output_dir / rel).is_file():
                results.append(rel)
        return results

    # Fallback: scan only managed directories.
    managed_dirs = [".claude", "memory", "agent_docs", "tasks", "specs", "docs"]
    results = []
    for managed in managed_dirs:
        managed_path = output_dir / managed
        if managed_path.exists():
            for path in managed_path.rglob("*"):
                if path.is_file():
                    rel = str(path.relative_to(output_dir))
                    if not suffix or rel.endswith(suffix):
                        results.append(rel)
    # Also check top-level generated files.
    for name in ("CLAUDE.md", "CLAUDE.local.md", ".mcp.json", ".cc-rig.json", ".gitignore"):
        if suffix and not name.endswith(suffix):
            continue
        if (output_dir / name).is_file():
            results.append(name)
    return results


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

# Target line counts per workflow (from SMART-DEFAULTS-MATRIX.md §7)
_CLAUDE_MD_LINE_TARGETS: dict[str, int] = {
    "speedrun": 60,
    "standard": 95,
    "spec-driven": 110,
    "gtd-lite": 115,
    "verify-heavy": 120,
}


def _check_claude_md(output_dir: Path, config: ProjectConfig, result: ValidationResult) -> None:
    """V2-V4: Check CLAUDE.md exists, line count, ordering."""
    claude_md = output_dir / "CLAUDE.md"
    if not claude_md.exists():
        result.issues.append(ValidationIssue("V2", "CLAUDE.md not found", "error"))
        return

    content = claude_md.read_text()
    if not content.strip():
        result.issues.append(ValidationIssue("V2", "CLAUDE.md is empty", "error"))
        return

    # V3: Line count check
    line_count = content.count("\n") + 1
    target = _CLAUDE_MD_LINE_TARGETS.get(config.workflow, 90)
    if line_count > target:
        result.issues.append(
            ValidationIssue(
                "V3",
                f"CLAUDE.md has {line_count} lines (target: {target})",
                "warning",
            )
        )

    # V4: Static-first ordering check
    lines = content.split("\n")
    headers = [line.strip() for line in lines if line.startswith("## ")]
    if headers:
        static_headers = {
            "Project Identity",
            "Commands",
            "Guardrails",
            "Framework Rules",
            "Agent Docs",
        }
        dynamic_headers = {"Current Context"}
        last_static = -1
        first_dynamic = len(headers)
        for i, h in enumerate(headers):
            h_text = h.lstrip("# ").strip()
            if h_text in static_headers:
                last_static = i
            if h_text in dynamic_headers:
                first_dynamic = min(first_dynamic, i)
        if last_static >= first_dynamic:
            result.issues.append(
                ValidationIssue(
                    "V4",
                    "CLAUDE.md static sections should come before dynamic",
                    "warning",
                )
            )


def _check_json_files(
    output_dir: Path,
    manifest_files: list[str],
    result: ValidationResult,
) -> None:
    """V1, V18: All JSON files must parse."""
    for rel in _iter_manifest_files(output_dir, manifest_files, suffix=".json"):
        path = output_dir / rel
        try:
            json.loads(path.read_text())
        except json.JSONDecodeError as e:
            result.issues.append(
                ValidationIssue(
                    "V1",
                    f"Invalid JSON: {e}",
                    "error",
                    file=rel,
                )
            )


def _check_settings_hooks(output_dir: Path, result: ValidationResult) -> None:
    """V5-V7: settings.json hook schema validity."""
    settings_path = output_dir / ".claude" / "settings.json"
    if not settings_path.exists():
        return

    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        return  # Already caught by _check_json_files

    hooks = settings.get("hooks", {})
    for event_name, matchers in hooks.items():
        # V6: Valid event names
        if event_name not in VALID_CC_EVENTS:
            result.issues.append(
                ValidationIssue(
                    "V6",
                    f"Unknown hook event: {event_name!r}",
                    "error",
                    file=".claude/settings.json",
                )
            )

        if not isinstance(matchers, list):
            continue

        for matcher in matchers:
            if not isinstance(matcher, dict):
                continue
            for hook in matcher.get("hooks", []):
                # V7: Valid hook types
                hook_type = hook.get("type", "")
                if hook_type not in ("command", "prompt", "agent"):
                    result.issues.append(
                        ValidationIssue(
                            "V7",
                            f"Invalid hook type: {hook_type!r}",
                            "error",
                            file=".claude/settings.json",
                        )
                    )


def _check_hook_scripts(output_dir: Path, result: ValidationResult) -> None:
    """V8-V9: Hook scripts exist and are portable shell."""
    hooks_dir = output_dir / ".claude" / "hooks"
    if not hooks_dir.exists():
        return

    for script in hooks_dir.glob("*.sh"):
        content = script.read_text()

        # V8: Not empty
        if not content.strip():
            result.issues.append(
                ValidationIssue(
                    "V8",
                    "Hook script is empty",
                    "error",
                    file=str(script.relative_to(output_dir)),
                )
            )

        # Check for Node.js (should be portable shell)
        if "node -e" in content or "node --eval" in content:
            result.issues.append(
                ValidationIssue(
                    "V8",
                    "Hook script contains Node.js",
                    "error",
                    file=str(script.relative_to(output_dir)),
                )
            )


def _check_no_empty_files(
    output_dir: Path,
    manifest_files: list[str],
    result: ValidationResult,
) -> None:
    """V13: No zero-byte files."""
    for rel in _iter_manifest_files(output_dir, manifest_files):
        path = output_dir / rel
        if path.stat().st_size == 0:
            result.issues.append(
                ValidationIssue(
                    "V13",
                    "Empty file (0 bytes)",
                    "error",
                    file=rel,
                )
            )


def _check_no_placeholders(
    output_dir: Path,
    manifest_files: list[str],
    result: ValidationResult,
) -> None:
    """V14: No placeholder content in markdown files."""
    placeholder_patterns = ["<!-- TODO", "FILL IN", "YOUR_", "PLACEHOLDER"]
    for rel in _iter_manifest_files(output_dir, manifest_files, suffix=".md"):
        path = output_dir / rel
        content = path.read_text().upper()
        for pattern in placeholder_patterns:
            if pattern in content:
                result.issues.append(
                    ValidationIssue(
                        "V14",
                        f"Placeholder content found: {pattern}",
                        "warning",
                        file=rel,
                    )
                )
                break


def _check_agent_files(
    output_dir: Path,
    config: ProjectConfig,
    result: ValidationResult,
) -> None:
    """V10: Agent files exist and have content."""
    agents_dir = output_dir / ".claude" / "agents"
    for agent in config.agents:
        agent_file = agents_dir / f"{agent}.md"
        if not agent_file.exists():
            result.issues.append(
                ValidationIssue(
                    "V10",
                    f"Agent file missing: {agent}.md",
                    "error",
                    file=f".claude/agents/{agent}.md",
                )
            )


def _check_command_files(
    output_dir: Path,
    config: ProjectConfig,
    result: ValidationResult,
) -> None:
    """V11: Command files exist and have frontmatter."""
    commands_dir = output_dir / ".claude" / "commands"
    for command in config.commands:
        cmd_file = commands_dir / f"{command}.md"
        if not cmd_file.exists():
            result.issues.append(
                ValidationIssue(
                    "V11",
                    f"Command file missing: {command}.md",
                    "error",
                    file=f".claude/commands/{command}.md",
                )
            )
            continue
        content = cmd_file.read_text()
        if not content.startswith("---"):
            result.issues.append(
                ValidationIssue(
                    "V11",
                    f"Command missing frontmatter: {command}.md",
                    "error",
                    file=f".claude/commands/{command}.md",
                )
            )


def _check_memory_files(
    output_dir: Path,
    config: ProjectConfig,
    result: ValidationResult,
) -> None:
    """V19: Memory files present if memory enabled."""
    if not config.features.memory:
        return

    memory_dir = output_dir / "memory"
    expected = [
        "decisions.md",
        "patterns.md",
        "gotchas.md",
        "people.md",
        "session-log.md",
        "MEMORY-README.md",
    ]
    for filename in expected:
        if not (memory_dir / filename).exists():
            result.issues.append(
                ValidationIssue(
                    "V19",
                    f"Memory file missing: {filename}",
                    "error",
                    file=f"memory/{filename}",
                )
            )


def _check_claude_local(output_dir: Path, result: ValidationResult) -> None:
    """V20: CLAUDE.local.md should exist after generation."""
    if not (output_dir / "CLAUDE.local.md").exists():
        result.issues.append(
            ValidationIssue(
                "V20",
                "CLAUDE.local.md not found — personal preference file missing",
                "warning",
                file="CLAUDE.local.md",
            )
        )


def _check_manifest(
    output_dir: Path,
    manifest: dict,
    result: ValidationResult,
) -> None:
    """V16: Manifest tracks all generated files."""
    manifest_files = set(manifest.get("files", []))
    # Only scan cc-rig managed directories, not the entire project tree.
    _MANAGED_DIRS = [".claude", "memory", "agent_docs", "tasks", "specs", "docs"]
    actual_files: set[str] = set()
    for managed in _MANAGED_DIRS:
        managed_path = output_dir / managed
        if managed_path.exists():
            for path in managed_path.rglob("*"):
                if path.is_file():
                    actual_files.add(str(path.relative_to(output_dir)))
    # Also check top-level generated files
    for name in ("CLAUDE.md", "CLAUDE.local.md", ".mcp.json", ".cc-rig.json", ".gitignore"):
        top = output_dir / name
        if top.exists():
            actual_files.add(name)

    untracked = actual_files - manifest_files
    if untracked:
        for f in sorted(untracked):
            result.issues.append(
                ValidationIssue(
                    "V16",
                    f"File not in manifest: {f}",
                    "warning",
                    file=f,
                )
            )
