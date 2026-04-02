"""Generate .claude/agents/ subagent markdown files."""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker

_DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class AgentDef:
    """Agent definition with required and optional CC frontmatter fields."""

    description: str
    model: str
    tools: str
    body: str
    # Optional CC frontmatter (omitted from YAML when None)
    permission_mode: str | None = None  # "plan", "dontAsk", etc.
    max_turns: int | None = None  # e.g. 15
    background: bool | None = None  # True for parallel workers
    isolation: str | None = None  # "worktree"
    agent_memory: str | None = None  # "user", "project", "local"
    disallowed_tools: str | None = None  # comma-separated
    effort: str | None = None  # "low", "medium", "high"
    skills: str | None = None  # comma-separated skill names to preload
    initial_prompt: str | None = None  # auto-submit first turn (v2.1.83+)


# ── Agent definitions (loaded from JSON) ──────────────────────────

# Known optional fields on AgentDef (beyond the 4 required fields).
_AGENT_OPTIONAL_FIELDS = frozenset(
    {
        "permission_mode",
        "max_turns",
        "background",
        "isolation",
        "agent_memory",
        "disallowed_tools",
        "effort",
        "skills",
        "initial_prompt",
    }
)


def _load_agent_defs() -> dict[str, AgentDef]:
    """Load agent definitions from cc_rig/data/agents.json."""
    data = json.loads((_DATA_DIR / "agents.json").read_text())
    result: dict[str, AgentDef] = {}
    for name, d in data.items():
        kwargs = {
            "description": d["description"],
            "model": d["model"],
            "tools": d["tools"],
            "body": d["body"],
        }
        for field in _AGENT_OPTIONAL_FIELDS:
            if field in d:
                kwargs[field] = d[field]
        result[name] = AgentDef(**kwargs)
    return result


_AGENT_DEFS: dict[str, AgentDef] = _load_agent_defs()


def generate_agents(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate .claude/agents/{name}.md for each agent in config.

    Returns list of relative file paths written.
    """
    if not config.agents:
        return []

    agents_dir = output_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    files_written: list[str] = []

    for agent_name in config.agents:
        defn = _AGENT_DEFS.get(agent_name)
        if defn is None:
            warnings.warn(
                f"Unknown agent '{agent_name}' — skipped",
                stacklevel=2,
            )
            continue

        model = config.model_overrides.get(agent_name, defn.model)
        lines = [
            "---",
            f"name: {agent_name}",
            f"description: {defn.description}",
            f"model: {model}",
            f"tools: {defn.tools}",
        ]
        if defn.disallowed_tools is not None:
            lines.append(f"disallowedTools: {defn.disallowed_tools}")
        if defn.permission_mode is not None:
            lines.append(f"permissionMode: {defn.permission_mode}")
        if defn.max_turns is not None:
            lines.append(f"maxTurns: {defn.max_turns}")
        if defn.background is not None:
            lines.append(f"background: {'true' if defn.background else 'false'}")
        if defn.isolation is not None:
            lines.append(f"isolation: {defn.isolation}")
        if defn.agent_memory is not None:
            lines.append(f"memory: {defn.agent_memory}")
        if defn.effort is not None:
            lines.append(f"effort: {defn.effort}")
        if defn.skills is not None:
            lines.append(f"skills: {defn.skills}")
        if defn.initial_prompt is not None:
            lines.append(f"initialPrompt: {defn.initial_prompt}")
        lines.append("---")
        content = "\n".join(lines) + f"\n\n{defn.body}\n"

        filename = f"{agent_name}.md"
        rel = f".claude/agents/{filename}"
        if tracker is not None:
            tracker.write_text(rel, content)
        else:
            (agents_dir / filename).write_text(content)
        files_written.append(rel)

    return files_written
