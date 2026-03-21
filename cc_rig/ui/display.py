"""Output formatting for cc-rig CLI.

ANSI color codes with auto-detection. Falls back to plain text
when stdout is not a TTY or NO_COLOR is set.
"""

from __future__ import annotations

import os
import re
import sys

from cc_rig.config.project import ProjectConfig

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return _ANSI_RE.sub("", text)


def _use_color() -> bool:
    """Check if color output is appropriate."""
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


# ANSI codes (empty strings when color disabled)
if _use_color():
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    RESET = "\033[0m"
else:
    BOLD = DIM = GREEN = YELLOW = RED = CYAN = RESET = ""


def success(msg: str) -> str:
    """Format a success message."""
    return f"{GREEN}+{RESET} {msg}"


def warning(msg: str) -> str:
    """Format a warning message."""
    return f"{YELLOW}!{RESET} {msg}"


def error(msg: str) -> str:
    """Format an error message."""
    return f"{RED}x{RESET} {msg}"


def heading(msg: str) -> str:
    """Format a section heading."""
    return f"\n{BOLD}{msg}{RESET}"


def dim(msg: str) -> str:
    """Format dimmed text."""
    return f"{DIM}{msg}{RESET}"


def format_summary(config: ProjectConfig) -> str:
    """Format a ProjectConfig as a review summary.

    Uses rich formatting when available.
    """
    try:
        from cc_rig.ui.tui import HAS_RICH

        if HAS_RICH and _use_color():
            from cc_rig.ui.rich_tui import rich_format_summary

            return rich_format_summary(config)
    except ImportError:
        pass
    lines = [
        heading("Configuration preview"),
        "",
        f"  Project:    {BOLD}{config.project_name}{RESET}",
        f"  Stack:      {config.language} / {config.framework}",
        f"  Type:       {config.project_type}",
        f"  Workflow:   {BOLD}{config.workflow}{RESET}",
        "",
        f"  Agents:     {len(config.agents)}",
        f"  Commands:   {len(config.commands)}",
        f"  Hooks:      {len(config.hooks)}",
        f"  Skills:     {len(config.recommended_skills)}",
        f"  Process:    {len(config.process_skills)} ({config.workflow_source})"
        if config.process_skills
        else "  Process:    0",
        f"  Plugins:    {len(config.recommended_plugins)}",
        f"  MCPs:       {len(config.default_mcps)}",
        "",
        "  Features:",
    ]
    if config.features.memory:
        lines.append("    - Memory system")
    if config.features.spec_workflow:
        lines.append("    - Spec workflow")
    if config.features.gtd:
        lines.append("    - GTD task management")
    if config.features.worktrees:
        lines.append("    - Git worktrees")
    lines.append("")
    return "\n".join(lines)


def format_file_list(files: list[str]) -> str:
    """Format a list of generated files with checkmarks.

    Uses rich tree when available.
    """
    try:
        from cc_rig.ui.tui import HAS_RICH

        if HAS_RICH and _use_color():
            from cc_rig.ui.rich_tui import rich_format_file_list

            return rich_format_file_list(files)
    except ImportError:
        pass
    lines = []
    for f in sorted(files):
        lines.append(f"  {GREEN}+{RESET} {f}")
    return "\n".join(lines)
