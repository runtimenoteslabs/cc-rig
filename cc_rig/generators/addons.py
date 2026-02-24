"""Generate add-on files: specs template, GTD task files."""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker


def generate_addons(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate add-on files based on feature flags.

    Returns list of relative file paths written.
    """
    files: list[str] = []

    if config.features.spec_workflow:
        files.extend(_generate_specs_template(output_dir, tracker))

    if config.features.gtd:
        files.extend(_generate_gtd_files(output_dir, tracker))

    return files


def _generate_specs_template(
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate specs/TEMPLATE.md for the spec workflow."""
    specs_dir = output_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    template_content = (
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
    if tracker is not None:
        tracker.write_text("specs/TEMPLATE.md", template_content)
    else:
        (specs_dir / "TEMPLATE.md").write_text(template_content)
    return ["specs/TEMPLATE.md"]


def _generate_gtd_files(
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate GTD task files: inbox.md, todo.md, someday.md."""
    tasks_dir = output_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    files: list[str] = []

    gtd_files = {
        "tasks/inbox.md": (
            "# Inbox\n"
            "\n"
            "Raw capture. Process with `/gtd-process`.\n"
            "\n"
            "Format: `- [ ] [YYYY-MM-DD] <description>`\n"
            "\n"
            "<!-- Items below -->\n"
        ),
        "tasks/todo.md": (
            "# Todo\n"
            "\n"
            "Active tasks. Picked from inbox during "
            "`/gtd-process`.\n"
            "\n"
            "Format: `- [ ] [YYYY-MM-DD] <description> "
            "— Next: <action>`\n"
            "\n"
            "<!-- Items below -->\n"
        ),
        "tasks/someday.md": (
            "# Someday / Maybe\n"
            "\n"
            "Not actionable now. Review weekly.\n"
            "\n"
            "Format: `- [ ] [YYYY-MM-DD] <description>`\n"
            "\n"
            "<!-- Items below -->\n"
        ),
    }
    for rel, content in gtd_files.items():
        full = output_dir / rel
        if not full.exists():
            if tracker is not None:
                tracker.write_text(rel, content)
            else:
                full.write_text(content)
            files.append(rel)

    return files
