"""Generate CLAUDE.md with cache-aware static-first ordering."""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker
from cc_rig.skills.registry import SKILL_CATALOG, resolve_skills
from cc_rig.templates import get_framework_content


def generate_claude_md(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
    *,
    skip: bool = False,
) -> list[str]:
    """Generate CLAUDE.md with sections ordered for prompt-cache efficiency.

    Static sections first (rarely change), dynamic sections last.
    Target line counts: speedrun ~56, standard ~93, spec-driven ~111,
    gtd-lite ~114, verify-heavy ~114.
    """
    if skip:
        return []

    sections: list[str] = []

    # ── Section 1: Project Identity (STATIC) ───────────────────────
    sections.append(_section_project_identity(config))

    # ── Section 2: Commands (STATIC) ───────────────────────────────
    sections.append(_section_commands(config))

    # ── Section 3: Guardrails (STATIC) ─────────────────────────────
    sections.append(_section_guardrails(config))

    # ── Section 3.5: Workflow Principles (STATIC, non-speedrun) ──
    if config.workflow != "speedrun":
        sections.append(_section_workflow_principles())

    # ── Section 3.6: Process Skills (STATIC, if community workflow) ──
    if config.process_skills:
        sections.append(_section_process_skills(config))

    # ── Section 4: Framework Rules (STATIC) ────────────────────────
    sections.append(_section_framework_rules(config))

    # ── Section 5: Agent Docs pointers (STATIC) ────────────────────
    sections.append(_section_agent_docs(config))

    # ── Section 5.5: Installed Skills (STATIC, if any) ──────────
    skills_section = _section_installed_skills(config)
    if skills_section:
        sections.append(skills_section)

    # ── Section 6: Memory pointers (SEMI-STATIC, if enabled) ──────
    if config.features.memory:
        sections.append(_section_memory(config))

    # ── Section 7: Spec Workflow (if enabled) ──────────────────────
    if config.features.spec_workflow:
        sections.append(_section_spec_workflow(config))

    # ── Section 8: GTD (if enabled) ───────────────────────────────
    if config.features.gtd:
        sections.append(_section_gtd(config))

    # ── Section 9: Worktree guidance (if enabled) ─────────────────
    if config.features.worktrees:
        sections.append(_section_worktrees(config))

    # ── Section 10: Current Context (DYNAMIC — last for cache) ────
    sections.append(_section_current_context(config))

    content = "\n".join(sections)

    if tracker is not None:
        tracker.write_text("CLAUDE.md", content, preserve_on_clean=True)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "CLAUDE.md").write_text(content)

    return ["CLAUDE.md"]


# ── Section builders ───────────────────────────────────────────────


def _section_project_identity(config: ProjectConfig) -> str:
    name = config.project_name or "my-project"
    desc = config.project_desc or f"A {config.framework} project"
    return (
        f"# {name}\n"
        f"\n"
        f"{desc}\n"
        f"\n"
        f"- **Stack**: {config.language} / {config.framework}\n"
        f"- **Type**: {config.project_type}\n"
        f"- **Source**: `{config.source_dir}/`  "
        f"**Tests**: `{config.test_dir}/`\n"
    )


def _section_commands(config: ProjectConfig) -> str:
    lines = ["## Commands\n"]
    if config.test_cmd:
        lines.append(f"- **Test**: `{config.test_cmd}`")
    if config.lint_cmd:
        lines.append(f"- **Lint**: `{config.lint_cmd}`")
    if config.format_cmd:
        lines.append(f"- **Format**: `{config.format_cmd}`")
    if config.typecheck_cmd:
        lines.append(f"- **Typecheck**: `{config.typecheck_cmd}`")
    if config.build_cmd:
        lines.append(f"- **Build**: `{config.build_cmd}`")
    lines.append("")
    return "\n".join(lines)


def _section_guardrails(config: ProjectConfig) -> str:
    lines = [
        "## Guardrails\n",
        "- Run tests before committing. Run lint before pushing.",
        "- Never commit .env, credentials, or secrets.",
        "- Never push directly to main/master.",
        "- Never run destructive commands (rm -rf /, DROP TABLE).",
        "- Prefer editing existing files over creating new ones.",
        "- Keep commits small and focused. One concern per commit.",
    ]

    # Harness-aware guardrails (flag-based)
    h = config.harness
    if h.budget_awareness:
        lines.append(
            "- Budget-aware: plan before acting, checkpoint often, stop cleanly at budget warning."
        )
    if h.verification_gates:
        lines.append(
            "- Commits are gate-checked: lint must pass. Run ./init-sh.sh verify before committing."
        )
    if h.autonomy_loop:
        lines.append("- Autonomy mode active. Follow PROMPT.md for iteration instructions.")

    lines.append("")
    return "\n".join(lines)


def _section_workflow_principles() -> str:
    return (
        "## Workflow Principles\n"
        "\n"
        "- **Plan first.** Before writing any code, describe your "
        "approach and wait for approval. Use `/plan` or `/assumptions` "
        "before implementing non-trivial changes.\n"
        "- **Clarify before coding.** If the requirements are ambiguous, "
        "ask clarifying questions before writing any code.\n"
        "- **Research before coding.** Spawn an explorer subagent "
        "(Task tool with Explore type) to map unfamiliar code "
        "before modifying it. Keep the main context clean.\n"
        "- **Suggest tests.** After writing code, list the edge cases "
        "and suggest test cases to cover them.\n"
        "- **Break up large changes.** If a task requires changes to "
        "more than 3 files, stop and break it into smaller tasks first.\n"
        "- **Test-first debugging.** When there's a bug, start by writing "
        "a test that reproduces it, then fix it until the test passes.\n"
        "- **Verify before done.** Run tests, lint, and typecheck "
        "before committing. Never assume code works without "
        "running it.\n"
        "- **Fix failures immediately.** When tests or lint fail, "
        "diagnose and fix the root cause now. Don't log it for "
        "later.\n"
        "- **Learn from corrections.** Every time you are corrected, "
        "reflect on what went wrong and plan to avoid the same "
        "mistake again.\n"
        "- **Demand elegance.** After getting code working, "
        "consider a refactor pass. Leave code measurably better "
        "than you found it.\n"
        "- **Save learnings.** Auto-memory handles personal "
        "continuity. Use `/remember` for team knowledge — "
        "decisions, patterns, and gotchas.\n"
    )


def _section_process_skills(config: ProjectConfig) -> str:
    """Generate process skills section with source attribution."""
    source = config.workflow_source or "community"
    url = config.workflow_source_url or ""

    lines = [f"## Process Skills ({config.workflow})", ""]

    # Attribution
    if url:
        lines.append(f"This project uses the **{config.workflow}** workflow ({source}).")
    else:
        lines.append(f"This project uses the **{config.workflow}** workflow.")
    lines.append("")

    # Skill list
    lines.append("Installed process skills:")
    for skill_name in config.process_skills:
        spec = SKILL_CATALOG.get(skill_name)
        desc = spec.description if spec else ""
        lines.append(f"- `/{skill_name}` -- {desc}")
    lines.append("")

    # Workflow-specific notes
    if config.workflow == "gstack":
        lines.append(
            "For the full gstack suite (browser-based QA, retros), "
            "see https://github.com/garrytan/gstack"
        )
        lines.append("")

    return "\n".join(lines)


def _section_framework_rules(config: ProjectConfig) -> str:
    content = get_framework_content(config.framework)
    rules = content.get("rules", "")

    # Templates already include "## Framework Rules (FrameworkName)" heading
    if rules.startswith("## "):
        return f"{rules}\n"
    return f"## Framework Rules\n\n{rules}\n"


def _section_agent_docs(config: ProjectConfig) -> str:
    lines = [
        "## Agent Docs\n",
        "Read @agent_docs/architecture.md @agent_docs/conventions.md for core context.",
        "Additional docs: @agent_docs/testing.md @agent_docs/deployment.md",
        "@agent_docs/cache-friendly-workflow.md\n",
    ]
    return "\n".join(lines)


def _section_installed_skills(config: ProjectConfig) -> str:
    """List auto-installed community skills grouped by phase.

    Returns empty string if no skills are resolved (e.g. unknown template).
    """
    specs = resolve_skills(
        config.template_preset or config.framework or "",
        config.workflow or "standard",
        config.default_mcps,
        packs=config.skill_packs,
    )
    if not specs:
        return ""

    lines = [
        "## Installed Skills\n",
        "Community skills auto-installed by cc-rig:\n",
    ]

    # Group by SDLC phase
    by_phase: dict[str, list[str]] = {}
    for spec in specs:
        phase = spec.sdlc_phase or "other"
        by_phase.setdefault(phase, []).append(f"{spec.name} ({spec.repo})")

    for phase in ("coding", "testing", "review", "security", "database", "devops", "planning"):
        entries = by_phase.get(phase, [])
        if entries:
            lines.append(f"- **{phase.title()}**: {entries[0]}")
            for entry in entries[1:]:
                lines.append(f"  - {entry}")

    lines.append("")
    lines.append("Manage: `cc-rig skills list` | Browse: [skills.sh](https://skills.sh/)\n")
    return "\n".join(lines)


def _section_memory(config: ProjectConfig) -> str:
    return (
        "## Memory\n"
        "\n"
        "Two memory systems work together:\n"
        "- **Auto-memory** (`~/.claude/projects/`): Personal notes, "
        "loaded automatically each session.\n"
        "- **Team memory** (`memory/`): Git-tracked shared knowledge "
        "for the whole team.\n"
        "\n"
        "Team memory files — load via Read tool when context is needed:\n"
        "- `memory/decisions.md` — architectural decisions\n"
        "- `memory/patterns.md` — discovered patterns\n"
        "- `memory/gotchas.md` — known issues and surprises\n"
        "- `memory/people.md` — team ownership\n"
        "- `memory/session-log.md` — brief session history\n"
        "- See `memory/MEMORY-README.md` for usage instructions.\n"
    )


def _section_spec_workflow(config: ProjectConfig) -> str:
    return (
        "## Spec Workflow\n"
        "\n"
        "Use `/spec-create` to interview the user and produce a spec "
        "document in `specs/`.\n"
        "Use `/spec-execute` to pick a task from the spec and "
        "implement it with validation.\n"
        "Specs live in `specs/` as markdown. Each spec has "
        "acceptance criteria and task breakdown.\n"
    )


def _section_gtd(config: ProjectConfig) -> str:
    return (
        "## GTD System\n"
        "\n"
        "Task management follows Getting Things Done:\n"
        "- `tasks/inbox.md` — quick capture, unprocessed items\n"
        "- `tasks/todo.md` — actionable tasks with context\n"
        "- `tasks/someday.md` — deferred ideas\n"
        "\n"
        "Use `/gtd-capture` to add items, `/gtd-process` to triage, "
        "`/daily-plan` for morning review.\n"
    )


def _section_worktrees(config: ProjectConfig) -> str:
    return (
        "## Worktrees\n"
        "\n"
        "Use `/worktree <task>` to spawn a parallel-worker agent "
        "in an isolated git worktree.\n"
        "The parallel-worker runs with `isolation: worktree` and "
        "`background: true`.\n"
        "Each worktree gets its own branch. Merge results back via PR.\n"
        "\n"
        "For batch orchestration from the terminal:\n"
        "```\n"
        'cc-rig worktree spawn "Fix auth bug" "Add rate limiting"\n'
        "cc-rig worktree list        # check status of all worktrees\n"
        "cc-rig worktree pr fix-auth  # push and create PR\n"
        "cc-rig worktree cleanup --merged  # clean up finished work\n"
        "```\n"
    )


def _section_current_context(config: ProjectConfig) -> str:
    return (
        "## Current Context\n"
        "\n"
        "_This section is updated each session. "
        "Everything above is static._\n"
        "\n"
        "- **Current task**: (none)\n"
        "- **Branch**: main\n"
    )
