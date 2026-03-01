"""Curated skill catalog and resolution engine.

Central registry of all downloadable community skills with metadata.
Replaces the old template recommended_skills + workflow skill_phases/skill_packs
approach with a single registry that resolves skills based on template × workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillSpec:
    """Metadata for a single downloadable skill."""

    name: str
    repo: str  # "obra/superpowers"
    repo_path: str  # "skills/test-driven-development"
    sdlc_phase: str  # "testing"
    description: str
    download_mode: str = "skill_md_only"  # "skill_md_only" or "full_tree"
    companion_files: list[str] = field(default_factory=list)


@dataclass
class SkillPackSpec:
    """Optional skill pack selectable in the wizard."""

    name: str  # "security"
    label: str  # "Security Deep Dive"
    description: str  # one-line for wizard
    skill_names: list[str]  # refs into SKILL_CATALOG
    suggested_templates: list[str] | None = None  # None = all, list = specific


# ── All downloadable skills (40 unique) ────────────────────────────────

SKILL_CATALOG: dict[str, SkillSpec] = {
    # obra/superpowers — 12 skills
    "test-driven-development": SkillSpec(
        name="test-driven-development",
        repo="obra/superpowers",
        repo_path="skills/test-driven-development",
        sdlc_phase="testing",
        description="Red-green-refactor cycle enforcement",
        download_mode="full_tree",
    ),
    "systematic-debugging": SkillSpec(
        name="systematic-debugging",
        repo="obra/superpowers",
        repo_path="skills/systematic-debugging",
        sdlc_phase="testing",
        description="4-phase root cause analysis",
        download_mode="full_tree",
    ),
    "requesting-code-review": SkillSpec(
        name="requesting-code-review",
        repo="obra/superpowers",
        repo_path="skills/requesting-code-review",
        sdlc_phase="review",
        description="Pre-review checklist, severity reporting",
        download_mode="full_tree",
    ),
    "receiving-code-review": SkillSpec(
        name="receiving-code-review",
        repo="obra/superpowers",
        repo_path="skills/receiving-code-review",
        sdlc_phase="review",
        description="Guides responding to review feedback",
        download_mode="full_tree",
    ),
    "finishing-a-development-branch": SkillSpec(
        name="finishing-a-development-branch",
        repo="obra/superpowers",
        repo_path="skills/finishing-a-development-branch",
        sdlc_phase="devops",
        description="Merge/PR decisions, branch cleanup",
        download_mode="full_tree",
    ),
    "brainstorming": SkillSpec(
        name="brainstorming",
        repo="obra/superpowers",
        repo_path="skills/brainstorming",
        sdlc_phase="planning",
        description="Socratic design refinement, explores alternatives",
        download_mode="full_tree",
    ),
    "writing-plans": SkillSpec(
        name="writing-plans",
        repo="obra/superpowers",
        repo_path="skills/writing-plans",
        sdlc_phase="planning",
        description="Breaks work into bite-sized tasks",
        download_mode="full_tree",
    ),
    "executing-plans": SkillSpec(
        name="executing-plans",
        repo="obra/superpowers",
        repo_path="skills/executing-plans",
        sdlc_phase="planning",
        description="Batch execution with human checkpoints",
        download_mode="full_tree",
    ),
    "using-git-worktrees": SkillSpec(
        name="using-git-worktrees",
        repo="obra/superpowers",
        repo_path="skills/using-git-worktrees",
        sdlc_phase="devops",
        description="Isolated git worktrees with safety",
        download_mode="full_tree",
    ),
    "verification-before-completion": SkillSpec(
        name="verification-before-completion",
        repo="obra/superpowers",
        repo_path="skills/verification-before-completion",
        sdlc_phase="review",
        description="Pre-completion validation",
        download_mode="full_tree",
    ),
    "subagent-driven-development": SkillSpec(
        name="subagent-driven-development",
        repo="obra/superpowers",
        repo_path="skills/subagent-driven-development",
        sdlc_phase="coding",
        description="Two-stage: spec compliance + code quality",
        download_mode="full_tree",
    ),
    # trailofbits/skills — 4 skills
    "modern-python": SkillSpec(
        name="modern-python",
        repo="trailofbits/skills",
        repo_path="plugins/modern-python/skills/modern-python",
        sdlc_phase="coding",
        description="Modern Python with uv, ruff, ty, pytest",
        download_mode="skill_md_only",
    ),
    "property-based-testing": SkillSpec(
        name="property-based-testing",
        repo="trailofbits/skills",
        repo_path="plugins/property-based-testing/skills/property-based-testing",
        sdlc_phase="testing",
        description="Multi-language property testing",
        download_mode="skill_md_only",
    ),
    "insecure-defaults": SkillSpec(
        name="insecure-defaults",
        repo="trailofbits/skills",
        repo_path="plugins/insecure-defaults/skills/insecure-defaults",
        sdlc_phase="security",
        description="Detect hardcoded credentials, fail-open security patterns",
        download_mode="skill_md_only",
    ),
    "static-analysis": SkillSpec(
        name="static-analysis",
        repo="trailofbits/skills",
        repo_path="plugins/static-analysis/skills/codeql",
        sdlc_phase="security",
        description="CodeQL, Semgrep, SARIF parsing",
        download_mode="skill_md_only",
    ),
    # anthropics/skills — 3 skills
    "skill-creator": SkillSpec(
        name="skill-creator",
        repo="anthropics/skills",
        repo_path="skills/skill-creator",
        sdlc_phase="coding",
        description="Meta-skill: create new Claude Code skills interactively",
        download_mode="skill_md_only",
    ),
    "webapp-testing": SkillSpec(
        name="webapp-testing",
        repo="anthropics/skills",
        repo_path="skills/webapp-testing",
        sdlc_phase="testing",
        description="Web application testing patterns from Anthropic",
        download_mode="skill_md_only",
    ),
    "frontend-design": SkillSpec(
        name="frontend-design",
        repo="anthropics/skills",
        repo_path="skills/frontend-design",
        sdlc_phase="coding",
        description="Frontend design patterns from Anthropic",
        download_mode="skill_md_only",
    ),
    # supabase/agent-skills — 1 skill
    "supabase-postgres-best-practices": SkillSpec(
        name="supabase-postgres-best-practices",
        repo="supabase/agent-skills",
        repo_path="skills/supabase-postgres-best-practices",
        sdlc_phase="database",
        description="PostgreSQL best practices with Supabase",
        download_mode="full_tree",
    ),
    # planetscale/database-skills — 1 skill
    "planetscale-postgresql": SkillSpec(
        name="planetscale-postgresql",
        repo="planetscale/database-skills",
        repo_path="skills/postgres",
        sdlc_phase="database",
        description="Postgres MVCC, VACUUM, WAL tuning, replication",
        download_mode="full_tree",
    ),
    # akin-ozer/cc-devops-skills — 2 skills
    "github-actions-generator": SkillSpec(
        name="github-actions-generator",
        repo="akin-ozer/cc-devops-skills",
        repo_path="devops-skills-plugin/skills/github-actions-generator",
        sdlc_phase="devops",
        description="GitHub Actions CI/CD pipeline generation",
        download_mode="full_tree",
    ),
    "dockerfile-generator": SkillSpec(
        name="dockerfile-generator",
        repo="akin-ozer/cc-devops-skills",
        repo_path="devops-skills-plugin/skills/dockerfile-generator",
        sdlc_phase="devops",
        description="Dockerfile generation with best practices",
        download_mode="full_tree",
    ),
    # agamm/claude-code-owasp — 1 skill
    "owasp-security": SkillSpec(
        name="owasp-security",
        repo="agamm/claude-code-owasp",
        repo_path=".claude/skills/owasp-security",
        sdlc_phase="security",
        description="OWASP Top 10:2025, ASVS 5.0, language-specific security",
        download_mode="skill_md_only",
    ),
    # vercel-labs — 3 skills
    "vercel-react-best-practices": SkillSpec(
        name="vercel-react-best-practices",
        repo="vercel-labs/agent-skills",
        repo_path="skills/react-best-practices",
        sdlc_phase="coding",
        description="React best practices from Vercel",
        download_mode="skill_md_only",
    ),
    "next-best-practices": SkillSpec(
        name="next-best-practices",
        repo="vercel-labs/next-skills",
        repo_path="skills/next-best-practices",
        sdlc_phase="coding",
        description="Next.js App Router, RSC, caching patterns",
        download_mode="skill_md_only",
    ),
    "web-design-guidelines": SkillSpec(
        name="web-design-guidelines",
        repo="vercel-labs/agent-skills",
        repo_path="skills/web-design-guidelines",
        sdlc_phase="coding",
        description="Web design guidelines and UI patterns",
        download_mode="skill_md_only",
    ),
    # wshobson/agents — 1 skill
    "tailwind-design-system": SkillSpec(
        name="tailwind-design-system",
        repo="wshobson/agents",
        repo_path="plugins/frontend-mobile-development/skills/tailwind-design-system",
        sdlc_phase="coding",
        description="Tailwind CSS v4 design system",
        download_mode="skill_md_only",
    ),
    # ── Skill pack skills ──────────────────────────────────────────────
    # trailofbits/skills — security pack
    "supply-chain-risk-auditor": SkillSpec(
        name="supply-chain-risk-auditor",
        repo="trailofbits/skills",
        repo_path="plugins/supply-chain-risk-auditor/skills/supply-chain-risk-auditor",
        sdlc_phase="security",
        description="Dependency risk analysis and supply chain auditing",
        download_mode="skill_md_only",
    ),
    "variant-analysis": SkillSpec(
        name="variant-analysis",
        repo="trailofbits/skills",
        repo_path="plugins/variant-analysis/skills/variant-analysis",
        sdlc_phase="security",
        description="Find similar vulnerabilities across codebase",
        download_mode="skill_md_only",
    ),
    "sharp-edges": SkillSpec(
        name="sharp-edges",
        repo="trailofbits/skills",
        repo_path="plugins/sharp-edges/skills/sharp-edges",
        sdlc_phase="security",
        description="Identify dangerous API patterns and footguns",
        download_mode="skill_md_only",
    ),
    "differential-review": SkillSpec(
        name="differential-review",
        repo="trailofbits/skills",
        repo_path="plugins/differential-review/skills/differential-review",
        sdlc_phase="review",
        description="Security-focused diff review for PRs",
        download_mode="skill_md_only",
    ),
    # ahmedasmar/devops — devops pack
    "iac-terraform": SkillSpec(
        name="iac-terraform",
        repo="ahmedasmar/devops",
        repo_path="iac-terraform/skills",
        sdlc_phase="devops",
        description="Terraform IaC patterns and best practices",
        download_mode="skill_md_only",
    ),
    "k8s-troubleshooter": SkillSpec(
        name="k8s-troubleshooter",
        repo="ahmedasmar/devops",
        repo_path="k8s-troubleshooter/skills",
        sdlc_phase="devops",
        description="Kubernetes debugging and troubleshooting",
        download_mode="skill_md_only",
    ),
    "monitoring-observability": SkillSpec(
        name="monitoring-observability",
        repo="ahmedasmar/devops",
        repo_path="monitoring-observability",
        sdlc_phase="devops",
        description="Monitoring, alerting, and observability patterns",
        download_mode="skill_md_only",
    ),
    "gitops-workflows": SkillSpec(
        name="gitops-workflows",
        repo="ahmedasmar/devops",
        repo_path="gitops-workflows",
        sdlc_phase="devops",
        description="GitOps deployment workflows and patterns",
        download_mode="skill_md_only",
    ),
    # addyosmani/web-quality-skills — web quality pack
    "web-quality-audit": SkillSpec(
        name="web-quality-audit",
        repo="addyosmani/web-quality-skills",
        repo_path="skills/web-quality-audit",
        sdlc_phase="review",
        description="Comprehensive web quality auditing",
        download_mode="skill_md_only",
    ),
    "accessibility": SkillSpec(
        name="accessibility",
        repo="addyosmani/web-quality-skills",
        repo_path="skills/accessibility",
        sdlc_phase="review",
        description="WCAG accessibility compliance checking",
        download_mode="skill_md_only",
    ),
    "performance": SkillSpec(
        name="performance",
        repo="addyosmani/web-quality-skills",
        repo_path="skills/performance",
        sdlc_phase="review",
        description="Web performance optimization and auditing",
        download_mode="skill_md_only",
    ),
    # wshobson/agents — database pro pack
    "database-migrations": SkillSpec(
        name="database-migrations",
        repo="wshobson/agents",
        repo_path="plugins/database-management/skills/database-migrations",
        sdlc_phase="database",
        description="Safe database migration patterns and rollbacks",
        download_mode="skill_md_only",
    ),
    "query-efficiency-auditor": SkillSpec(
        name="query-efficiency-auditor",
        repo="wshobson/agents",
        repo_path="plugins/database-management/skills/query-efficiency-auditor",
        sdlc_phase="database",
        description="SQL query performance analysis and optimization",
        download_mode="skill_md_only",
    ),
}


# ── Template → framework-specific skill names ─────────────────────────

TEMPLATE_SKILLS: dict[str, list[str]] = {
    "generic": [],
    "fastapi": [
        "modern-python",
        "property-based-testing",
        "webapp-testing",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "github-actions-generator",
        "dockerfile-generator",
    ],
    "django": [
        "modern-python",
        "property-based-testing",
        "webapp-testing",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "github-actions-generator",
        "dockerfile-generator",
    ],
    "flask": [
        "modern-python",
        "property-based-testing",
        "webapp-testing",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "github-actions-generator",
        "dockerfile-generator",
    ],
    "nextjs": [
        "vercel-react-best-practices",
        "next-best-practices",
        "web-design-guidelines",
        "frontend-design",
        "tailwind-design-system",
        "webapp-testing",
        "github-actions-generator",
    ],
    "gin": [
        "property-based-testing",
        "static-analysis",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
    ],
    "echo": [
        "property-based-testing",
        "static-analysis",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
    ],
    "rust-cli": [
        "property-based-testing",
        "static-analysis",
        "github-actions-generator",
    ],
    "rust-web": [
        "property-based-testing",
        "static-analysis",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
    ],
    "rails": [
        "property-based-testing",
        "webapp-testing",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
    ],
    "spring": [
        "property-based-testing",
        "static-analysis",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
    ],
    "dotnet": [
        "property-based-testing",
        "static-analysis",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
    ],
    "laravel": [
        "property-based-testing",
        "webapp-testing",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
    ],
    "express": [
        "property-based-testing",
        "webapp-testing",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
    ],
    "phoenix": [
        "property-based-testing",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
    ],
    "go-std": [
        "property-based-testing",
        "static-analysis",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
    ],
}


# ── Workflow → cross-cutting skill names ───────────────────────────────
# Each workflow level is cumulative (includes all skills from simpler levels).

_STANDARD_SKILLS = [
    "owasp-security",
    "insecure-defaults",
    "requesting-code-review",
    "receiving-code-review",
    "finishing-a-development-branch",
]

_SPEC_DRIVEN_SKILLS = [
    *_STANDARD_SKILLS,
    "test-driven-development",
    "systematic-debugging",
    "brainstorming",
    "writing-plans",
    "executing-plans",
    "using-git-worktrees",
]

_VERIFY_HEAVY_SKILLS = [
    *_SPEC_DRIVEN_SKILLS,
    "verification-before-completion",
    "subagent-driven-development",
    "skill-creator",
]

WORKFLOW_SKILLS: dict[str, list[str]] = {
    "speedrun": [],
    "standard": _STANDARD_SKILLS,
    "spec-driven": _SPEC_DRIVEN_SKILLS,
    "gtd-lite": _SPEC_DRIVEN_SKILLS,  # same as spec-driven
    "verify-heavy": _VERIFY_HEAVY_SKILLS,
}


# ── Phase gating per workflow ──────────────────────────────────────────
# Same logic as the old skill_phases from workflow JSONs.
# Values: True, False, "bundled_only", "if_applicable"

WORKFLOW_PHASES: dict[str, dict[str, Any]] = {
    "speedrun": {
        "coding": True,
        "testing": "bundled_only",
        "review": False,
        "security": False,
        "database": "if_applicable",
        "devops": False,
        "planning": False,
    },
    "standard": {
        "coding": True,
        "testing": True,
        "review": True,
        "security": True,
        "database": "if_applicable",
        "devops": True,
        "planning": False,
    },
    "spec-driven": {
        "coding": True,
        "testing": True,
        "review": True,
        "security": True,
        "database": "if_applicable",
        "devops": True,
        "planning": True,
    },
    "gtd-lite": {
        "coding": True,
        "testing": True,
        "review": True,
        "security": True,
        "database": "if_applicable",
        "devops": True,
        "planning": True,
    },
    "verify-heavy": {
        "coding": True,
        "testing": True,
        "review": True,
        "security": True,
        "database": "if_applicable",
        "devops": True,
        "planning": True,
    },
}

# ── Optional skill packs ──────────────────────────────────────────────

SKILL_PACKS: dict[str, SkillPackSpec] = {
    "security": SkillPackSpec(
        name="security",
        label="Security Deep Dive",
        description="Supply chain auditing, variant analysis, sharp edges, differential review",
        skill_names=[
            "supply-chain-risk-auditor",
            "variant-analysis",
            "sharp-edges",
            "differential-review",
        ],
        suggested_templates=None,  # all templates
    ),
    "devops": SkillPackSpec(
        name="devops",
        label="DevOps & IaC",
        description="Terraform, Kubernetes, monitoring, GitOps workflows",
        skill_names=[
            "iac-terraform",
            "k8s-troubleshooter",
            "monitoring-observability",
            "gitops-workflows",
        ],
        suggested_templates=None,  # all templates
    ),
    "web-quality": SkillPackSpec(
        name="web-quality",
        label="Web Quality",
        description="Web quality auditing, accessibility, performance optimization",
        skill_names=[
            "web-quality-audit",
            "accessibility",
            "performance",
        ],
        suggested_templates=["nextjs"],  # suggested for frontend
    ),
    "database-pro": SkillPackSpec(
        name="database-pro",
        label="Database Pro",
        description="Database migration patterns, query efficiency auditing",
        skill_names=[
            "database-migrations",
            "query-efficiency-auditor",
        ],
        suggested_templates=None,  # all templates (DB MCPs determine applicability)
    ),
}

# DB services that trigger "if_applicable" database phase.
_DB_SERVICES = {"postgres", "mysql", "sqlite"}


def _phase_is_active(
    phases: dict[str, Any],
    phase: str,
    default_mcps: list[str] | None = None,
) -> bool:
    """Check if a phase is active for skill inclusion.

    Returns True for: True
    Returns False for: False, "bundled_only", "if_applicable" (unless resolved), absent
    """
    if not phase:
        return False
    value = phases.get(phase)
    if value is True:
        return True
    if value == "if_applicable" and default_mcps is not None:
        return bool(set(default_mcps) & _DB_SERVICES)
    return False


def resolve_skills(
    template: str,
    workflow: str,
    default_mcps: list[str] | None = None,
    packs: list[str] | None = None,
) -> list[SkillSpec]:
    """Resolve the full list of skills to install for a template × workflow combo.

    Combines:
    1. Cross-cutting workflow skills (always installed for the workflow level)
    2. Framework-specific template skills (gated by workflow phase settings)
    3. Optional skill pack skills (not phase-gated — explicit user opt-in)

    Deduplicates by name (workflow wins over template, packs win over both).

    Args:
        template: Template name (e.g. "fastapi", "nextjs").
        workflow: Workflow name (e.g. "standard", "speedrun").
        default_mcps: Template's default MCP servers (used to resolve "if_applicable").
        packs: Optional list of skill pack names (e.g. ["security", "devops"]).

    Returns:
        Deduplicated list of SkillSpec objects to install.
    """
    if default_mcps is None:
        default_mcps = []

    phases = dict(WORKFLOW_PHASES.get(workflow, {}))

    # Collect template-specific skills, gated by active phases
    template_skill_names = TEMPLATE_SKILLS.get(template, [])
    template_specs: list[SkillSpec] = []
    for name in template_skill_names:
        spec = SKILL_CATALOG.get(name)
        if spec and _phase_is_active(phases, spec.sdlc_phase, default_mcps):
            template_specs.append(spec)

    # Collect cross-cutting workflow skills (not phase-gated — these are
    # explicitly curated per workflow level)
    workflow_skill_names = WORKFLOW_SKILLS.get(workflow, [])
    workflow_specs: list[SkillSpec] = []
    for name in workflow_skill_names:
        spec = SKILL_CATALOG.get(name)
        if spec:
            workflow_specs.append(spec)

    # Collect skill pack skills (not phase-gated — explicit user opt-in)
    pack_specs: list[SkillSpec] = []
    for pack_name in packs or []:
        pack = SKILL_PACKS.get(pack_name)
        if pack:
            for skill_name in pack.skill_names:
                spec = SKILL_CATALOG.get(skill_name)
                if spec:
                    pack_specs.append(spec)

    # Deduplicate: template first, then workflow, then packs (last wins)
    seen: dict[str, SkillSpec] = {}
    for spec in template_specs:
        seen[spec.name] = spec
    for spec in workflow_specs:
        seen[spec.name] = spec
    for spec in pack_specs:
        seen[spec.name] = spec

    return list(seen.values())
