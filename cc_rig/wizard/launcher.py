"""Launcher screen (Screen 1) — 5 entry point options."""

from __future__ import annotations

from cc_rig.ui.prompts import IO, ask_choice


def run_launcher(io: IO) -> str:
    """Show the launcher screen and return the selected mode.

    Returns one of: "fresh", "quick", "config", "file", "migrate".
    """
    options = [
        ("fresh", "Fresh project — full guided setup"),
        ("quick", "Template picker — pick template + workflow"),
        ("config", "Load saved config — reuse a previous setup"),
        ("file", "Load config file — from a .json path"),
        ("migrate", "Apply to existing repo — scan and propose"),
    ]

    return ask_choice(
        "How would you like to start?",
        options,
        default="fresh",
        io=io,
    )
