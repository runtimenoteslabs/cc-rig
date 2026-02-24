"""Generate miscellaneous files: .cc-rig.json config snapshot."""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.project import ProjectConfig


def generate_misc(
    config: ProjectConfig,
    output_dir: Path,
) -> list[str]:
    """Write .cc-rig.json (the full config as JSON).

    This file is the project-level config snapshot for team sharing
    and for `cc-rig config load` to consume.

    Returns list of relative file paths written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / ".cc-rig.json"
    config_path.write_text(config.to_json(indent=2) + "\n")
    return [".cc-rig.json"]
