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
from cc_rig.ui.descriptions import TEMPLATE_DESCRIPTIONS
from cc_rig.ui.prompts import IO, ask_choice, ask_input, confirm
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

    # Interactive flows: confirm output directory when not explicitly set.
    # Skip this when the Textual TUI will handle it (output dir shown in ConfirmScreen).
    if not output_arg and not in_place:
        from cc_rig.ui.tui import should_use_textual

        if not should_use_textual(io):
            output_dir = _confirm_output_dir(output_dir, io)
            if output_dir is None:
                return 0

    # Quick picker
    if getattr(args, "quick", False):
        return _quick_flow(name, output_dir, io)

    # A2: Expert (runs guided then expert customizer)
    expert = getattr(args, "expert", False)

    # A1: Guided (default) — starts with launcher
    return _guided_flow(name, output_dir, io, expert=expert)


def _confirm_output_dir(output_dir: Path, io: IO) -> Path | None:
    """Confirm or change the output directory for interactive flows.

    Returns the confirmed Path, or None if the user cancels.
    """
    cwd = Path(".").resolve()
    if output_dir == cwd and any(cwd.iterdir()):
        io.say(f"\nOutput directory: {output_dir}")
        raw = ask_input(
            "Generate here? Enter a different path or press Enter to confirm",
            default=str(output_dir),
            io=io,
        )
        if not raw:
            return None
        return Path(raw).resolve()
    return output_dir


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

    if detected.framework:
        io.say(f"  Detected: {detected.language} / {detected.framework}")
        template = detected.framework
    else:
        lang_msg = f" (detected language: {detected.language})" if detected.language else ""
        io.say(f"  Could not auto-detect framework{lang_msg}.")
        io.say("  Select a template manually:\n")
        template = _ask_template(io)

    workflow = _ask_workflow(io)

    io.say(f"\n  Proposed: template={template}, workflow={workflow}")
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
    from cc_rig.ui.tui import should_use_textual

    if should_use_textual(io):
        return _quick_flow_textual(name, output_dir, io)

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
    """Full guided wizard (A1) with optional expert mode (A2).

    Uses Textual TUI when available, otherwise falls back to StepRunner.
    """
    from cc_rig.ui.tui import should_use_textual

    if should_use_textual(io):
        return _guided_flow_textual(name, output_dir, io, expert=expert)

    from cc_rig.ui.banner import print_banner
    from cc_rig.wizard.stepper import StepAction, StepRunner
    from cc_rig.wizard.steps import (
        BasicsStep,
        ConfirmStep,
        ExpertStep,
        HarnessStep,
        ReviewStep,
        SkillPacksStep,
        TemplateStep,
        WorkflowStep,
    )

    print_banner(io.say)

    # Screen 1: Launcher (handled outside StepRunner since it can
    # redirect to completely different flows)
    from cc_rig.wizard.launcher import run_launcher

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

    # mode == "fresh" — run through step-based guided flow
    steps = [
        BasicsStep(),
        TemplateStep(),
        WorkflowStep(),
        ReviewStep(),
        ExpertStep(),
        SkillPacksStep(),
        HarnessStep(),
        ConfirmStep(),
    ]

    initial_state = {
        "name": name,
        "output_dir": output_dir,
        "force_expert": expert,
    }

    runner = StepRunner(steps, io)
    action, state = runner.run(initial_state)

    if action == StepAction.CANCEL:
        return 0

    config = state.get("config")
    if config is None:
        io.say("No configuration built.")
        return 1

    return run_generation(config, output_dir, io)


def _guided_flow_textual(
    name: str,
    output_dir: Path,
    io: IO,
    expert: bool = False,
) -> int:
    """Run the guided flow using the Textual full-screen TUI."""
    from cc_rig.ui.textual_wizard import WizardApp

    initial_state = {
        "name": name,
        "output_dir": output_dir,
        "force_expert": expert,
    }

    app = WizardApp(initial_state=initial_state)
    state = app.run()

    if state is None:
        io.say("Cancelled.")
        return 0

    final_output_dir = Path(state.get("output_dir", output_dir))

    # Handle launcher modes that exit the TUI for CLI input
    mode = state.get("launcher_mode", "fresh")
    if mode == "config":
        config_name = ask_input("Config name or path", "", io=io)
        if config_name:
            return _config_load(config_name, name, final_output_dir, io)
        io.say("No config specified.")
        return 1
    if mode == "file":
        file_path = ask_input("Path to .json config file", "", io=io)
        if file_path:
            return _config_load(file_path, name, final_output_dir, io)
        io.say("No file specified.")
        return 1

    config = state.get("config")
    if config is None:
        io.say("No configuration built.")
        return 1

    return run_generation(config, final_output_dir, io)


def _quick_flow_textual(
    name: str,
    output_dir: Path,
    io: IO,
) -> int:
    """Run the quick flow using the Textual full-screen TUI."""
    from cc_rig.ui.textual_wizard import QuickWizardApp

    initial_state = {
        "name": name or "",
        "output_dir": output_dir,
    }

    app = QuickWizardApp(initial_state=initial_state)
    state = app.run()

    if state is None:
        io.say("Cancelled.")
        return 0

    config = state.get("config")
    if config is None:
        io.say("No configuration built.")
        return 1

    final_output_dir = Path(state.get("output_dir", output_dir))
    return run_generation(config, final_output_dir, io)


def run_update_wizard(
    project_dir: Path,
    io: IO | None = None,
    expert: bool = False,
    quick: bool = False,
) -> int:
    """Re-run wizard with existing config values pre-filled.

    Loads .cc-rig.json, runs wizard with defaults from current config,
    shows diff, and regenerates on confirmation.
    """
    io = io or IO()

    config_path = project_dir / ".cc-rig.json"
    if not config_path.exists():
        io.say("No .cc-rig.json found. Run 'cc-rig init' first.")
        return 1

    import json as _json

    try:
        old_config = ProjectConfig.from_json(config_path.read_text())
    except (_json.JSONDecodeError, KeyError, TypeError) as exc:
        io.say(f"Error loading .cc-rig.json: {exc}")
        return 1

    # Check for locked config
    old_data = _json.loads(config_path.read_text())
    if old_data.get("locked"):
        io.say("Config is locked. Run 'cc-rig config unlock' first.")
        return 1

    io.say(f"\nUpdating: {old_config.project_name}")
    io.say(f"  Current: {old_config.template_preset} + {old_config.workflow_preset}")
    io.say("")

    if quick:
        # Quick mode: just re-pick template + workflow
        template = _ask_template(io)
        workflow = _ask_workflow(io)
    else:
        # Guided: let user change template and workflow
        io.say("Press Enter to keep current value, or select a new one.\n")
        template = _ask_template_with_default(io, old_config.template_preset or "fastapi")
        workflow = _ask_workflow_with_default(io, old_config.workflow or "standard")

    name = old_config.project_name

    try:
        new_config = compute_defaults(
            template,
            workflow,
            project_name=name,
            output_dir=str(project_dir),
        )
    except (KeyError, ValueError) as exc:
        io.say(f"Error: {exc}")
        return 1

    # Show diff
    from cc_rig.config.manager import diff_configs

    diff = diff_configs(old_config, new_config)
    if diff:
        io.say("\nChanges from current config:")
        io.say(diff)
        io.say("")
    else:
        io.say("\nNo changes detected.")
        return 0

    from cc_rig.ui.prompts import confirm as _confirm

    if not _confirm("Regenerate?", io=io):
        io.say("Cancelled.")
        return 0

    return run_generation(new_config, project_dir, io)


def _ask_template_with_default(io: IO, current: str) -> str:
    """Prompt user to select a template with a default from existing config."""
    options = [(t, TEMPLATE_DESCRIPTIONS.get(t, t)) for t in BUILTIN_TEMPLATES]
    return ask_choice(
        f"Select template (current: {current}):",
        options,
        current,
        io=io,
    )


def _ask_workflow_with_default(io: IO, current: str) -> str:
    """Prompt user to select a workflow with a default from existing config."""
    descriptions = {}
    for w in BUILTIN_WORKFLOWS:
        data = load_workflow(w)
        descriptions[w] = data.get("description", w)
    options = [(w, f"{w} - {descriptions[w]}") for w in BUILTIN_WORKFLOWS]
    return ask_choice(
        f"Select workflow (current: {current}):",
        options,
        current,
        io=io,
    )


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
    options = [(w, f"{w} - {descriptions[w]}") for w in BUILTIN_WORKFLOWS]
    return ask_choice("Select workflow:", options, "standard", io=io)
