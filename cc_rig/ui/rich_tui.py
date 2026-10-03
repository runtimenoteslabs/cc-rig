"""Rich-enhanced TUI functions (optional dependency).

This module is only imported when `rich` is installed.
It provides enhanced versions of the stdlib display functions
with better formatting, tables, and progress indicators.

Install: pip install cc-rig[rich]
"""

from __future__ import annotations

from typing import Any


def rich_print_banner() -> None:
    """Print the cc-rig banner with rich formatting."""
    from rich.console import Console
    from rich.panel import Panel

    from cc_rig.ui.banner import BANNER, TAGLINE

    console = Console()
    console.print(
        Panel(
            f"[bold cyan]{BANNER.strip()}[/]\n[dim]{TAGLINE}[/]",
            border_style="cyan",
        )
    )


def rich_format_summary(config: Any) -> str:
    """Format a ProjectConfig summary using rich markup."""
    import io as _io

    from rich.console import Console
    from rich.table import Table

    table = Table(title="Configuration preview", show_header=False, border_style="dim")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Project", config.project_name)
    table.add_row("Stack", f"{config.language} / {config.framework}")
    table.add_row("Type", config.project_type)
    table.add_row("Workflow", config.workflow)
    table.add_row("Agents", str(len(config.agents)))
    table.add_row("Commands", str(len(config.commands)))
    table.add_row("Hooks", str(len(config.hooks)))
    table.add_row("Skills", str(len(config.recommended_skills)))
    table.add_row("Plugins", str(len(config.recommended_plugins)))
    table.add_row("MCPs", str(len(config.default_mcps)))

    features = []
    if config.features.memory:
        features.append("Memory")
    if config.features.spec_workflow:
        features.append("Spec workflow")
    if config.features.gtd:
        features.append("GTD")
    if config.features.worktrees:
        features.append("Worktrees")
    table.add_row("Features", ", ".join(features) if features else "none")

    buf = _io.StringIO()
    console = Console(file=buf, force_terminal=True)
    console.print(table)
    return buf.getvalue()


def rich_format_file_list(files: list[str]) -> str:
    """Format a file list with rich markup."""
    import io as _io

    from rich.console import Console
    from rich.tree import Tree

    tree = Tree("[bold]Generated files[/]")
    for f in sorted(files):
        tree.add(f"[green]+[/] {f}")

    buf = _io.StringIO()
    console = Console(file=buf, force_terminal=True)
    console.print(tree)
    return buf.getvalue()
