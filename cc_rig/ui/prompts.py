"""Input helpers for wizard prompts.

Provides ask_choice, ask_input, confirm, and ask_multi with
pluggable IO for testing. Falls back gracefully when stdin is
not a TTY (piped input).
"""

from __future__ import annotations

import sys
from typing import Any, Callable


class IO:
    """Pluggable input/output for testability.

    Pass custom input_fn and print_fn to simulate user input
    in tests. Default uses builtin input() and print().
    """

    def __init__(
        self,
        input_fn: Callable[[str], str] | None = None,
        print_fn: Callable[..., Any] | None = None,
    ):
        self._input = input_fn or input
        self._print = print_fn or print

    def ask(self, prompt: str) -> str:
        """Read a line of input."""
        return self._input(prompt)

    def say(self, *args: Any, **kwargs: Any) -> None:
        """Print output."""
        self._print(*args, **kwargs)

    @property
    def is_tty(self) -> bool:
        """Check if stdin is a real terminal."""
        return hasattr(sys.stdin, "isatty") and sys.stdin.isatty()


_default_io = IO()


def ask_choice(
    prompt: str,
    options: list[tuple[str, str]],
    default: str | None = None,
    io: IO | None = None,
) -> str:
    """Ask user to pick one option from a numbered list.

    Args:
        prompt: Question to display.
        options: List of (value, label) tuples.
        default: Value returned on empty input.
        io: IO instance for testing.

    Returns:
        The selected value string.
    """
    io = io or _default_io
    io.say(f"\n{prompt}")
    for i, (value, label) in enumerate(options, 1):
        marker = " (default)" if value == default else ""
        io.say(f"  {i}. {label}{marker}")

    while True:
        try:
            raw = io.ask("> ").strip()
        except (EOFError, KeyboardInterrupt):
            if default:
                return default
            raise SystemExit(1)
        if not raw and default:
            return default
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        except ValueError:
            for value, _label in options:
                if raw.lower() == value.lower():
                    return value
        io.say("Invalid selection. Try again.")


def ask_input(
    prompt: str,
    default: str = "",
    io: IO | None = None,
) -> str:
    """Ask for free-text input with optional default.

    Returns:
        User input or default if empty.
    """
    io = io or _default_io
    suffix = f" [{default}]" if default else ""
    try:
        raw = io.ask(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return default
    return raw or default


def confirm(
    prompt: str,
    default: bool = True,
    io: IO | None = None,
) -> bool:
    """Ask a yes/no question.

    Returns:
        True for yes, False for no.
    """
    io = io or _default_io
    yn = "[Y/n]" if default else "[y/N]"
    try:
        raw = io.ask(f"{prompt} {yn} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if not raw:
        return default
    return raw in ("y", "yes")


def ask_multi(
    prompt: str,
    options: list[tuple[str, str]],
    defaults: list[str] | None = None,
    io: IO | None = None,
) -> list[str]:
    """Multi-select from a numbered list.

    Args:
        prompt: Question to display.
        options: List of (value, label) tuples.
        defaults: Pre-selected values (returned on empty input).
        io: IO instance for testing.

    Returns:
        List of selected value strings.
    """
    io = io or _default_io
    defaults = defaults or []
    io.say(f"\n{prompt}")
    io.say("  (Enter numbers separated by commas, or 'all'/'none')")
    for i, (value, label) in enumerate(options, 1):
        marker = " *" if value in defaults else ""
        io.say(f"  {i}. {label}{marker}")

    while True:
        try:
            raw = io.ask("> ").strip()
        except (EOFError, KeyboardInterrupt):
            return list(defaults)
        if not raw:
            return list(defaults)
        if raw.lower() == "all":
            return [v for v, _ in options]
        if raw.lower() == "none":
            return []
        try:
            indices = [int(x.strip()) - 1 for x in raw.split(",")]
            if all(0 <= i < len(options) for i in indices):
                return [options[i][0] for i in indices]
        except ValueError:
            pass
        io.say("Invalid selection. Try again.")
