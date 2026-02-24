"""Harness choice screen (Screen 7) — B0-B3 selection."""

from __future__ import annotations

from cc_rig.config.project import HarnessConfig
from cc_rig.ui.prompts import IO, ask_choice

AUTONOMY_WARNING_LINES = [
    "  ================================================",
    "  WARNING: AUTONOMOUS OPERATION MODE (B3)",
    "  Claude will iterate through tasks without",
    "  human intervention. Safety rails will be active.",
    "  ================================================",
]


def ask_harness(io: IO) -> HarnessConfig:
    """Prompt the user to choose a harness level.

    Returns a HarnessConfig with the selected level.
    """
    options = [
        ("none", "None — scaffold only, you drive (B0)"),
        ("lite", "Lite — task tracking + budget awareness (B1)"),
        (
            "standard",
            "Standard — + verification gates + review notes (B2)",
        ),
        (
            "autonomy",
            "Autonomy — autonomous iteration with safety rails (B3)",
        ),
    ]

    level = ask_choice(
        "Runtime harness level:",
        options,
        default="none",
        io=io,
    )

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
        if response != "I understand":
            io.say("  Cancelled. Autonomy mode not enabled.")
            return HarnessConfig(level="none")

    return HarnessConfig(level=level)
