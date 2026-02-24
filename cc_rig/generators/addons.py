"""Generate add-on files: specs template, GTD task files."""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.project import ProjectConfig


def generate_addons(
    config: ProjectConfig,
    output_dir: Path,
) -> list[str]:
    """Generate add-on files based on feature flags.

    Returns list of relative file paths written.
    """
    files: list[str] = []

    if config.features.spec_workflow:
        files.extend(_generate_specs_template(output_dir))

    if config.features.gtd:
        files.extend(_generate_gtd_files(output_dir))

    return files


def _generate_specs_template(output_dir: Path) -> list[str]:
    """Generate specs/TEMPLATE.md for the spec workflow."""
    specs_dir = output_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    (specs_dir / "TEMPLATE.md").write_text(
        "# Spec: <Feature Name>\n"
        "\n"
        "**Author**: <name>  \n"
        "**Date**: YYYY-MM-DD  \n"
        "**Status**: Draft | In Review | Approved | Implemented\n"
        "\n"
        "## Summary\n"
        "\n"
        "One-paragraph description of the feature.\n"
        "\n"
        "## User Stories\n"
        "\n"
        "- As a <role>, I want <action> so that <benefit>.\n"
        "\n"
        "## Acceptance Criteria\n"
        "\n"
        "- [ ] Given <context>, when <action>, then <result>.\n"
        "\n"
        "## Task Breakdown\n"
        "\n"
        "- [ ] Task 1 — description\n"
        "- [ ] Task 2 — description\n"
        "\n"
        "## Out of Scope\n"
        "\n"
        "- Items explicitly excluded from this spec.\n"
        "\n"
        "## Open Questions\n"
        "\n"
        "- Unresolved decisions or uncertainties.\n"
    )
    return ["specs/TEMPLATE.md"]


def _generate_gtd_files(output_dir: Path) -> list[str]:
    """Generate GTD task files: inbox.md, todo.md, someday.md."""
    tasks_dir = output_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    files: list[str] = []

    inbox_path = tasks_dir / "inbox.md"
    if not inbox_path.exists():
        inbox_path.write_text(
            "# Inbox\n"
            "\n"
            "Raw capture. Process with `/gtd-process`.\n"
            "\n"
            "Format: `- [ ] [YYYY-MM-DD] <description>`\n"
            "\n"
            "<!-- Items below -->\n"
        )
        files.append("tasks/inbox.md")

    todo_path = tasks_dir / "todo.md"
    if not todo_path.exists():
        todo_path.write_text(
            "# Todo\n"
            "\n"
            "Active tasks. Picked from inbox during "
            "`/gtd-process`.\n"
            "\n"
            "Format: `- [ ] [YYYY-MM-DD] <description> "
            "— Next: <action>`\n"
            "\n"
            "<!-- Items below -->\n"
        )
        files.append("tasks/todo.md")

    someday_path = tasks_dir / "someday.md"
    if not someday_path.exists():
        someday_path.write_text(
            "# Someday / Maybe\n"
            "\n"
            "Not actionable now. Review weekly.\n"
            "\n"
            "Format: `- [ ] [YYYY-MM-DD] <description>`\n"
            "\n"
            "<!-- Items below -->\n"
        )
        files.append("tasks/someday.md")

    return files
