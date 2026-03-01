"""Harness choice screen (Screen 7) — B0-B3 + custom selection."""

from __future__ import annotations

from cc_rig.config.project import HarnessConfig
from cc_rig.ui.prompts import IO, ask_choice, confirm

AUTONOMY_WARNING_LINES = [
    "  ================================================",
    "  WARNING: AUTONOMOUS OPERATION MODE (B3)",
    "  Claude will iterate through tasks without",
    "  human intervention. Safety rails will be active.",
    "  loop.sh uses --dangerously-skip-permissions.",
    "  Run inside a Docker container or sandbox.",
    "  ================================================",
]


def ask_harness(io: IO) -> HarnessConfig:
    """Prompt the user to choose a harness level.

    Returns a HarnessConfig with the selected level.
    """
    options = [
        ("none", "None - scaffold only, you drive (B0)"),
        ("lite", "Lite - task tracking + budget awareness (B1)"),
        (
            "standard",
            "Standard - enforcement gates + init-sh.sh (B2)",
        ),
        (
            "autonomy",
            "Autonomy - autonomous iteration with safety rails (B3)",
        ),
        (
            "custom",
            "Custom - pick individual features",
        ),
    ]

    level = ask_choice(
        "Runtime harness level:",
        options,
        default="none",
        io=io,
    )

    if level == "custom":
        return _ask_custom_harness(io)

    if level == "autonomy":
        io.say("")
        for line in AUTONOMY_WARNING_LINES:
            io.say(line)
        io.say("")
        try:
            response = io.ask('  Type "I understand" to confirm: ').strip()
        except (EOFError, KeyboardInterrupt):
            io.say("\nCancelled.")
            return HarnessConfig(level="none")
        if response.lower() != "i understand":
            io.say("  Cancelled. Autonomy mode not enabled.")
            return HarnessConfig(level="none")

    return HarnessConfig(level=level)


def _ask_custom_harness(io: IO) -> HarnessConfig:
    """Prompt for individual harness feature flags."""
    io.say("\n  Pick individual harness features:")

    task_tracking = confirm(
        "  Task tracking? (todo.md + session-tasks hook)",
        default=True,
        io=io,
    )
    budget_awareness = confirm(
        "  Budget awareness? (budget-reminder hook)",
        default=True,
        io=io,
    )
    verification_gates = confirm(
        "  Verification gates? (commit-gate hook + init-sh.sh)",
        default=False,
        io=io,
    )
    autonomy_loop = confirm(
        "  Autonomy loop? (PROMPT.md + loop.sh)",
        default=False,
        io=io,
    )

    if autonomy_loop:
        io.say("")
        for line in AUTONOMY_WARNING_LINES:
            io.say(line)
        io.say("")
        try:
            response = io.ask('  Type "I understand" to confirm: ').strip()
        except (EOFError, KeyboardInterrupt):
            io.say("\nCancelled.")
            autonomy_loop = False
        else:
            if response.lower() != "i understand":
                io.say("  Cancelled. Autonomy loop not enabled.")
                autonomy_loop = False

    return HarnessConfig(
        level="custom",
        task_tracking=task_tracking,
        budget_awareness=budget_awareness,
        verification_gates=verification_gates,
        autonomy_loop=autonomy_loop,
    )
