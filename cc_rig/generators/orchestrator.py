"""Orchestrate all file generators and produce the manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cc_rig import __version__
from cc_rig.config.project import ProjectConfig
from cc_rig.generators.addons import generate_addons
from cc_rig.generators.agent_docs import generate_agent_docs
from cc_rig.generators.agents import generate_agents
from cc_rig.generators.claude_local import generate_claude_local
from cc_rig.generators.claude_md import generate_claude_md
from cc_rig.generators.commands import generate_commands
from cc_rig.generators.fileops import FileTracker
from cc_rig.generators.harness import generate_harness
from cc_rig.generators.mcp import generate_mcp
from cc_rig.generators.memory import generate_memory
from cc_rig.generators.misc import generate_misc
from cc_rig.generators.settings import generate_settings
from cc_rig.generators.skills import generate_skills


def generate_all(
    config: ProjectConfig,
    output_dir: Path,
) -> dict[str, Any]:
    """Run every generator in order, collect file lists, write manifest.

    Args:
        config: Fully resolved project configuration.
        output_dir: Root directory for generated output.

    Returns:
        Manifest dict with version info and file listing.
    """
    tracker = FileTracker(output_dir)
    all_files: list[str] = []

    # Run generators in dependency order (CLAUDE.md first since it's the
    # primary file, settings next for hooks, then everything else).
    all_files.extend(generate_claude_md(config, output_dir, tracker=tracker))
    all_files.extend(generate_settings(config, output_dir, tracker=tracker))
    all_files.extend(generate_agents(config, output_dir, tracker=tracker))
    all_files.extend(generate_commands(config, output_dir, tracker=tracker))
    all_files.extend(generate_skills(config, output_dir, tracker=tracker))
    all_files.extend(generate_agent_docs(config, output_dir, tracker=tracker))
    all_files.extend(generate_memory(config, output_dir, tracker=tracker))
    all_files.extend(generate_mcp(config, output_dir, tracker=tracker))
    all_files.extend(generate_harness(config, output_dir, tracker=tracker))
    all_files.extend(generate_addons(config, output_dir, tracker=tracker))
    all_files.extend(generate_misc(config, output_dir, tracker=tracker))
    all_files.extend(generate_claude_local(output_dir, tracker=tracker))

    # Include the manifest file itself in the file list
    manifest_rel = ".claude/.cc-rig-manifest.json"
    all_files.append(manifest_rel)

    manifest: dict[str, Any] = {
        "cc_rig_version": config.cc_rig_version or __version__,
        "template_preset": config.template_preset,
        "workflow_preset": config.workflow_preset,
        "files": sorted(all_files),
        "file_metadata": tracker.metadata(),
    }

    # Write manifest to .claude/.cc-rig-manifest.json
    manifest_dir = output_dir / ".claude"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / ".cc-rig-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    return manifest
