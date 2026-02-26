"""Generate memory/ system files for project memory."""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker

# Shared memory file templates — used by both the generator and doctor --fix.
MEMORY_FILE_TEMPLATES: dict[str, str] = {
    "decisions.md": (
        "# Decisions\n"
        "\n"
        "Architectural decisions and rationale. "
        "One line per entry.\n"
        "\n"
        "Format: `[YYYY-MM-DD] Decision: <description> "
        "— Reason: <why>`\n"
        "\n"
        "<!-- Entries below -->\n"
    ),
    "patterns.md": (
        "# Patterns\n"
        "\n"
        "Discovered code patterns and established conventions. "
        "One line per entry.\n"
        "\n"
        "Format: `[YYYY-MM-DD] Pattern: <description>`\n"
        "\n"
        "<!-- Entries below -->\n"
    ),
    "gotchas.md": (
        "# Gotchas\n"
        "\n"
        "Known issues, things that did not work, and surprises. "
        "One line per entry.\n"
        "\n"
        "Format: `[YYYY-MM-DD] Gotcha: <what happened> "
        "— Fix: <what worked>`\n"
        "\n"
        "<!-- Entries below -->\n"
    ),
    "people.md": (
        "# People\n"
        "\n"
        "Who owns what. Updated when ownership changes. "
        "One line per entry.\n"
        "\n"
        "Format: `[YYYY-MM-DD] <person/team>: owns <area>`\n"
        "\n"
        "<!-- Entries below -->\n"
    ),
    "session-log.md": (
        "# Session Log\n"
        "\n"
        "Brief log of what was done each session. Keep only "
        "the last 20 entries.\n"
        "Older entries should be summarized into a single "
        '"history" line.\n'
        "\n"
        "Format: `[YYYY-MM-DD] <one-line summary of session>`\n"
        "\n"
        "<!-- Entries below -->\n"
    ),
}


def generate_memory(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate memory/ files if config.features.memory is True.

    Creates 5 memory files plus MEMORY-README.md with usage
    instructions for Claude.

    Returns list of relative file paths written.
    """
    if not config.features.memory:
        return []

    memory_dir = output_dir / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    files_written: list[str] = []

    for filename, template in MEMORY_FILE_TEMPLATES.items():
        rel = f"memory/{filename}"
        if tracker is not None:
            tracker.write_text(rel, template, preserve_on_clean=True)
        else:
            (memory_dir / filename).write_text(template)
        files_written.append(rel)

    # MEMORY-README.md
    readme_content = (
        "# Memory System — Instructions for Claude\n"
        "\n"
        "This directory is the project's persistent memory. "
        "Claude Code has no native memory across sessions, "
        "so these files bridge the gap.\n"
        "\n"
        "## How to Use\n"
        "\n"
        "### Reading Memory\n"
        "- At session start, read `decisions.md` and "
        "`session-log.md` for recent context.\n"
        "- Read other files on demand when relevant to the "
        "current task.\n"
        "- Use the Read tool to load files. Do NOT put "
        "memory content in CLAUDE.md.\n"
        "\n"
        "### Writing Memory\n"
        "- Before stopping a session, save learnings to the "
        "appropriate file.\n"
        "- Before context compaction, save key decisions and "
        "patterns.\n"
        "- Always use one-line entries with date prefix.\n"
        "\n"
        "### Anti-Ballooning Rules\n"
        "1. **One line per entry.** No multi-line descriptions.\n"
        "2. **Session-log rotation.** Keep only the last 20 "
        "sessions. Summarize older entries into a single "
        '"history" line.\n'
        "3. **Periodic review.** When using `/remember`, "
        "consolidate duplicates and prune outdated entries.\n"
        "4. **Pointers, not inline.** CLAUDE.md points here. "
        "Load via Read tool on demand.\n"
        "\n"
        "## File Purposes\n"
        "\n"
        "| File | What to Store | When to Update |\n"
        "|------|---------------|----------------|\n"
        "| `decisions.md` | Architectural decisions + rationale "
        "| When major decisions are made |\n"
        "| `patterns.md` | Code patterns + conventions | When "
        "patterns are established |\n"
        "| `gotchas.md` | Known issues, failed approaches | "
        "When something surprising happens |\n"
        "| `people.md` | Who owns what | When ownership "
        "changes |\n"
        "| `session-log.md` | One-line session summaries | End "
        "of every session |\n"
    )
    if tracker is not None:
        tracker.write_text("memory/MEMORY-README.md", readme_content, preserve_on_clean=True)
    else:
        (memory_dir / "MEMORY-README.md").write_text(readme_content)
    files_written.append("memory/MEMORY-README.md")

    return files_written
