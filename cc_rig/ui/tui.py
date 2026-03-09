"""TUI auto-detection: stdlib ANSI (default) → rich (if installed).

This module provides the TUI capability detection layer.
Zero runtime dependencies — `rich` and `textual` are optional
extras that enhance the experience when available.

Usage:
    from cc_rig.ui.tui import get_tui_backend, TUI_BACKEND

    if TUI_BACKEND == "rich":
        # rich is available for enhanced formatting
    elif TUI_BACKEND == "ansi":
        # stdlib ANSI codes (default)
    else:
        # plain text (no TTY or NO_COLOR)
"""

from __future__ import annotations

import os
import sys


def _detect_backend() -> str:
    """Detect the best available TUI backend.

    Priority:
      1. "rich" — if rich is installed and stdout is a TTY
      2. "ansi" — if stdout is a TTY (stdlib ANSI codes)
      3. "plain" — no color (piped, NO_COLOR, dumb terminal)
    """
    # No color if explicitly disabled
    if os.environ.get("NO_COLOR"):
        return "plain"

    # No color if not a TTY
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return "plain"

    # Dumb terminal
    if os.environ.get("TERM") == "dumb":
        return "plain"

    # Try rich
    if _has_rich():
        return "rich"

    return "ansi"


def _has_rich() -> bool:
    """Check if rich is importable."""
    try:
        import rich  # noqa: F401

        return True
    except ImportError:
        return False


def _has_textual() -> bool:
    """Check if textual is importable."""
    try:
        import textual  # noqa: F401

        return True
    except ImportError:
        return False


def _has_prompt_toolkit() -> bool:
    """Check if prompt_toolkit is importable."""
    try:
        import prompt_toolkit  # noqa: F401

        return True
    except ImportError:
        return False


def get_tui_backend() -> str:
    """Return the detected TUI backend name.

    Returns:
        "rich", "ansi", or "plain"
    """
    return _detect_backend()


# Module-level cached values for consumers that import directly.
TUI_BACKEND = _detect_backend()
HAS_RICH = _has_rich()
HAS_TEXTUAL = _has_textual()
HAS_PROMPT_TOOLKIT = _has_prompt_toolkit()


def should_use_textual(io: object = None) -> bool:
    """Check if we should use the Textual TUI.

    Returns True when:
      - textual is importable
      - stdout is a TTY
      - io is not a test-injected IO object

    This function lives here (not in textual_wizard.py) so it can be
    imported without triggering textual's top-level imports.
    """
    if not HAS_TEXTUAL:
        return False

    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False

    # Don't use Textual if io has been injected (test mode)
    if io is not None:
        from cc_rig.ui.prompts import IO

        if isinstance(io, IO) and io._input is not input:
            return False

    return True
