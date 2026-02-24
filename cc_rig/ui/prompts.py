"""Input helpers for wizard prompts.

Provides ask_choice, ask_input, confirm, and ask_multi with
pluggable IO for testing. Falls back gracefully when stdin is
not a TTY (piped input).

When rich is available and the caller is using real IO (not
test-injected), prompts automatically use rich inline styling
for colored output while keeping standard input().
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


def _bold(text: str) -> str:
    """Wrap text in ANSI bold if stdout supports color."""
    try:
        from cc_rig.ui.display import BOLD, RESET

        if BOLD:
            return f"{BOLD}{text}{RESET}"
    except ImportError:
        pass
    return text


# Lazy-loaded sentinel — avoids circular import at module level.
_BACK_SENTINEL: object | None = None


def _get_back() -> object:
    """Return the BACK sentinel, importing lazily."""
    global _BACK_SENTINEL
    if _BACK_SENTINEL is None:
        from cc_rig.wizard.stepper import BACK

        _BACK_SENTINEL = BACK
    return _BACK_SENTINEL


def _is_back_input(raw: str) -> bool:
    """Check if user typed 'back'."""
    return raw.strip().lower() == "back"


# ── Rich dispatch helpers ─────────────────────────────────────────


def _should_use_rich(io: IO | None) -> bool:
    """Return True when we should delegate to rich inline prompts.

    Rich prompts are only used when the IO is real (not test-injected)
    and rich is installed. Tests always use the ANSI path.
    """
    # Test-injected IO uses custom input/print functions — skip rich.
    if io is not None and (io._input is not input or io._print is not print):
        return False
    if not (hasattr(sys.stdin, "isatty") and sys.stdin.isatty()):
        return False
    try:
        from cc_rig.ui.rich_prompts import RICH_PROMPTS_AVAILABLE

        return RICH_PROMPTS_AVAILABLE
    except ImportError:
        return False


# ── Public API ────────────────────────────────────────────────────


def ask_choice(
    prompt: str,
    options: list[tuple[str, str]],
    default: str | None = None,
    io: IO | None = None,
    allow_back: bool = False,
) -> str:
    """Ask user to pick one option from a numbered list.

    Args:
        prompt: Question to display.
        options: List of (value, label) tuples.
        default: Value returned on empty input.
        io: IO instance for testing.
        allow_back: If True, typing "back" returns the BACK sentinel.

    Returns:
        The selected value string (or BACK sentinel).
    """
    if _should_use_rich(io):
        from cc_rig.ui.rich_prompts import rich_ask_choice

        return rich_ask_choice(prompt, options, default=default, allow_back=allow_back)

    io = io or _default_io
    back_hint = '  (Type "back" to go back)' if allow_back else ""
    io.say(f"\n{prompt}")
    for i, (value, label) in enumerate(options, 1):
        if value == default:
            io.say(f"  {i}. {_bold(label)} (default)")
        else:
            io.say(f"  {i}. {label}")
    if back_hint:
        io.say(back_hint)

    while True:
        try:
            raw = io.ask("> ").strip()
        except KeyboardInterrupt:
            raise SystemExit(130)
        except EOFError:
            if default:
                return default
            raise SystemExit(1)
        if allow_back and _is_back_input(raw):
            return _get_back()  # type: ignore[return-value]
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
    allow_back: bool = False,
    require_explicit: bool = False,
) -> str:
    """Ask for free-text input with optional default.

    Args:
        require_explicit: If True, reject empty input even when a default
            is set.  Forces the user to type something (or the default
            value explicitly) before the prompt accepts.
        allow_back: If True, typing "back" returns the BACK sentinel.

    Returns:
        User input, default if empty, or BACK sentinel.
    """
    if _should_use_rich(io):
        from cc_rig.ui.rich_prompts import rich_ask_input

        return rich_ask_input(
            prompt, default=default, allow_back=allow_back, require_explicit=require_explicit
        )

    io = io or _default_io
    suffix = f" [{_bold(default)}]" if default else ""
    back_hint = ' (or "back")' if allow_back else ""

    while True:
        try:
            raw = io.ask(f"{prompt}{suffix}{back_hint}: ").strip()
        except KeyboardInterrupt:
            raise SystemExit(130)
        except EOFError:
            return default
        if allow_back and _is_back_input(raw):
            return _get_back()  # type: ignore[return-value]
        if require_explicit and not raw:
            io.say(f"  Please enter a value{f' (default: {default})' if default else ''}.")
            continue
        return raw or default


def confirm(
    prompt: str,
    default: bool = True,
    io: IO | None = None,
    allow_back: bool = False,
) -> bool:
    """Ask a yes/no question.

    Returns:
        True for yes, False for no (or BACK sentinel).
    """
    if _should_use_rich(io):
        from cc_rig.ui.rich_prompts import rich_confirm

        return rich_confirm(prompt, default=default, allow_back=allow_back)

    io = io or _default_io
    yn = "[Y/n]" if default else "[y/N]"
    back_hint = ' (or "back")' if allow_back else ""
    try:
        raw = io.ask(f"{prompt} {yn}{back_hint} ").strip().lower()
    except KeyboardInterrupt:
        raise SystemExit(130)
    except EOFError:
        return default
    if allow_back and _is_back_input(raw):
        return _get_back()  # type: ignore[return-value]
    if not raw:
        return default
    return raw in ("y", "yes")


def ask_multi(
    prompt: str,
    options: list[tuple[str, str]],
    defaults: list[str] | None = None,
    io: IO | None = None,
    allow_back: bool = False,
) -> list[str]:
    """Multi-select from a numbered list.

    Args:
        prompt: Question to display.
        options: List of (value, label) tuples.
        defaults: Pre-selected values (returned on empty input).
        io: IO instance for testing.
        allow_back: If True, typing "back" returns the BACK sentinel.

    Returns:
        List of selected value strings (or BACK sentinel).
    """
    if _should_use_rich(io):
        from cc_rig.ui.rich_prompts import rich_ask_multi

        return rich_ask_multi(prompt, options, defaults=defaults, allow_back=allow_back)

    io = io or _default_io
    defaults = defaults or []
    back_hint = ', or "back"' if allow_back else ""
    io.say(f"\n{prompt}")
    io.say(f"  (Enter numbers separated by commas, or 'all'/'none'{back_hint})")
    for i, (value, label) in enumerate(options, 1):
        marker = " *" if value in defaults else ""
        io.say(f"  {i}. {label}{marker}")

    while True:
        try:
            raw = io.ask("> ").strip()
        except KeyboardInterrupt:
            raise SystemExit(130)
        except EOFError:
            return list(defaults)
        if allow_back and _is_back_input(raw):
            return _get_back()  # type: ignore[return-value]
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
