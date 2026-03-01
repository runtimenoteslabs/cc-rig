"""Preset loading, listing, inspection, creation, and installation."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

_PRESETS_DIR = Path(__file__).parent

# User-installed presets live here
_USER_PRESETS_DIR = Path.home() / ".cc-rig" / "presets"

# Built-in preset name lists
BUILTIN_TEMPLATES = [
    "nextjs",
    "fastapi",
    "django",
    "gin",
    "echo",
    "rust-cli",
    "rust-web",
    "flask",
    "rails",
]

BUILTIN_WORKFLOWS = [
    "speedrun",
    "standard",
    "spec-driven",
    "gtd-lite",
    "verify-heavy",
]

# Map preset names to filenames (handles hyphens → underscores)
_TEMPLATE_FILES: dict[str, str] = {
    "nextjs": "nextjs.json",
    "fastapi": "fastapi.json",
    "django": "django.json",
    "gin": "gin.json",
    "echo": "echo.json",
    "rust-cli": "rust_cli.json",
    "rust-web": "rust_web.json",
    "flask": "flask.json",
    "rails": "rails.json",
}

_WORKFLOW_FILES: dict[str, str] = {
    "speedrun": "speedrun.json",
    "standard": "standard.json",
    "spec-driven": "spec_driven.json",
    "gtd-lite": "gtd_lite.json",
    "verify-heavy": "verify_heavy.json",
}


def load_template(name: str) -> dict[str, Any]:
    """Load a template preset by name. Raises ValueError if not found."""
    filename = _TEMPLATE_FILES.get(name)
    if filename is None:
        # Check user-installed templates
        user_path = _USER_PRESETS_DIR / "templates" / f"{name}.json"
        if user_path.exists():
            return json.loads(user_path.read_text())
        available = ", ".join(BUILTIN_TEMPLATES)
        raise ValueError(f"Unknown template: {name!r}. Available: {available}")

    path = _PRESETS_DIR / "templates" / filename
    return json.loads(path.read_text())


def load_workflow(name: str) -> dict[str, Any]:
    """Load a workflow preset by name. Raises ValueError if not found."""
    filename = _WORKFLOW_FILES.get(name)
    if filename is None:
        # Check user-installed workflows
        user_path = _USER_PRESETS_DIR / "workflows" / f"{name}.json"
        if user_path.exists():
            return json.loads(user_path.read_text())
        available = ", ".join(BUILTIN_WORKFLOWS)
        raise ValueError(f"Unknown workflow: {name!r}. Available: {available}")

    path = _PRESETS_DIR / "workflows" / filename
    return json.loads(path.read_text())


def list_presets(
    filter_type: str | None = None,
) -> dict[str, list[dict[str, str]]]:
    """List all built-in + user-installed presets.

    Args:
        filter_type: "templates", "workflows", or None for both.
    """
    templates: list[dict[str, str]] = []
    workflows: list[dict[str, str]] = []

    if filter_type != "workflows":
        for name in BUILTIN_TEMPLATES:
            data = load_template(name)
            templates.append(
                {
                    "name": data["name"],
                    "language": data["language"],
                    "framework": data["framework"],
                    "project_type": data["project_type"],
                    "source": "builtin",
                }
            )
        # User-installed templates
        user_tmpl_dir = _USER_PRESETS_DIR / "templates"
        if user_tmpl_dir.exists():
            for p in sorted(user_tmpl_dir.glob("*.json")):
                try:
                    data = json.loads(p.read_text())
                    templates.append(
                        {
                            "name": data.get("name", p.stem),
                            "language": data.get("language", ""),
                            "framework": data.get("framework", ""),
                            "project_type": data.get("project_type", ""),
                            "source": "user",
                        }
                    )
                except (json.JSONDecodeError, KeyError):
                    pass

    if filter_type != "templates":
        for name in BUILTIN_WORKFLOWS:
            data = load_workflow(name)
            workflows.append(
                {
                    "name": data["name"],
                    "description": data["description"],
                    "source": "builtin",
                }
            )
        # User-installed workflows
        user_wf_dir = _USER_PRESETS_DIR / "workflows"
        if user_wf_dir.exists():
            for p in sorted(user_wf_dir.glob("*.json")):
                try:
                    data = json.loads(p.read_text())
                    workflows.append(
                        {
                            "name": data.get("name", p.stem),
                            "description": data.get("description", ""),
                            "source": "user",
                        }
                    )
                except (json.JSONDecodeError, KeyError):
                    pass

    return {"templates": templates, "workflows": workflows}


def inspect_preset(name: str) -> str:
    """Pretty-print a preset's contents. Returns formatted string."""
    # Try template first, then workflow
    try:
        data = load_template(name)
        return _format_template_preset(data)
    except ValueError:
        pass

    try:
        data = load_workflow(name)
        return _format_workflow_preset(data)
    except ValueError:
        pass

    raise ValueError(
        f"Preset not found: {name!r}. Use 'cc-rig preset list' to see available presets."
    )


def create_preset(
    config_path: Path,
    name: str,
    preset_type: str = "workflow",
) -> Path:
    """Create a preset from an existing .cc-rig.json config.

    Args:
        config_path: Path to .cc-rig.json.
        name: Name for the new preset.
        preset_type: "template" or "workflow".

    Returns:
        Path where the preset was saved.
    """
    data = json.loads(config_path.read_text())

    if preset_type == "template":
        preset = {
            "name": name,
            "language": data.get("language", ""),
            "framework": data.get("framework", ""),
            "project_type": data.get("project_type", ""),
            "tool_commands": {
                "test": data.get("test_cmd", ""),
                "lint": data.get("lint_cmd", ""),
                "format": data.get("format_cmd", ""),
                "typecheck": data.get("typecheck_cmd", ""),
                "build": data.get("build_cmd", ""),
            },
            "source_dir": data.get("source_dir", "."),
            "test_dir": data.get("test_dir", "tests"),
            "recommended_skills": data.get("recommended_skills", []),
            "default_mcps": data.get("default_mcps", []),
        }
        dest_dir = _USER_PRESETS_DIR / "templates"
    else:
        preset = {
            "name": name,
            "description": f"Custom workflow from {data.get('project_name', 'project')}",
            "agents": data.get("agents", []),
            "commands": data.get("commands", []),
            "hooks": data.get("hooks", []),
            "features": data.get("features", {}),
            "permission_mode": data.get("permission_mode", "default"),
        }
        dest_dir = _USER_PRESETS_DIR / "workflows"

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{name}.json"
    dest.write_text(json.dumps(preset, indent=2) + "\n")
    return dest


def install_preset(source_path: Path) -> Path:
    """Install a preset from a local file path.

    No URL downloads — local paths only (security).

    Returns:
        Path where the preset was installed.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Preset file not found: {source_path}")

    # Validate it's valid JSON with a name
    try:
        data = json.loads(source_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in preset file: {exc}") from exc

    if "name" not in data:
        raise ValueError("Preset file must contain a 'name' field")

    # Determine type by contents
    if "agents" in data and "commands" in data:
        dest_dir = _USER_PRESETS_DIR / "workflows"
    elif "language" in data and "framework" in data:
        dest_dir = _USER_PRESETS_DIR / "templates"
    else:
        raise ValueError(
            "Cannot determine preset type. Must contain either "
            "'agents'+'commands' (workflow) or 'language'+'framework' (template)."
        )

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{data['name']}.json"
    shutil.copy2(source_path, dest)
    return dest


def _format_template_preset(data: dict[str, Any]) -> str:
    """Format a template preset for display."""
    lines = [
        f"Template: {data['name']}",
        f"  Language:  {data.get('language', '')}",
        f"  Framework: {data.get('framework', '')}",
        f"  Type:      {data.get('project_type', '')}",
        "",
        "  Tool Commands:",
    ]
    for key, val in data.get("tool_commands", {}).items():
        lines.append(f"    {key}: {val}")
    lines.append("")
    lines.append(f"  Source dir: {data.get('source_dir', '.')}")
    lines.append(f"  Test dir:   {data.get('test_dir', 'tests')}")
    skills = data.get("recommended_skills", [])
    if skills:
        skill_names = [s["name"] if isinstance(s, dict) else s for s in skills]
        lines.append(f"  Skills:     {', '.join(skill_names)}")
    mcps = data.get("default_mcps", [])
    if mcps:
        lines.append(f"  MCPs:       {', '.join(mcps)}")
    return "\n".join(lines)


def _format_workflow_preset(data: dict[str, Any]) -> str:
    """Format a workflow preset for display."""
    agents = data.get("agents", [])
    commands = data.get("commands", [])
    hooks = data.get("hooks", [])
    features = data.get("features", {})

    lines = [
        f"Workflow: {data['name']}",
        f"  {data.get('description', '')}",
        "",
        f"  Agents ({len(agents)}):   {', '.join(agents)}",
        f"  Commands ({len(commands)}): {', '.join(commands)}",
        f"  Hooks ({len(hooks)}):    {', '.join(hooks)}",
        "",
        "  Features:",
    ]
    for feat, enabled in features.items():
        status = "on" if enabled else "off"
        lines.append(f"    {feat}: {status}")
    lines.append(f"\n  Permission: {data.get('permission_mode', 'default')}")
    return "\n".join(lines)
