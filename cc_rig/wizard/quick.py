"""Quick picker: template + workflow selection (Screen 1b)."""

from __future__ import annotations

from cc_rig.presets.manager import (
    BUILTIN_TEMPLATES,
    BUILTIN_WORKFLOWS,
    load_workflow,
)
from cc_rig.ui.descriptions import TEMPLATE_DESCRIPTIONS
from cc_rig.ui.prompts import IO, ask_choice


def run_quick(io: IO) -> tuple[str, str]:
    """Run the quick template+workflow picker.

    Returns (template, workflow) tuple.
    """
    io.say("\n--- Quick Setup ---")

    # Template selection with descriptions
    template_options = [(t, TEMPLATE_DESCRIPTIONS.get(t, t)) for t in BUILTIN_TEMPLATES]
    template = ask_choice(
        "Select template:",
        template_options,
        "fastapi",
        io=io,
    )

    # Workflow selection with descriptions
    workflow_options = []
    for w in BUILTIN_WORKFLOWS:
        data = load_workflow(w)
        desc = data.get("description", w)
        agents = len(data.get("agents", []))
        commands = len(data.get("commands", []))
        label = f"{w} - {desc} ({agents} agents, {commands} cmds)"
        if w == "standard":
            label += " (recommended)"
        workflow_options.append((w, label))

    workflow = ask_choice(
        "Select workflow:",
        workflow_options,
        "standard",
        io=io,
    )

    return template, workflow
