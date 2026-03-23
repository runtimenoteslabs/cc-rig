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
    branch: str = "main"  # Git branch for raw content URLs


@dataclass
class SkillPackSpec:
    """Optional skill pack selectable in the wizard."""

    name: str  # "security"
    label: str  # "Security Deep Dive"
    description: str  # one-line for wizard
    skill_names: list[str]  # refs into SKILL_CATALOG
    suggested_templates: list[str] | None = None  # None = all, list = specific


# ── All downloadable skills (78 unique) ────────────────────────────────

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
    # ── garrytan/gstack — 6 process skills ─────────────────────────────
    "plan-ceo-review": SkillSpec(
        name="plan-ceo-review",
        repo="garrytan/gstack",
        repo_path="plan-ceo-review",
        sdlc_phase="planning",
        description="Founder/CEO product review with 9 prime directives",
    ),
    "plan-eng-review": SkillSpec(
        name="plan-eng-review",
        repo="garrytan/gstack",
        repo_path="plan-eng-review",
        sdlc_phase="planning",
        description="Engineering architecture lock, data flow, edge cases",
    ),
    "plan-design-review": SkillSpec(
        name="plan-design-review",
        repo="garrytan/gstack",
        repo_path="plan-design-review",
        sdlc_phase="review",
        description="80-item design audit, AI slop detection",
    ),
    "gstack-review": SkillSpec(
        name="gstack-review",
        repo="garrytan/gstack",
        repo_path="review",
        sdlc_phase="review",
        description="Two-pass staff engineer review (critical + informational)",
        download_mode="full_tree",
    ),
    "ship": SkillSpec(
        name="ship",
        repo="garrytan/gstack",
        repo_path="ship",
        sdlc_phase="devops",
        description="8-step release pipeline with preflight checks",
    ),
    "document-release": SkillSpec(
        name="document-release",
        repo="garrytan/gstack",
        repo_path="document-release",
        sdlc_phase="devops",
        description="Post-launch documentation update",
    ),
    # mattpocock/skills — 7 process skills
    "grill-me": SkillSpec(
        name="grill-me",
        repo="mattpocock/skills",
        repo_path="grill-me",
        sdlc_phase="planning",
        description="Exhaustive requirements interview",
    ),
    "write-a-prd": SkillSpec(
        name="write-a-prd",
        repo="mattpocock/skills",
        repo_path="write-a-prd",
        sdlc_phase="planning",
        description="PRD creation through interview and codebase exploration",
    ),
    "prd-to-issues": SkillSpec(
        name="prd-to-issues",
        repo="mattpocock/skills",
        repo_path="prd-to-issues",
        sdlc_phase="planning",
        description="PRD to vertical slice GitHub issues",
    ),
    "mp-tdd": SkillSpec(
        name="mp-tdd",
        repo="mattpocock/skills",
        repo_path="tdd",
        sdlc_phase="testing",
        description="Red-green-refactor with vertical slicing",
        download_mode="full_tree",
    ),
    "improve-codebase-architecture": SkillSpec(
        name="improve-codebase-architecture",
        repo="mattpocock/skills",
        repo_path="improve-codebase-architecture",
        sdlc_phase="coding",
        description="Module deepening refactors",
        download_mode="full_tree",
    ),
    "triage-issue": SkillSpec(
        name="triage-issue",
        repo="mattpocock/skills",
        repo_path="triage-issue",
        sdlc_phase="coding",
        description="Bug investigation and root cause analysis",
    ),
    "design-an-interface": SkillSpec(
        name="design-an-interface",
        repo="mattpocock/skills",
        repo_path="design-an-interface",
        sdlc_phase="coding",
        description="Interface design using Ousterhout deep modules",
    ),
    # OthmanAdi/planning-with-files — 1 process skill
    "planning-with-files": SkillSpec(
        name="planning-with-files",
        repo="OthmanAdi/planning-with-files",
        repo_path="skills/planning-with-files",
        sdlc_phase="planning",
        description="Persistent task tracking with task_plan.md, findings.md, progress.md",
        download_mode="full_tree",
        branch="master",
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
    # ahmedasmar/devops-claude-skills — devops pack
    "iac-terraform": SkillSpec(
        name="iac-terraform",
        repo="ahmedasmar/devops-claude-skills",
        repo_path="iac-terraform/skills",
        sdlc_phase="devops",
        description="Terraform IaC patterns and best practices",
        download_mode="skill_md_only",
    ),
    "k8s-troubleshooter": SkillSpec(
        name="k8s-troubleshooter",
        repo="ahmedasmar/devops-claude-skills",
        repo_path="k8s-troubleshooter/skills",
        sdlc_phase="devops",
        description="Kubernetes debugging and troubleshooting",
        download_mode="skill_md_only",
    ),
    "monitoring-observability": SkillSpec(
        name="monitoring-observability",
        repo="ahmedasmar/devops-claude-skills",
        repo_path="monitoring-observability",
        sdlc_phase="devops",
        description="Monitoring, alerting, and observability patterns",
        download_mode="skill_md_only",
    ),
    "gitops-workflows": SkillSpec(
        name="gitops-workflows",
        repo="ahmedasmar/devops-claude-skills",
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
    # peteromallet/desloppify — 1 skill
    "desloppify": SkillSpec(
        name="desloppify",
        repo="peteromallet/desloppify",
        repo_path="docs",
        sdlc_phase="review",
        description="Codebase quality scanner with 20 quality dimensions and anti-gaming scoring",
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
    # affaan-m/everything-claude-code — 23 skills (v2.1)
    # Python (2 cross-framework)
    "ecc-python-patterns": SkillSpec(
        name="ecc-python-patterns",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/python-patterns",
        sdlc_phase="coding",
        description="Python idioms, type hints, async patterns, packaging",
    ),
    "ecc-python-testing": SkillSpec(
        name="ecc-python-testing",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/python-testing",
        sdlc_phase="testing",
        description="pytest patterns, fixtures, mocking, coverage strategies",
    ),
    # Django (4)
    "ecc-django-patterns": SkillSpec(
        name="ecc-django-patterns",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/django-patterns",
        sdlc_phase="coding",
        description="Django models, views, forms, signals, middleware patterns",
    ),
    "ecc-django-security": SkillSpec(
        name="ecc-django-security",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/django-security",
        sdlc_phase="security",
        description="Django CSRF, auth, permissions, SQL injection prevention",
    ),
    "ecc-django-tdd": SkillSpec(
        name="ecc-django-tdd",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/django-tdd",
        sdlc_phase="testing",
        description="Django test client, factories, fixtures, coverage",
    ),
    "ecc-django-verification": SkillSpec(
        name="ecc-django-verification",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/django-verification",
        sdlc_phase="review",
        description="Django deployment checklist, migration verification",
    ),
    # Spring Boot (4)
    "ecc-springboot-patterns": SkillSpec(
        name="ecc-springboot-patterns",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/springboot-patterns",
        sdlc_phase="coding",
        description="Spring Boot DI, JPA, REST controllers, configuration",
    ),
    "ecc-springboot-security": SkillSpec(
        name="ecc-springboot-security",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/springboot-security",
        sdlc_phase="security",
        description="Spring Security, OAuth2, CORS, input validation",
    ),
    "ecc-springboot-tdd": SkillSpec(
        name="ecc-springboot-tdd",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/springboot-tdd",
        sdlc_phase="testing",
        description="JUnit 5, MockMvc, Testcontainers, integration tests",
    ),
    "ecc-springboot-verification": SkillSpec(
        name="ecc-springboot-verification",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/springboot-verification",
        sdlc_phase="review",
        description="Spring Boot health checks, actuator, deployment verification",
    ),
    # Laravel (4)
    "ecc-laravel-patterns": SkillSpec(
        name="ecc-laravel-patterns",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/laravel-patterns",
        sdlc_phase="coding",
        description="Laravel Eloquent, Blade, middleware, service providers",
    ),
    "ecc-laravel-security": SkillSpec(
        name="ecc-laravel-security",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/laravel-security",
        sdlc_phase="security",
        description="Laravel auth, gates, policies, CSRF, encryption",
    ),
    "ecc-laravel-tdd": SkillSpec(
        name="ecc-laravel-tdd",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/laravel-tdd",
        sdlc_phase="testing",
        description="PHPUnit, feature tests, database testing, Dusk",
    ),
    "ecc-laravel-verification": SkillSpec(
        name="ecc-laravel-verification",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/laravel-verification",
        sdlc_phase="review",
        description="Laravel deployment, queue verification, config caching",
    ),
    # Go (2)
    "ecc-golang-patterns": SkillSpec(
        name="ecc-golang-patterns",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/golang-patterns",
        sdlc_phase="coding",
        description="Go idioms, error handling, concurrency, interface design",
    ),
    "ecc-golang-testing": SkillSpec(
        name="ecc-golang-testing",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/golang-testing",
        sdlc_phase="testing",
        description="Go table tests, benchmarks, test helpers, mocking",
    ),
    # Rust (2)
    "ecc-rust-patterns": SkillSpec(
        name="ecc-rust-patterns",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/rust-patterns",
        sdlc_phase="coding",
        description="Rust ownership, lifetimes, traits, error handling patterns",
    ),
    "ecc-rust-testing": SkillSpec(
        name="ecc-rust-testing",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/rust-testing",
        sdlc_phase="testing",
        description="Rust unit tests, integration tests, proptest, criterion",
    ),
    # Cross-cutting SDLC (5)
    "ecc-tdd-workflow": SkillSpec(
        name="ecc-tdd-workflow",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/tdd-workflow",
        sdlc_phase="testing",
        description="TDD methodology with 80%+ coverage targets",
    ),
    "ecc-verification-loop": SkillSpec(
        name="ecc-verification-loop",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/verification-loop",
        sdlc_phase="review",
        description="Pre-PR verification gate with automated checks",
    ),
    "ecc-search-first": SkillSpec(
        name="ecc-search-first",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/search-first",
        sdlc_phase="planning",
        description="Research-before-coding workflow for unfamiliar codebases",
    ),
    "ecc-coding-standards": SkillSpec(
        name="ecc-coding-standards",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/coding-standards",
        sdlc_phase="coding",
        description="Universal coding standards: KISS, DRY, YAGNI enforcement",
    ),
    "ecc-api-design": SkillSpec(
        name="ecc-api-design",
        repo="affaan-m/everything-claude-code",
        repo_path="skills/api-design",
        sdlc_phase="coding",
        description="REST API design, pagination, error handling, versioning",
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
        "ecc-python-patterns",
        "ecc-python-testing",
    ],
    "django": [
        "modern-python",
        "property-based-testing",
        "webapp-testing",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "github-actions-generator",
        "dockerfile-generator",
        "ecc-python-patterns",
        "ecc-python-testing",
        "ecc-django-patterns",
        "ecc-django-security",
        "ecc-django-tdd",
        "ecc-django-verification",
    ],
    "flask": [
        "modern-python",
        "property-based-testing",
        "webapp-testing",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "github-actions-generator",
        "dockerfile-generator",
        "ecc-python-patterns",
        "ecc-python-testing",
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
        "ecc-golang-patterns",
        "ecc-golang-testing",
    ],
    "echo": [
        "property-based-testing",
        "static-analysis",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
        "ecc-golang-patterns",
        "ecc-golang-testing",
    ],
    "rust-cli": [
        "property-based-testing",
        "static-analysis",
        "github-actions-generator",
        "ecc-rust-patterns",
        "ecc-rust-testing",
    ],
    "rust-web": [
        "property-based-testing",
        "static-analysis",
        "supabase-postgres-best-practices",
        "planetscale-postgresql",
        "dockerfile-generator",
        "github-actions-generator",
        "ecc-rust-patterns",
        "ecc-rust-testing",
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
        "ecc-springboot-patterns",
        "ecc-springboot-security",
        "ecc-springboot-tdd",
        "ecc-springboot-verification",
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
        "ecc-laravel-patterns",
        "ecc-laravel-security",
        "ecc-laravel-tdd",
        "ecc-laravel-verification",
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
        "ecc-golang-patterns",
        "ecc-golang-testing",
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
    "gstack": _STANDARD_SKILLS,
    "aihero": _SPEC_DRIVEN_SKILLS,
    "spec-driven": _SPEC_DRIVEN_SKILLS,
    "superpowers": _VERIFY_HEAVY_SKILLS,
    "gtd": _SPEC_DRIVEN_SKILLS,
    # Backward compat aliases
    "gtd-lite": _SPEC_DRIVEN_SKILLS,
    "verify-heavy": _VERIFY_HEAVY_SKILLS,
}


# ── Workflow → process skill names (curated community skills) ────────
# Process skills define the workflow process itself (e.g., plan/review/ship).
# These are ADDITIONAL to WORKFLOW_SKILLS (cross-cutting security/review skills).

WORKFLOW_PROCESS_SKILLS: dict[str, list[str]] = {
    "speedrun": [],
    "standard": [],
    "gstack": [
        "plan-ceo-review",
        "plan-eng-review",
        "plan-design-review",
        "gstack-review",
        "ship",
        "document-release",
    ],
    "aihero": [
        "grill-me",
        "write-a-prd",
        "prd-to-issues",
        "mp-tdd",
        "improve-codebase-architecture",
        "triage-issue",
        "design-an-interface",
    ],
    "spec-driven": [
        "write-a-prd",
        "prd-to-issues",
        "writing-plans",
        "executing-plans",
    ],
    "superpowers": [
        "brainstorming",
        "writing-plans",
        "executing-plans",
        "test-driven-development",
        "systematic-debugging",
        "requesting-code-review",
        "receiving-code-review",
        "verification-before-completion",
        "subagent-driven-development",
        "using-git-worktrees",
        "finishing-a-development-branch",
    ],
    "gtd": [
        "planning-with-files",
        "writing-plans",
        "executing-plans",
    ],
    # Backward compat aliases
    "gtd-lite": [],
    "verify-heavy": [],
}


# ── Phase gating per workflow ──────────────────────────────────────────
# Same logic as the old skill_phases from workflow JSONs.
# Values: True, False, "bundled_only", "if_applicable"

_ALL_PHASES_ON = {
    "coding": True,
    "testing": True,
    "review": True,
    "security": True,
    "database": "if_applicable",
    "devops": True,
    "planning": True,
}

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
    "gstack": {
        "coding": True,
        "testing": True,
        "review": True,
        "security": True,
        "database": "if_applicable",
        "devops": True,
        "planning": True,
    },
    "aihero": dict(_ALL_PHASES_ON),
    "spec-driven": dict(_ALL_PHASES_ON),
    "superpowers": dict(_ALL_PHASES_ON),
    "gtd": dict(_ALL_PHASES_ON),
    # Backward compat aliases
    "gtd-lite": dict(_ALL_PHASES_ON),
    "verify-heavy": dict(_ALL_PHASES_ON),
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
    "code-quality": SkillPackSpec(
        name="code-quality",
        label="Code Quality",
        description="Desloppify codebase health scanner — 20 quality dimensions, anti-gaming",
        skill_names=["desloppify"],
        suggested_templates=None,  # all templates
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
    "ecc-sdlc": SkillPackSpec(
        name="ecc-sdlc",
        label="ECC SDLC Suite",
        description="TDD workflow, verification loop, search-first, coding standards, API design",
        skill_names=[
            "ecc-tdd-workflow",
            "ecc-verification-loop",
            "ecc-search-first",
            "ecc-coding-standards",
            "ecc-api-design",
        ],
        suggested_templates=None,  # all templates
    ),
}

# DB services that trigger "if_applicable" database phase.
_DB_SERVICES = {"postgres", "mysql", "sqlite"}


def compute_pack_overlap(
    workflow: str,
    pack_name: str,
) -> tuple:
    """Compute pack overlap with workflow skills.

    Returns:
        (direct_overlap_count, total_pack_skills, workflow_is_comprehensive)
    """
    pack = SKILL_PACKS.get(pack_name)
    if not pack:
        return (0, 0, False)

    all_workflow_skills: set = set(WORKFLOW_SKILLS.get(workflow, []))
    all_workflow_skills.update(WORKFLOW_PROCESS_SKILLS.get(workflow, []))

    total = len(pack.skill_names)
    overlap = sum(1 for s in pack.skill_names if s in all_workflow_skills)

    # "Comprehensive" = workflow has 8+ total skills (process + cross-cutting)
    is_comprehensive = len(all_workflow_skills) >= 8

    return (overlap, total, is_comprehensive)


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
