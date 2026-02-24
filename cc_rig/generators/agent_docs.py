"""Generate agent_docs/ — architecture, conventions, testing, deployment."""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.project import ProjectConfig
from cc_rig.templates import get_framework_content


def generate_agent_docs(
    config: ProjectConfig,
    output_dir: Path,
) -> list[str]:
    """Generate agent_docs/ files with framework-specific content.

    Each file has a header and content from the framework template.
    Unknown frameworks fall back to the generic template.

    Returns list of relative file paths written.
    """
    docs_dir = output_dir / "agent_docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    content = get_framework_content(config.framework)

    files_written: list[str] = []

    for section in ("architecture", "conventions", "testing", "deployment"):
        section_content = content.get(section, "")

        text = f"# {section.title()}\n\n{section_content}\n"

        filename = f"{section}.md"
        (docs_dir / filename).write_text(text)
        files_written.append(f"agent_docs/{filename}")

    # Cache-friendly workflow guide (always generated)
    _write_cache_friendly_workflow(docs_dir)
    files_written.append("agent_docs/cache-friendly-workflow.md")

    return files_written


def _write_cache_friendly_workflow(docs_dir: Path) -> None:
    """Generate cache-friendly-workflow.md."""
    (docs_dir / "cache-friendly-workflow.md").write_text(
        "# Cache-Friendly Workflow\n"
        "\n"
        "Claude Code builds its system around prompt caching. "
        "Follow these practices to maximize cache hit rates.\n"
        "\n"
        "## CLAUDE.md Structure\n"
        "- Static sections (project identity, commands, guardrails) "
        "are at the top.\n"
        "- Dynamic sections (current context) are at the bottom.\n"
        "- Everything above the dynamic section is identical across "
        "sessions, maximizing cache reuse.\n"
        "\n"
        "## Do\n"
        "- Keep CLAUDE.md stable. Avoid frequent edits to the top "
        "sections.\n"
        "- Define all hooks, permissions, and MCP servers upfront. "
        "Don't toggle mid-project.\n"
        "- Use subagents (Task tool) for model escalation instead "
        "of switching models mid-session.\n"
        "- Load memory files via Read tool on demand, not inline "
        "in CLAUDE.md.\n"
        "\n"
        "## Don't\n"
        "- Don't put memory content directly in CLAUDE.md — it "
        "changes every session and breaks cache.\n"
        "- Don't switch models mid-conversation — this rebuilds "
        "the prompt cache.\n"
        "- Don't conditionally enable/disable hooks during a "
        "session.\n"
        "- Don't connect/disconnect MCP servers during work.\n"
    )
