"""Generate .claude/commands/ slash command markdown files."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import NamedTuple

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker

_DATA_DIR = Path(__file__).parent.parent / "data"


class CommandDef(NamedTuple):
    """Command definition: (description, allowed_tools, prompt_body)."""

    description: str
    allowed_tools: str
    body: str


# ── Command definitions (loaded from JSON) ─────────────────────────


def _load_command_defs() -> dict[str, tuple[str, str, str]]:
    """Load command definitions from cc_rig/data/commands.json."""
    data = json.loads((_DATA_DIR / "commands.json").read_text())
    return {name: (d["description"], d["allowed_tools"], d["body"]) for name, d in data.items()}


_COMMAND_DEFS: dict[str, tuple[str, str, str]] = _load_command_defs()

# Effort level per workflow for command frontmatter (CC v2.1.80+).
# Only emit for workflows with a non-default effort.
_WORKFLOW_EFFORT: dict[str, str] = {
    "speedrun": "low",
    "spec-driven": "high",
    "superpowers": "high",
    "verify-heavy": "high",
}


def generate_commands(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate .claude/commands/{name}.md for each command in config.

    Returns list of relative file paths written.
    """
    if not config.commands:
        return []

    commands_dir = output_dir / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    files_written: list[str] = []

    for cmd_name in config.commands:
        raw = _COMMAND_DEFS.get(cmd_name)
        if raw is None:
            warnings.warn(
                f"Unknown command '{cmd_name}' — skipped",
                stacklevel=2,
            )
            continue

        defn = CommandDef(*raw)
        effort = _WORKFLOW_EFFORT.get(config.workflow)
        effort_line = f"effort: {effort}\n" if effort else ""
        content = (
            f"---\ndescription: {defn.description}\n"
            f"allowed-tools: {defn.allowed_tools}\n"
            f"{effort_line}---\n\n{defn.body}\n"
        )

        filename = f"{cmd_name}.md"
        rel = f".claude/commands/{filename}"
        if tracker is not None:
            tracker.write_text(rel, content)
        else:
            (commands_dir / filename).write_text(content)
        files_written.append(rel)

    return files_written
