"""Generate CLAUDE.local.md with personal preference stubs."""

from __future__ import annotations

from pathlib import Path

from cc_rig.generators.fileops import FileTracker


def generate_claude_local(
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate CLAUDE.local.md with personal preference stubs.

    This file is for per-developer customization and is not tracked
    by git. Uses preserve_on_clean=True so cc-rig clean does not
    delete user customizations.

    Returns list of relative file paths written.
    """
    content = (
        "# Personal Preferences (CLAUDE.local.md)\n"
        "\n"
        "This file is for your personal preferences. It is not "
        "tracked by git.\n"
        "Uncomment and edit the examples below, or add your own.\n"
        "\n"
        "## Preferences\n"
        "\n"
        "<!-- Uncomment any preferences you want to set:\n"
        "- Always use descriptive variable names.\n"
        "- Prefer functional style over imperative.\n"
        "- Use type annotations on all public functions.\n"
        "-->\n"
        "\n"
        "## Personal Context\n"
        "\n"
        "<!-- Add any personal context here:\n"
        "- I am working on the payments module this sprint.\n"
        "- My local dev environment uses Docker Compose.\n"
        "-->\n"
    )

    rel = "CLAUDE.local.md"
    if tracker is not None:
        tracker.write_text(rel, content, preserve_on_clean=True)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / rel).write_text(content)

    return [rel]
