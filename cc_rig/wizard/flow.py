"""Main wizard flow — routes to the right setup path.

Entry points:
  A0: zero-config  (--template X --workflow Y)
  A1: guided       (cc-rig init, interactive)
  A1: quick        (--quick, template+workflow picker)
  A2: expert       (--expert, full customization)
  A3: config-load  (--config X)
  migrate          (--migrate)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cc_rig.config.defaults import compute_defaults
from cc_rig.config.detection import detect_project
from cc_rig.config.project import ProjectConfig
from cc_rig.presets.manager import (
    BUILTIN_TEMPLATES,
    BUILTIN_WORKFLOWS,
    load_workflow,
)
from cc_rig.ui.prompts import IO, ask_choice, ask_input, confirm
from cc_rig.wizard.expert import run_expert
from cc_rig.wizard.generate import run_generation
from cc_rig.wizard.quick import run_quick


def run_wizard(args: argparse.Namespace, io: IO | None = None) -> int:
    """Top-level wizard dispatcher. Returns exit code."""
    io = io or IO()

    in_place = getattr(args, "in_place", False)
    output_arg = getattr(args, "output", None)
    if in_place:
        output_dir = Path(".").resolve()
    else:
        output_dir = Path(output_arg or ".").resolve()
    name = getattr(args, "name", None) or ""

    # A0: Zero-config — template + workflow on CLI
    template = getattr(args, "template", None)
    workflow = getattr(args, "workflow", None)

    # Validate CLI args early (before falling through to guided flow)
    if template and template not in BUILTIN_TEMPLATES:
        available = ", ".join(sorted(BUILTIN_TEMPLATES))
        io.say(f"Error: Unknown template: {template!r}. Available: {available}")
        return 1
    if workflow and workflow not in BUILTIN_WORKFLOWS:
        available = ", ".join(sorted(BUILTIN_WORKFLOWS))
        io.say(f"Error: Unknown workflow: {workflow!r}. Available: {available}")
        return 1

    if template and workflow:
        return _zero_config(template, workflow, name, output_dir, io)

    # A3: Config load
    config_path = getattr(args, "config", None)
    if config_path:
        return _config_load(config_path, name, output_dir, io)

    # Migrate
    if getattr(args, "migrate", False):
        return _migrate(name, output_dir, io)

    # Quick picker
    if getattr(args, "quick", False):
        return _quick_flow(name, output_dir, io)

    # A2: Expert (runs guided then expert customizer)
    expert = getattr(args, "expert", False)

    # A1: Guided (default) — starts with launcher
    return _guided_flow(name, output_dir, io, expert=expert)


def _zero_config(
    template: str,
    workflow: str,
    name: str,
    output_dir: Path,
    io: IO,
) -> int:
    """A0: Direct generation with no prompts."""
    name = name or output_dir.name
    try:
        config = compute_defaults(
            template,
            workflow,
            project_name=name,
            output_dir=str(output_dir),
        )
    except (KeyError, ValueError) as exc:
        io.say(f"Error: {exc}")
        return 1
    return run_generation(config, output_dir, io)


def _config_load(
    config_path: str,
    name: str,
    output_dir: Path,
    io: IO,
) -> int:
    """A3: Load a saved config and generate."""
    path = Path(config_path)
    if not path.exists():
        io.say(f"Error: config file not found: {config_path}")
        return 1
    try:
        data = json.loads(path.read_text())
        config = ProjectConfig.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        io.say(f"Error loading config: {exc}")
        return 1

    if name:
        config.project_name = name
    config.output_dir = str(output_dir)

    io.say(f"Loaded config: {config.template_preset} + {config.workflow_preset}")
    io.say(f"  Project: {config.project_name}")
    io.say(f"  Output:  {output_dir}")

    return run_generation(config, output_dir, io)


def _migrate(
    name: str,
    output_dir: Path,
    io: IO,
) -> int:
    """Scan existing repo and propose a setup."""
    io.say("Scanning project directory...")
    detected = detect_project(output_dir)

    if not detected.framework:
        io.say("Could not detect framework. Use --template to specify manually.")
        return 1

    io.say(f"  Detected: {detected.language} / {detected.framework}")
    template = detected.framework
    workflow = "standard"

    io.say(f"  Proposed: template={template}, workflow={workflow}")
    if not confirm("Apply this setup?", io=io):
        io.say("Cancelled.")
        return 0

    name = name or output_dir.name
    config = compute_defaults(
        template,
        workflow,
        project_name=name,
        output_dir=str(output_dir),
    )
    return run_generation(config, output_dir, io)


def _quick_flow(
    name: str,
    output_dir: Path,
    io: IO,
) -> int:
    """Quick picker: template + workflow, then generate."""
    template, workflow = run_quick(io)
    name = name or ask_input("Project name", output_dir.name, io=io)
    config = compute_defaults(
        template,
        workflow,
        project_name=name,
        output_dir=str(output_dir),
    )
    return run_generation(config, output_dir, io)


def _guided_flow(
    name: str,
    output_dir: Path,
    io: IO,
    expert: bool = False,
) -> int:
    """Full guided wizard (A1) with optional expert mode (A2)."""
    from cc_rig.ui.banner import print_banner
    from cc_rig.wizard.harness import ask_harness
    from cc_rig.wizard.launcher import run_launcher

    print_banner(io.say)

    # Screen 1: Launcher (5 options)
    mode = run_launcher(io)

    if mode == "quick":
        return _quick_flow(name, output_dir, io)
    if mode == "config":
        config_name = ask_input("Config name or path", "", io=io)
        if config_name:
            return _config_load(config_name, name, output_dir, io)
        io.say("No config specified.")
        return 1
    if mode == "file":
        file_path = ask_input("Path to .json config file", "", io=io)
        if file_path:
            return _config_load(file_path, name, output_dir, io)
        io.say("No file specified.")
        return 1
    if mode == "migrate":
        return _migrate(name, output_dir, io)

    # mode == "fresh" — continue with full guided flow

    # Screen 2: Basics
    name = name or ask_input("Project name", output_dir.name, io=io)
    desc = ask_input("Description (optional)", "", io=io)

    # Screen 3: Stack detection
    detected = detect_project(output_dir)
    template = None
    if detected.framework:
        io.say(f"\nDetected: {detected.language} / {detected.framework}")
        if confirm(f"Use {detected.framework}?", io=io):
            template = detected.framework

    if not template:
        template = _ask_template(io)

    # Screen 4: Workflow
    workflow = _ask_workflow(io)

    # Build config from defaults
    config = compute_defaults(
        template,
        workflow,
        project_name=name,
        project_desc=desc,
        output_dir=str(output_dir),
    )

    # Screen 5: Review
    from cc_rig.ui.display import format_summary

    io.say(format_summary(config))

    # Expert mode (A2)
    if expert or confirm("Customize?", default=False, io=io):
        config = run_expert(config, io)

    # Screen 7: Harness choice
    if confirm("Add runtime harness?", default=False, io=io):
        config.harness = ask_harness(io)

    # Screen 8: Confirm and generate
    if not confirm("Generate?", io=io):
        io.say("Cancelled.")
        return 0

    return run_generation(config, output_dir, io)


def _ask_template(io: IO) -> str:
    """Prompt user to select a template."""
    options = [(t, t) for t in BUILTIN_TEMPLATES]
    return ask_choice("Select template:", options, "fastapi", io=io)


def _ask_workflow(io: IO) -> str:
    """Prompt user to select a workflow."""
    descriptions = {}
    for w in BUILTIN_WORKFLOWS:
        data = load_workflow(w)
        descriptions[w] = data.get("description", w)
    options = [(w, f"{w} — {descriptions[w]}") for w in BUILTIN_WORKFLOWS]
    return ask_choice("Select workflow:", options, "standard", io=io)
