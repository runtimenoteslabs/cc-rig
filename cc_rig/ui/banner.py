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

BANNER_COMPACT = "cc-rig"

TAGLINE = "Project setup generator for Claude Code"


def print_banner(print_fn: Callable[..., Any] | None = None) -> None:
    """Print the cc-rig banner. Uses rich Panel when available."""
    if print_fn is None:
        try:
            from cc_rig.ui.tui import HAS_RICH

            if HAS_RICH:
                from cc_rig.ui.rich_tui import rich_print_banner

                rich_print_banner()
                return
        except ImportError:
            pass
    out = print_fn or print
    out(BANNER.strip())
    out(TAGLINE)
    out("")
