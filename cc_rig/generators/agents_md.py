"""Generate AGENTS.md — cross-agent configuration (Linux Foundation standard).

AGENTS.md is the cross-platform equivalent of CLAUDE.md. It is recognized by
Claude Code, Codex, Cursor, Copilot, Gemini CLI, and 30+ other AI coding
agents. Generated only when the agents_md feature flag is enabled.

Spec: https://agents.md/
"""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker


def generate_agents_md(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate AGENTS.md at the project root.

    Returns list of relative file paths written.
    """
    if not config.features.agents_md:
        return []

    content = _build_agents_md(config)

    rel = "AGENTS.md"
    if tracker is not None:
        tracker.write_text(rel, content)
    else:
        (output_dir / rel).write_text(content)

    return [rel]


def _build_agents_md(config: ProjectConfig) -> str:
    """Build AGENTS.md content from project config."""
    sections: list[str] = []

    # Header
    sections.append(
        f"# {config.project_name}\n\nLanguage: {config.language}  \nFramework: {config.framework}\n"
    )

    # Commands
    cmds: list[str] = []
    if config.test_cmd:
        cmds.append(f"- **Test**: `{config.test_cmd}`")
    if config.lint_cmd:
        cmds.append(f"- **Lint**: `{config.lint_cmd}`")
    if config.format_cmd:
        cmds.append(f"- **Format**: `{config.format_cmd}`")
    if config.typecheck_cmd:
        cmds.append(f"- **Typecheck**: `{config.typecheck_cmd}`")
    if cmds:
        sections.append("## Commands\n\n" + "\n".join(cmds) + "\n")

    # Project structure
    structure_lines = []
    if config.source_dir and config.source_dir != ".":
        structure_lines.append(f"- Source: `{config.source_dir}/`")
    if config.test_dir:
        structure_lines.append(f"- Tests: `{config.test_dir}/`")
    if structure_lines:
        sections.append("## Structure\n\n" + "\n".join(structure_lines) + "\n")

    # Code style
    style_lines = [
        "- Prefer editing existing files over creating new ones.",
        "- Keep commits small and focused.",
    ]
    if config.language == "python":
        style_lines.append("- Python 3.9+ compatibility. Use `Optional[Type]` not `Type | None`.")
    elif config.language == "typescript":
        style_lines.append("- Use TypeScript strict mode. Prefer interfaces over type aliases.")
    elif config.language == "go":
        style_lines.append(
            "- Follow Go conventions: `gofmt`, short variable names, error wrapping."
        )
    elif config.language == "rust":
        style_lines.append("- Follow Rust conventions: `cargo fmt`, derive macros, `Result` types.")
    sections.append("## Code Style\n\n" + "\n".join(style_lines) + "\n")

    # Testing
    test_lines = ["- Run tests before committing.", "- Run lint before pushing."]
    sections.append("## Testing\n\n" + "\n".join(test_lines) + "\n")

    # Boundaries
    boundary_lines = [
        "- Never commit .env, credentials, or secrets.",
        "- Never read, output, or log API keys, private keys, tokens, or seed phrases.",
        "- Never push directly to main/master.",
        "- Never run destructive commands (rm -rf /, DROP TABLE).",
    ]
    sections.append("## Boundaries\n\n" + "\n".join(boundary_lines) + "\n")

    return "\n".join(sections)
