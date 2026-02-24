"""Rich-styled inline prompts (optional dependency).

Uses ``rich.console.Console`` for colorful output while keeping
standard ``input()`` for reading — prompts stay inline in the
scrollback, no alternate-screen takeover.

Install: ``pip install cc-rig[rich]``
"""

from __future__ import annotations

from typing import Any

# ── Availability flag ─────────────────────────────────────────────

try:
    from rich.console import Console

    RICH_PROMPTS_AVAILABLE = True
except ImportError:
    RICH_PROMPTS_AVAILABLE = False


def _get_back() -> Any:
    from cc_rig.wizard.stepper import BACK

    return BACK


def _console() -> Console:
    return Console(highlight=False)


# ── Public prompt functions ───────────────────────────────────────


def rich_ask_choice(
    prompt: str,
    options: list[tuple[str, str]],
    default: str | None = None,
    allow_back: bool = False,
) -> str:
    """Inline numbered list with rich styling."""
    con = _console()
    con.print(f"\n[bold]{prompt}[/]")
    for i, (value, label) in enumerate(options, 1):
        if value == default:
            con.print(f"  [cyan]{i}.[/] [bold]{label}[/] [dim](default)[/]")
        else:
            con.print(f"  [cyan]{i}.[/] {label}")
    if allow_back:
        con.print('  [dim](Type "back" to go back)[/]')

    while True:
        try:
            raw = input("> ").strip()
        except KeyboardInterrupt:
            raise SystemExit(130)
        except EOFError:
            if default:
                return default
            raise SystemExit(1)
        if allow_back and raw.lower() == "back":
            return _get_back()
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
        con.print("[yellow]Invalid selection. Try again.[/]")


def rich_ask_multi(
    prompt: str,
    options: list[tuple[str, str]],
    defaults: list[str] | None = None,
    allow_back: bool = False,
) -> list[str]:
    """Inline multi-select with rich styling."""
    con = _console()
    defaults = defaults or []
    back_hint = ', or "back"' if allow_back else ""
    con.print(f"\n[bold]{prompt}[/]")
    con.print(f"  [dim](Enter numbers separated by commas, or 'all'/'none'{back_hint})[/]")
    for i, (value, label) in enumerate(options, 1):
        marker = " [green]*[/]" if value in defaults else ""
        con.print(f"  [cyan]{i}.[/] {label}{marker}")

    while True:
        try:
            raw = input("> ").strip()
        except KeyboardInterrupt:
            raise SystemExit(130)
        except EOFError:
            return list(defaults)
        if allow_back and raw.lower() == "back":
            return _get_back()
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
        con.print("[yellow]Invalid selection. Try again.[/]")


def rich_ask_input(
    prompt: str,
    default: str = "",
    allow_back: bool = False,
    require_explicit: bool = False,
) -> str:
    """Inline text input with rich-styled prompt."""
    con = _console()
    suffix = f" [dim]\\[[/][bold cyan]{default}[/][dim]][/]" if default else ""
    back_hint = ' [dim](or "back")[/]' if allow_back else ""

    while True:
        con.print(f"{prompt}{suffix}{back_hint}: ", end="")
        try:
            raw = input("").strip()
        except KeyboardInterrupt:
            raise SystemExit(130)
        except EOFError:
            return default
        if allow_back and raw.lower() == "back":
            return _get_back()
        if require_explicit and not raw:
            msg = "Please enter a value"
            if default:
                msg += f" (default: {default})"
            con.print(f"  [yellow]{msg}.[/]")
            continue
        return raw or default


def rich_confirm(
    prompt: str,
    default: bool = True,
    allow_back: bool = False,
) -> bool:
    """Inline Y/N confirm with rich styling."""
    con = _console()
    if default:
        yn = "[bold]Y[/]/n"
    else:
        yn = "y/[bold]N[/]"
    back_hint = ' [dim](or "back")[/]' if allow_back else ""
    con.print(f"{prompt} [{yn}]{back_hint} ", end="")
    try:
        raw = input("").strip().lower()
    except KeyboardInterrupt:
        raise SystemExit(130)
    except EOFError:
        return default
    if allow_back and raw == "back":
        return _get_back()
    if not raw:
        return default
    return raw in ("y", "yes")
