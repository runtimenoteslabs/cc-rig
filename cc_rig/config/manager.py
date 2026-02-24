"""Config management: save, load, list, inspect, diff, lock.

Personal configs stored in ~/.cc-rig/configs/<name>.json.
Team configs stored in .cc-rig.json in the project root.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cc_rig.config.project import ProjectConfig

_CONFIG_DIR = Path.home() / ".cc-rig" / "configs"

# Fields that are machine-specific and should be stripped
# when creating a portable (team-shareable) config.
_MACHINE_SPECIFIC_FIELDS = {"output_dir", "created_at"}


def config_dir() -> Path:
    """Return the personal config directory, creating it if needed."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return _CONFIG_DIR


def save_config(
    config: ProjectConfig,
    name: str | None = None,
    path: Path | None = None,
    portable: bool = False,
) -> Path:
    """Save a config to personal dir or a custom path.

    Args:
        config: The ProjectConfig to save.
        name: Config name (saved to ~/.cc-rig/configs/<name>.json).
        path: Custom file path (overrides name).
        portable: If True, strip machine-specific fields.

    Returns:
        Path where the config was saved.
    """
    data = config.to_dict()

    if portable:
        data = _make_portable(data)

    if path:
        dest = Path(path)
    elif name:
        dest = config_dir() / f"{name}.json"
    else:
        dest = config_dir() / f"{config.project_name or 'unnamed'}.json"

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2) + "\n")
    return dest


def load_config(name_or_path: str) -> ProjectConfig:
    """Load a config by name or file path.

    If name_or_path is a file path (contains / or .json), load
    directly. Otherwise look in ~/.cc-rig/configs/.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If the JSON is invalid.
    """
    path = _resolve_config_path(name_or_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {name_or_path}")

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    return ProjectConfig.from_dict(data)


def list_configs(
    project_dir: Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """List personal and project configs.

    Returns dict with 'personal' and 'project' keys, each
    containing a list of config summaries.
    """
    personal: list[dict[str, Any]] = []
    cdir = config_dir()
    if cdir.exists():
        for p in sorted(cdir.glob("*.json")):
            try:
                data = json.loads(p.read_text())
                personal.append(
                    {
                        "name": p.stem,
                        "path": str(p),
                        "template": data.get("template_preset", ""),
                        "workflow": data.get("workflow_preset", ""),
                        "locked": data.get("locked", False),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                personal.append(
                    {
                        "name": p.stem,
                        "path": str(p),
                        "template": "?",
                        "workflow": "?",
                        "locked": False,
                    }
                )

    project: list[dict[str, Any]] = []
    if project_dir:
        cc_rig_json = project_dir / ".cc-rig.json"
        if cc_rig_json.exists():
            try:
                data = json.loads(cc_rig_json.read_text())
                project.append(
                    {
                        "name": data.get("project_name", cc_rig_json.stem),
                        "path": str(cc_rig_json),
                        "template": data.get("template_preset", ""),
                        "workflow": data.get("workflow_preset", ""),
                        "locked": data.get("locked", False),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                project.append(
                    {
                        "name": cc_rig_json.stem,
                        "path": str(cc_rig_json),
                        "template": "?",
                        "workflow": "?",
                        "locked": False,
                    }
                )

    return {"personal": personal, "project": project}


def inspect_config(name_or_path: str) -> str:
    """Pretty-print a config. Returns formatted string."""
    config = load_config(name_or_path)
    data = config.to_dict()
    locked = _is_locked_path(_resolve_config_path(name_or_path))

    lines = []
    if locked:
        lines.append("[LOCKED]")
    lines.append(f"Project:    {config.project_name}")
    lines.append(f"Template:   {config.template_preset}")
    lines.append(f"Workflow:   {config.workflow_preset}")
    lines.append(f"Stack:      {config.language} / {config.framework}")
    lines.append(f"Type:       {config.project_type}")
    lines.append("")
    lines.append(f"Agents:     {len(config.agents)} — " + ", ".join(config.agents))
    lines.append(f"Commands:   {len(config.commands)} — " + ", ".join(config.commands))
    lines.append(f"Hooks:      {len(config.hooks)} — " + ", ".join(config.hooks))
    lines.append(f"Skills:     {', '.join(s.name for s in config.recommended_skills)}")
    lines.append(f"MCPs:       {', '.join(config.default_mcps)}")
    lines.append("")
    lines.append("Features:")
    for feat_name, enabled in data.get("features", {}).items():
        status = "on" if enabled else "off"
        lines.append(f"  {feat_name}: {status}")
    lines.append("")
    lines.append(f"Permission: {config.permission_mode}")
    lines.append(f"Plan:       {config.claude_plan}")

    return "\n".join(lines)


def diff_configs(
    config_a: ProjectConfig,
    config_b: ProjectConfig,
) -> str:
    """Show meaningful differences between two configs.

    Returns a human-readable diff string. Empty string if identical.
    """
    dict_a = config_a.to_dict()
    dict_b = config_b.to_dict()
    lines: list[str] = []

    for key in sorted(set(dict_a.keys()) | set(dict_b.keys())):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            lines.append(f"  {key}:")
            lines.append(f"    - {val_a}")
            lines.append(f"    + {val_b}")

    if not lines:
        return ""
    return "Differences:\n" + "\n".join(lines)


def lock_config(name_or_path: str) -> Path:
    """Mark a config as locked. Returns the path.

    Locked configs cannot be modified via the wizard —
    only project name and output dir can change.
    """
    path = _resolve_config_path(name_or_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {name_or_path}")

    data = json.loads(path.read_text())
    data["locked"] = True
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path


def unlock_config(name_or_path: str) -> Path:
    """Remove the lock from a config. Returns the path."""
    path = _resolve_config_path(name_or_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {name_or_path}")

    data = json.loads(path.read_text())
    data.pop("locked", None)
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path


def is_locked(name_or_path: str) -> bool:
    """Check if a config is locked."""
    path = _resolve_config_path(name_or_path)
    return _is_locked_path(path)


def _is_locked_path(path: Path) -> bool:
    """Check if a config file is locked."""
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
        return bool(data.get("locked", False))
    except (json.JSONDecodeError, KeyError):
        return False


def _make_portable(data: dict[str, Any]) -> dict[str, Any]:
    """Strip machine-specific fields for team sharing."""
    portable = dict(data)
    for field_name in _MACHINE_SPECIFIC_FIELDS:
        portable.pop(field_name, None)
    return portable


def _resolve_config_path(name_or_path: str) -> Path:
    """Resolve a name or path to a concrete file path."""
    p = Path(name_or_path)
    if "/" in name_or_path or "\\" in name_or_path or p.suffix:
        return p
    return config_dir() / f"{name_or_path}.json"
