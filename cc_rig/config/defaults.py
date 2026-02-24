"""Smart defaults engine: compute_defaults(template, workflow) -> ProjectConfig.

Pure function. No side effects, no file I/O beyond loading built-in presets.
Algorithm from SMART-DEFAULTS-MATRIX.md §5b + SKILLS-MATRIX.md §8.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cc_rig import __version__
from cc_rig.config.project import Features, ProjectConfig, SkillRecommendation
from cc_rig.presets.manager import load_template, load_workflow

# Hooks that require a specific tool command to be present.
# If the template doesn't provide the tool command, the hook is skipped.
_HOOK_TOOL_REQUIREMENTS: dict[str, str] = {
    "format": "format",
    "lint": "lint",
    "typecheck": "typecheck",
}

# DB services that trigger "if_applicable" database phase.
_DB_SERVICES = {"postgres", "mysql", "sqlite"}

# ── Cross-cutting skill definitions (SKILLS-MATRIX.md §3) ──────────

# obra/superpowers skills, keyed by name
_SUPERPOWERS_SKILLS: dict[str, SkillRecommendation] = {
    "brainstorming": SkillRecommendation(
        name="brainstorming",
        sdlc_phase="planning",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill brainstorming",
        description="Socratic design refinement, explores alternatives",
    ),
    "writing-plans": SkillRecommendation(
        name="writing-plans",
        sdlc_phase="planning",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill writing-plans",
        description="Breaks work into bite-sized tasks",
    ),
    "executing-plans": SkillRecommendation(
        name="executing-plans",
        sdlc_phase="planning",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill executing-plans",
        description="Batch execution with human checkpoints",
    ),
    "dispatching-parallel-agents": SkillRecommendation(
        name="dispatching-parallel-agents",
        sdlc_phase="coding",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill dispatching-parallel-agents",
        description="Parallel agent coordination",
    ),
    "subagent-driven-development": SkillRecommendation(
        name="subagent-driven-development",
        sdlc_phase="coding",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill subagent-driven-development",
        description="Two-stage: spec compliance + code quality",
    ),
    "test-driven-development": SkillRecommendation(
        name="test-driven-development",
        sdlc_phase="testing",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill test-driven-development",
        description="Red-green-refactor cycle enforcement",
    ),
    "systematic-debugging": SkillRecommendation(
        name="systematic-debugging",
        sdlc_phase="testing",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill systematic-debugging",
        description="4-phase root cause analysis",
    ),
    "requesting-code-review": SkillRecommendation(
        name="requesting-code-review",
        sdlc_phase="review",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill requesting-code-review",
        description="Pre-review checklist, severity reporting",
    ),
    "receiving-code-review": SkillRecommendation(
        name="receiving-code-review",
        sdlc_phase="review",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill receiving-code-review",
        description="Guides responding to review feedback",
    ),
    "verification-before-completion": SkillRecommendation(
        name="verification-before-completion",
        sdlc_phase="review",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill verification-before-completion",
        description="Pre-completion validation",
    ),
    "using-git-worktrees": SkillRecommendation(
        name="using-git-worktrees",
        sdlc_phase="devops",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill using-git-worktrees",
        description="Isolated git worktrees with safety",
    ),
    "finishing-a-development-branch": SkillRecommendation(
        name="finishing-a-development-branch",
        sdlc_phase="devops",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill finishing-a-development-branch",
        description="Merge/PR decisions, branch cleanup",
    ),
    "writing-skills": SkillRecommendation(
        name="writing-skills",
        sdlc_phase="coding",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill writing-skills",
        description="Meta-skill: write new skills",
    ),
    "using-superpowers": SkillRecommendation(
        name="using-superpowers",
        sdlc_phase="coding",
        source="obra/superpowers",
        install="npx skills add obra/superpowers --skill using-superpowers",
        description="Meta-skill: orchestrate other skills",
    ),
}

# Trail of Bits core security skills
_TRAILOFBITS_CORE: dict[str, SkillRecommendation] = {
    "static-analysis": SkillRecommendation(
        name="static-analysis",
        sdlc_phase="security",
        source="trailofbits/skills",
        install="npx skills add trailofbits/skills --skill static-analysis",
        description="CodeQL, Semgrep, SARIF parsing",
    ),
    "insecure-defaults": SkillRecommendation(
        name="insecure-defaults",
        sdlc_phase="security",
        source="trailofbits/skills",
        install="npx skills add trailofbits/skills --skill insecure-defaults",
        description="Detect hardcoded credentials, fail-open security patterns",
    ),
    "second-opinion": SkillRecommendation(
        name="second-opinion",
        sdlc_phase="security",
        source="trailofbits/skills",
        install="npx skills add trailofbits/skills --skill second-opinion",
        description="Code review via external LLM CLIs",
    ),
}

# OWASP cross-cutting skill
_OWASP_SKILL = SkillRecommendation(
    name="claude-code-owasp",
    sdlc_phase="security",
    source="agamm/claude-code-owasp",
    install=(
        "curl -sL https://raw.githubusercontent.com/agamm/claude-code-owasp"
        "/main/.claude/skills/owasp-security/SKILL.md "
        "-o .claude/skills/owasp-security/SKILL.md --create-dirs"
    ),
    description="OWASP Top 10:2025, ASVS 5.0, language-specific security",
)


def compute_defaults(
    template: str,
    workflow: str,
    *,
    project_name: str = "",
    project_desc: str = "",
    output_dir: str = ".",
    claude_plan: str = "pro",
) -> ProjectConfig:
    """Map template + workflow → fully resolved ProjectConfig.

    Args:
        template: Template preset name (e.g. "fastapi", "nextjs").
        workflow: Workflow preset name (e.g. "standard", "speedrun").
        project_name: Project name (can be filled in later by wizard).
        project_desc: Project description.
        output_dir: Output directory for generated files.
        claude_plan: User's Claude plan tier.

    Returns:
        A fully resolved ProjectConfig ready for generators.
    """
    # Step 1: Load template preset → stack data
    tmpl = load_template(template)
    tool_cmds = tmpl["tool_commands"]

    # Step 2: Load workflow preset → process data
    wf = load_workflow(workflow)
    features = Features.from_dict(wf["features"])

    # Step 3: Build agent list from workflow
    agents = list(wf["agents"])

    # Step 4: Build command list from workflow
    commands = list(wf["commands"])

    # Step 5: Build hook list, filtering by tool command availability
    hooks = []
    for hook_name in wf["hooks"]:
        required_tool = _HOOK_TOOL_REQUIREMENTS.get(hook_name)
        if required_tool is not None:
            tool_cmd = tool_cmds.get(required_tool, "")
            if not tool_cmd:
                continue  # Skip hook — template has no command for it
        hooks.append(hook_name)

    # Step 6: Auto-add components for enabled features (safety net)
    # The workflow preset should already include these, but this ensures
    # consistency — especially important when expert mode toggles flags.
    if features.memory:
        if "memory-stop" not in hooks:
            hooks.append("memory-stop")
        if "memory-precompact" not in hooks:
            hooks.append("memory-precompact")
        if "remember" not in commands:
            commands.append("remember")

    if features.spec_workflow:
        if "pm-spec" not in agents:
            agents.append("pm-spec")
        if "implementer" not in agents:
            agents.append("implementer")
        if "spec-create" not in commands:
            commands.append("spec-create")
        if "spec-execute" not in commands:
            commands.append("spec-execute")

    if features.gtd:
        for cmd in ("gtd-capture", "gtd-process", "daily-plan"):
            if cmd not in commands:
                commands.append(cmd)

    if features.worktrees:
        if "parallel-worker" not in agents:
            agents.append("parallel-worker")
        if "worktree" not in commands:
            commands.append("worktree")

    # Step 7: Build recommended_skills with SDLC-aware merging
    default_mcps = list(tmpl.get("default_mcps", []))
    recommended_skills = _merge_skills(tmpl, wf, default_mcps)

    return ProjectConfig(
        project_name=project_name,
        project_desc=project_desc,
        output_dir=output_dir,
        language=tmpl["language"],
        framework=tmpl["framework"],
        project_type=tmpl["project_type"],
        test_cmd=tool_cmds.get("test", ""),
        lint_cmd=tool_cmds.get("lint", ""),
        format_cmd=tool_cmds.get("format", ""),
        typecheck_cmd=tool_cmds.get("typecheck", ""),
        build_cmd=tool_cmds.get("build", ""),
        source_dir=tmpl.get("source_dir", "."),
        test_dir=tmpl.get("test_dir", "tests"),
        workflow=wf["name"],
        agents=agents,
        commands=commands,
        hooks=hooks,
        features=features,
        permission_mode=wf.get("permission_mode", "default"),
        recommended_skills=recommended_skills,
        default_mcps=default_mcps,
        claude_plan=claude_plan,
        model_overrides={},
        cc_rig_version=__version__,
        created_at=datetime.now(timezone.utc).isoformat(),
        template_preset=tmpl["name"],
        workflow_preset=wf["name"],
    )


# ── Skill merge helpers (SKILLS-MATRIX.md §8) ──────────────────────


def _merge_skills(
    tmpl: dict[str, Any],
    wf: dict[str, Any],
    default_mcps: list[str],
) -> list[SkillRecommendation]:
    """Merge template + workflow skills using SDLC phase filtering."""
    skill_phases = dict(wf.get("skill_phases", {}))
    skill_packs = wf.get("skill_packs", {})

    # Step 0 + 1: Normalize template skills (bare strings → rich objects)
    template_skills = _normalize_skills(tmpl.get("recommended_skills", []))

    # Step 3: Resolve "if_applicable" for database phase
    if skill_phases.get("database") == "if_applicable":
        has_db = bool(set(default_mcps) & _DB_SERVICES)
        skill_phases["database"] = has_db

    # Step 4: Filter template skills by active phases
    active_skills: list[SkillRecommendation] = []
    for skill in template_skills:
        phase = skill.sdlc_phase
        if _phase_is_active(skill_phases, phase):
            active_skills.append(skill)

    # Step 5: Append cross-cutting skill packs
    pack_skills = _resolve_skill_packs(skill_packs, skill_phases)
    active_skills.extend(pack_skills)

    # Step 6: Deduplicate by name (later entries win — cross-cutting takes precedence)
    seen: dict[str, SkillRecommendation] = {}
    for skill in active_skills:
        seen[skill.name] = skill

    return list(seen.values())


def _normalize_skills(
    raw: list[Any],
) -> list[SkillRecommendation]:
    """Convert raw skill data (rich dicts or bare strings) to SkillRecommendation."""
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append(SkillRecommendation.from_dict(item))
        elif isinstance(item, str):
            result.append(SkillRecommendation(name=item))
        elif isinstance(item, SkillRecommendation):
            result.append(item)
    return result


def _phase_is_active(
    phases: dict[str, Any],
    phase: str,
) -> bool:
    """Check if a phase is active (included in CLAUDE.md output).

    Returns True for: True, "included"
    Returns False for: False, "reference", "bundled_only", absent, ""
    """
    if not phase:
        return False
    value = phases.get(phase)
    if value is True:
        return True
    return False


def _resolve_skill_packs(
    packs: dict[str, Any],
    skill_phases: dict[str, Any],
) -> list[SkillRecommendation]:
    """Expand skill packs into SkillRecommendation objects."""
    result: list[SkillRecommendation] = []

    # obra/superpowers
    superpowers = packs.get("superpowers", [])
    if superpowers == "full":
        # Include all superpowers skills whose phase is active
        for name, skill in _SUPERPOWERS_SKILLS.items():
            if _phase_is_active(skill_phases, skill.sdlc_phase):
                result.append(skill)
    elif isinstance(superpowers, list):
        for name in superpowers:
            skill = _SUPERPOWERS_SKILLS.get(name)
            if skill and _phase_is_active(skill_phases, skill.sdlc_phase):
                result.append(skill)

    # Trail of Bits core set
    tob = packs.get("trailofbits_core", [])
    if isinstance(tob, list):
        for name in tob:
            skill = _TRAILOFBITS_CORE.get(name)
            if skill and _phase_is_active(skill_phases, skill.sdlc_phase):
                result.append(skill)
    # "reference" means docs-only — don't include in active list

    # OWASP — included for all workflows where security phase is active
    if _phase_is_active(skill_phases, "security"):
        result.append(_OWASP_SKILL)

    return result
