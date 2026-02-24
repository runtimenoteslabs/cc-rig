"""ASCII art banner for cc-rig."""

from __future__ import annotations

from typing import Any, Callable

BANNER = r"""
                        _
   ___ ___   _ __ (_) __ _
  / __/ __| | '__|| |/ _` |
 | (_| (__  | |   | | (_| |
  \___\___| |_|   |_|\__, |
                      |___/
"""

TAGLINE = "Project setup generator for Claude Code"


def print_banner(print_fn: Callable[..., Any] | None = None) -> None:
    """Print the cc-rig banner."""
    out = print_fn or print
    out(BANNER.strip())
    out(TAGLINE)
    out("")
