"""Generate .github/workflows/claude.yml for Claude Code PR review.

Generates a GitHub Actions workflow that uses anthropics/claude-code-action@v1
to review pull requests and respond to @claude mentions in PR comments.
High-rigor workflows (verify-heavy, superpowers) get a security-review job.

Only generated when the github_actions feature flag is enabled.
"""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker

_SECURITY_REVIEW_WORKFLOWS = {"rigorous", "verify-heavy", "superpowers"}


def generate_github_actions(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate .github/workflows/claude.yml if feature enabled.

    Returns list of relative file paths written.
    """
    if not config.features.github_actions:
        return []

    content = _build_claude_yml(config)

    rel = ".github/workflows/claude.yml"
    if tracker is not None:
        tracker.write_text(rel, content)
    else:
        path = output_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    return [rel]


def _build_claude_yml(config: ProjectConfig) -> str:
    """Build the GitHub Actions workflow YAML content."""
    lines: list[str] = []

    lines.append("name: Claude Code Review")
    lines.append("")
    lines.append("on:")
    lines.append("  pull_request:")
    lines.append("    types: [opened, synchronize]")
    lines.append("  issue_comment:")
    lines.append("    types: [created]")
    lines.append("")
    lines.append("permissions:")
    lines.append("  contents: read")
    lines.append("  pull-requests: write")
    lines.append("  issues: write")
    lines.append("")
    lines.append("jobs:")
    lines.append("  claude-review:")
    lines.append("    if: |")
    lines.append("      github.event_name == 'pull_request' ||")
    lines.append("      (github.event_name == 'issue_comment' &&")
    lines.append("       contains(github.event.comment.body, '@claude'))")
    lines.append("    runs-on: ubuntu-latest")
    lines.append("    steps:")
    lines.append("      - uses: actions/checkout@v4")
    lines.append("      - uses: anthropics/claude-code-action@v1")
    lines.append("        with:")
    lines.append("          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}")

    if config.workflow in _SECURITY_REVIEW_WORKFLOWS:
        lines.append("")
        lines.append("  security-review:")
        lines.append("    if: github.event_name == 'pull_request'")
        lines.append("    runs-on: ubuntu-latest")
        lines.append("    steps:")
        lines.append("      - uses: actions/checkout@v4")
        lines.append("      - uses: anthropics/claude-code-action@v1")
        lines.append("        with:")
        lines.append("          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}")
        lines.append("          prompt: |")
        lines.append("            You are a security auditor. Review this PR for:")
        lines.append("            - Authentication and authorization issues")
        lines.append("            - Input validation vulnerabilities")
        lines.append("            - Secrets or credentials in code")
        lines.append("            - SQL injection, XSS, CSRF risks")
        lines.append("            - Dependency vulnerabilities")
        lines.append("            Focus only on security. Be specific about file and line.")

    lines.append("")
    return "\n".join(lines)
