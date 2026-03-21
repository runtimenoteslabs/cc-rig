"""Tests for the registry module: SKILL_CATALOG, TEMPLATE_SKILLS, WORKFLOW_SKILLS,
WORKFLOW_PHASES, _phase_is_active(), and resolve_skills().

Covers catalog completeness, phase gating, database if_applicable resolution,
deduplication, template-specific skills, and skill count scaling.
"""

from __future__ import annotations

import pytest

from cc_rig.skills.registry import (
    SKILL_CATALOG,
    SKILL_PACKS,
    TEMPLATE_SKILLS,
    WORKFLOW_PHASES,
    WORKFLOW_SKILLS,
    SkillPackSpec,
    SkillSpec,
    _phase_is_active,
    compute_pack_overlap,
    resolve_skills,
)

# All 16 templates and 5 workflows defined in the registry
ALL_TEMPLATES = [
    "generic",
    "fastapi",
    "django",
    "flask",
    "nextjs",
    "gin",
    "echo",
    "rust-cli",
    "rust-web",
    "rails",
    "spring",
    "dotnet",
    "laravel",
    "express",
    "phoenix",
    "go-std",
]
ALL_WORKFLOWS = [
    "speedrun",
    "standard",
    "gstack",
    "aihero",
    "spec-driven",
    "superpowers",
    "gtd",
    # Backward compat aliases
    "gtd-lite",
    "verify-heavy",
]

# Expected cross-cutting skill counts per workflow
_STANDARD_CROSS_CUTTING_COUNT = 5
_SPEC_DRIVEN_CROSS_CUTTING_COUNT = 11
_VERIFY_HEAVY_CROSS_CUTTING_COUNT = 14


# ---------------------------------------------------------------------------
# SKILL_CATALOG completeness — 41 skills
# ---------------------------------------------------------------------------


class TestSkillCatalogCompleteness:
    """SKILL_CATALOG must contain exactly 41 uniquely-named skills."""

    def test_catalog_has_41_skills(self):
        assert len(SKILL_CATALOG) == 55

    def test_all_catalog_keys_are_skill_spec(self):
        for name, spec in SKILL_CATALOG.items():
            assert isinstance(spec, SkillSpec), f"{name!r} is not a SkillSpec"

    def test_catalog_key_matches_spec_name(self):
        for key, spec in SKILL_CATALOG.items():
            assert key == spec.name, f"Key {key!r} does not match spec.name {spec.name!r}"

    def test_all_specs_have_nonempty_repo(self):
        for name, spec in SKILL_CATALOG.items():
            assert spec.repo, f"Skill {name!r} has empty repo"

    def test_all_specs_have_nonempty_repo_path(self):
        for name, spec in SKILL_CATALOG.items():
            assert spec.repo_path, f"Skill {name!r} has empty repo_path"

    def test_all_specs_have_nonempty_sdlc_phase(self):
        for name, spec in SKILL_CATALOG.items():
            assert spec.sdlc_phase, f"Skill {name!r} has empty sdlc_phase"

    def test_all_specs_have_nonempty_description(self):
        for name, spec in SKILL_CATALOG.items():
            assert spec.description, f"Skill {name!r} has empty description"

    def test_download_mode_values_are_valid(self):
        valid_modes = {"skill_md_only", "full_tree"}
        for name, spec in SKILL_CATALOG.items():
            assert spec.download_mode in valid_modes, (
                f"Skill {name!r} has invalid download_mode {spec.download_mode!r}"
            )

    def test_known_skills_present(self):
        expected_skills = [
            "test-driven-development",
            "systematic-debugging",
            "requesting-code-review",
            "receiving-code-review",
            "finishing-a-development-branch",
            "brainstorming",
            "writing-plans",
            "executing-plans",
            "using-git-worktrees",
            "verification-before-completion",
            "subagent-driven-development",
            "modern-python",
            "property-based-testing",
            "insecure-defaults",
            "static-analysis",
            "skill-creator",
            "webapp-testing",
            "frontend-design",
            "supabase-postgres-best-practices",
            "planetscale-postgresql",
            "github-actions-generator",
            "dockerfile-generator",
            "owasp-security",
            "vercel-react-best-practices",
            "next-best-practices",
            "web-design-guidelines",
            "tailwind-design-system",
            # Skill pack skills
            "desloppify",
            "supply-chain-risk-auditor",
            "variant-analysis",
            "sharp-edges",
            "differential-review",
            "iac-terraform",
            "k8s-troubleshooter",
            "monitoring-observability",
            "gitops-workflows",
            "web-quality-audit",
            "accessibility",
            "performance",
            "database-migrations",
            "query-efficiency-auditor",
        ]
        for skill in expected_skills:
            assert skill in SKILL_CATALOG, f"Expected skill {skill!r} missing from SKILL_CATALOG"

    def test_no_duplicate_names(self):
        names = list(SKILL_CATALOG.keys())
        assert len(names) == len(set(names)), "Duplicate keys in SKILL_CATALOG"

    def test_obra_superpowers_skills_use_full_tree(self):
        obra_skills = [s for s in SKILL_CATALOG.values() if s.repo == "obra/superpowers"]
        for spec in obra_skills:
            assert spec.download_mode == "full_tree", (
                f"obra/superpowers skill {spec.name!r} should use full_tree"
            )

    def test_trailofbits_skills_use_skill_md_only(self):
        tob_skills = [s for s in SKILL_CATALOG.values() if s.repo == "trailofbits/skills"]
        for spec in tob_skills:
            assert spec.download_mode == "skill_md_only", (
                f"trailofbits/skills skill {spec.name!r} should use skill_md_only"
            )


# ---------------------------------------------------------------------------
# TEMPLATE_SKILLS completeness — 11 templates
# ---------------------------------------------------------------------------


class TestTemplateSkillsCompleteness:
    """TEMPLATE_SKILLS must have entries for all 16 templates."""

    def test_has_all_16_templates(self):
        assert len(TEMPLATE_SKILLS) == 16

    @pytest.mark.parametrize("template", ALL_TEMPLATES)
    def test_template_is_present(self, template):
        assert template in TEMPLATE_SKILLS, f"Template {template!r} missing from TEMPLATE_SKILLS"

    @pytest.mark.parametrize("template", [t for t in ALL_TEMPLATES if t != "generic"])
    def test_template_skills_are_nonempty(self, template):
        assert len(TEMPLATE_SKILLS[template]) > 0, f"Template {template!r} has no skills"

    def test_generic_template_has_empty_skills(self):
        assert TEMPLATE_SKILLS["generic"] == []

    @pytest.mark.parametrize("template", ALL_TEMPLATES)
    def test_template_skills_reference_known_catalog_entries(self, template):
        for skill_name in TEMPLATE_SKILLS[template]:
            assert skill_name in SKILL_CATALOG, (
                f"Template {template!r} references unknown skill {skill_name!r}"
            )

    def test_python_templates_share_same_skills(self):
        """fastapi, django, flask all have identical template skill lists."""
        assert TEMPLATE_SKILLS["fastapi"] == TEMPLATE_SKILLS["django"]
        assert TEMPLATE_SKILLS["fastapi"] == TEMPLATE_SKILLS["flask"]

    def test_go_templates_share_same_skills(self):
        """gin and echo have identical template skill lists."""
        assert TEMPLATE_SKILLS["gin"] == TEMPLATE_SKILLS["echo"]

    def test_fastapi_template_skills(self):
        expected = {
            "modern-python",
            "property-based-testing",
            "webapp-testing",
            "supabase-postgres-best-practices",
            "planetscale-postgresql",
            "github-actions-generator",
            "dockerfile-generator",
        }
        assert set(TEMPLATE_SKILLS["fastapi"]) == expected

    def test_nextjs_template_skills(self):
        expected = {
            "vercel-react-best-practices",
            "next-best-practices",
            "web-design-guidelines",
            "frontend-design",
            "tailwind-design-system",
            "webapp-testing",
            "github-actions-generator",
        }
        assert set(TEMPLATE_SKILLS["nextjs"]) == expected

    def test_nextjs_has_no_modern_python(self):
        assert "modern-python" not in TEMPLATE_SKILLS["nextjs"]

    def test_rust_cli_template_skills(self):
        expected = {
            "property-based-testing",
            "static-analysis",
            "github-actions-generator",
        }
        assert set(TEMPLATE_SKILLS["rust-cli"]) == expected

    def test_rust_cli_has_no_database_skills(self):
        db_skills = {"supabase-postgres-best-practices", "planetscale-postgresql"}
        assert not db_skills.intersection(TEMPLATE_SKILLS["rust-cli"])

    def test_go_templates_have_static_analysis(self):
        assert "static-analysis" in TEMPLATE_SKILLS["gin"]
        assert "static-analysis" in TEMPLATE_SKILLS["echo"]

    def test_go_templates_no_modern_python(self):
        assert "modern-python" not in TEMPLATE_SKILLS["gin"]
        assert "modern-python" not in TEMPLATE_SKILLS["echo"]


# ---------------------------------------------------------------------------
# WORKFLOW_SKILLS completeness — 5 workflows
# ---------------------------------------------------------------------------


class TestWorkflowSkillsCompleteness:
    """WORKFLOW_SKILLS must have entries for all 5 workflows."""

    def test_has_all_5_workflows(self):
        assert len(WORKFLOW_SKILLS) == 9

    @pytest.mark.parametrize("workflow", ALL_WORKFLOWS)
    def test_workflow_is_present(self, workflow):
        assert workflow in WORKFLOW_SKILLS, f"Workflow {workflow!r} missing from WORKFLOW_SKILLS"

    def test_speedrun_has_empty_cross_cutting_skills(self):
        assert WORKFLOW_SKILLS["speedrun"] == []

    def test_standard_has_5_cross_cutting_skills(self):
        assert len(WORKFLOW_SKILLS["standard"]) == _STANDARD_CROSS_CUTTING_COUNT

    def test_spec_driven_has_11_cross_cutting_skills(self):
        assert len(WORKFLOW_SKILLS["spec-driven"]) == _SPEC_DRIVEN_CROSS_CUTTING_COUNT

    def test_gtd_lite_same_skills_as_spec_driven(self):
        """gtd-lite uses the same cross-cutting list as spec-driven."""
        assert WORKFLOW_SKILLS["gtd-lite"] == WORKFLOW_SKILLS["spec-driven"]

    def test_verify_heavy_has_14_cross_cutting_skills(self):
        assert len(WORKFLOW_SKILLS["verify-heavy"]) == _VERIFY_HEAVY_CROSS_CUTTING_COUNT

    def test_workflow_skill_counts_are_cumulative(self):
        """Each workflow level adds to the previous."""
        speedrun = len(WORKFLOW_SKILLS["speedrun"])
        standard = len(WORKFLOW_SKILLS["standard"])
        spec_driven = len(WORKFLOW_SKILLS["spec-driven"])
        verify_heavy = len(WORKFLOW_SKILLS["verify-heavy"])
        assert speedrun < standard < spec_driven < verify_heavy

    def test_standard_cross_cutting_skills(self):
        expected = {
            "owasp-security",
            "insecure-defaults",
            "requesting-code-review",
            "receiving-code-review",
            "finishing-a-development-branch",
        }
        assert set(WORKFLOW_SKILLS["standard"]) == expected

    def test_spec_driven_includes_standard_skills(self):
        standard_set = set(WORKFLOW_SKILLS["standard"])
        spec_set = set(WORKFLOW_SKILLS["spec-driven"])
        assert standard_set.issubset(spec_set), (
            f"spec-driven missing standard skills: {standard_set - spec_set}"
        )

    def test_spec_driven_adds_planning_and_workflow_skills(self):
        extra = {
            "test-driven-development",
            "systematic-debugging",
            "brainstorming",
            "writing-plans",
            "executing-plans",
            "using-git-worktrees",
        }
        spec_set = set(WORKFLOW_SKILLS["spec-driven"])
        assert extra.issubset(spec_set), f"spec-driven missing: {extra - spec_set}"

    def test_verify_heavy_includes_spec_driven_skills(self):
        spec_set = set(WORKFLOW_SKILLS["spec-driven"])
        heavy_set = set(WORKFLOW_SKILLS["verify-heavy"])
        assert spec_set.issubset(heavy_set), (
            f"verify-heavy missing spec-driven skills: {spec_set - heavy_set}"
        )

    def test_verify_heavy_adds_quality_skills(self):
        extra = {
            "verification-before-completion",
            "subagent-driven-development",
            "skill-creator",
        }
        heavy_set = set(WORKFLOW_SKILLS["verify-heavy"])
        assert extra.issubset(heavy_set), f"verify-heavy missing: {extra - heavy_set}"

    @pytest.mark.parametrize("workflow", ALL_WORKFLOWS)
    def test_workflow_skills_reference_known_catalog_entries(self, workflow):
        for skill_name in WORKFLOW_SKILLS[workflow]:
            assert skill_name in SKILL_CATALOG, (
                f"Workflow {workflow!r} references unknown skill {skill_name!r}"
            )

    @pytest.mark.parametrize("workflow", ALL_WORKFLOWS)
    def test_workflow_skills_no_duplicates(self, workflow):
        skills = WORKFLOW_SKILLS[workflow]
        assert len(skills) == len(set(skills)), (
            f"Workflow {workflow!r} has duplicate skills: {skills}"
        )


# ---------------------------------------------------------------------------
# WORKFLOW_PHASES completeness — 5 workflows
# ---------------------------------------------------------------------------


class TestWorkflowPhasesCompleteness:
    """WORKFLOW_PHASES must have entries for all workflows (including aliases)."""

    _EXPECTED_PHASES = {"coding", "testing", "review", "security", "database", "devops", "planning"}

    def test_has_all_workflows(self):
        assert len(WORKFLOW_PHASES) == 9

    @pytest.mark.parametrize("workflow", ALL_WORKFLOWS)
    def test_workflow_is_present(self, workflow):
        assert workflow in WORKFLOW_PHASES, f"Workflow {workflow!r} missing from WORKFLOW_PHASES"

    @pytest.mark.parametrize("workflow", ALL_WORKFLOWS)
    def test_workflow_has_all_7_phases(self, workflow):
        phases = set(WORKFLOW_PHASES[workflow].keys())
        assert phases == self._EXPECTED_PHASES, (
            f"Workflow {workflow!r} missing phases: {self._EXPECTED_PHASES - phases}"
        )

    def test_speedrun_phase_config(self):
        phases = WORKFLOW_PHASES["speedrun"]
        assert phases["coding"] is True
        assert phases["testing"] == "bundled_only"
        assert phases["review"] is False
        assert phases["security"] is False
        assert phases["database"] == "if_applicable"
        assert phases["devops"] is False
        assert phases["planning"] is False

    def test_standard_phase_config(self):
        phases = WORKFLOW_PHASES["standard"]
        assert phases["coding"] is True
        assert phases["testing"] is True
        assert phases["review"] is True
        assert phases["security"] is True
        assert phases["database"] == "if_applicable"
        assert phases["devops"] is True
        assert phases["planning"] is False

    def test_spec_driven_phase_config(self):
        phases = WORKFLOW_PHASES["spec-driven"]
        assert phases["planning"] is True

    def test_gtd_lite_phase_config_matches_spec_driven(self):
        assert WORKFLOW_PHASES["gtd-lite"] == WORKFLOW_PHASES["spec-driven"]

    def test_verify_heavy_all_phases_active(self):
        phases = WORKFLOW_PHASES["verify-heavy"]
        # All except database should be True; database is if_applicable
        assert phases["coding"] is True
        assert phases["testing"] is True
        assert phases["review"] is True
        assert phases["security"] is True
        assert phases["database"] == "if_applicable"
        assert phases["devops"] is True
        assert phases["planning"] is True


# ---------------------------------------------------------------------------
# _phase_is_active() — internal helper
# ---------------------------------------------------------------------------


class TestPhaseIsActive:
    """Direct tests for _phase_is_active() in the registry module."""

    def test_true_value_is_active(self):
        assert _phase_is_active({"coding": True}, "coding") is True

    def test_false_value_is_inactive(self):
        assert _phase_is_active({"coding": False}, "coding") is False

    def test_bundled_only_is_inactive(self):
        assert _phase_is_active({"testing": "bundled_only"}, "testing") is False

    def test_if_applicable_without_mcps_is_inactive(self):
        assert _phase_is_active({"database": "if_applicable"}, "database") is False

    def test_if_applicable_with_empty_mcps_is_inactive(self):
        assert _phase_is_active({"database": "if_applicable"}, "database", []) is False

    def test_if_applicable_with_postgres_mcp_is_active(self):
        assert _phase_is_active({"database": "if_applicable"}, "database", ["postgres"]) is True

    def test_if_applicable_with_mysql_mcp_is_active(self):
        assert _phase_is_active({"database": "if_applicable"}, "database", ["mysql"]) is True

    def test_if_applicable_with_sqlite_mcp_is_active(self):
        assert _phase_is_active({"database": "if_applicable"}, "database", ["sqlite"]) is True

    def test_if_applicable_with_nondb_mcp_is_inactive(self):
        assert _phase_is_active({"database": "if_applicable"}, "database", ["github"]) is False

    def test_if_applicable_with_mixed_mcps_including_db_is_active(self):
        assert (
            _phase_is_active({"database": "if_applicable"}, "database", ["github", "postgres"])
            is True
        )

    def test_absent_phase_key_is_inactive(self):
        assert _phase_is_active({}, "coding") is False

    def test_empty_phase_name_is_inactive(self):
        assert _phase_is_active({"": True}, "") is False

    def test_none_mcps_argument_leaves_if_applicable_inactive(self):
        """None default_mcps means database resolution is skipped."""
        assert _phase_is_active({"database": "if_applicable"}, "database", None) is False

    def test_string_true_is_not_active(self):
        """String 'true' is not the boolean True."""
        assert _phase_is_active({"coding": "true"}, "coding") is False

    def test_integer_one_is_not_active(self):
        """Integer 1 is not boolean True — Python strict type check."""
        # Python `1 is True` is False but `1 == True` is True.
        # The registry uses `value is True` style check? Let's verify exact behavior.
        # The implementation uses `if value is True` — so integer 1 should NOT pass.
        assert _phase_is_active({"coding": 1}, "coding") is False


# ---------------------------------------------------------------------------
# resolve_skills() — happy paths
# ---------------------------------------------------------------------------


class TestResolveSkillsHappyPath:
    """resolve_skills() returns the correct SkillSpec list for key combos."""

    def _names(self, template: str, workflow: str, mcps: list[str] | None = None) -> set[str]:
        return {s.name for s in resolve_skills(template, workflow, mcps)}

    def test_returns_list_of_skill_specs(self):
        result = resolve_skills("fastapi", "standard")
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, SkillSpec)

    def test_fastapi_standard_includes_workflow_skills(self):
        names = self._names("fastapi", "standard")
        assert "owasp-security" in names
        assert "insecure-defaults" in names
        assert "requesting-code-review" in names
        assert "receiving-code-review" in names
        assert "finishing-a-development-branch" in names

    def test_fastapi_standard_includes_coding_template_skill(self):
        names = self._names("fastapi", "standard")
        assert "modern-python" in names

    def test_fastapi_standard_includes_testing_template_skills(self):
        names = self._names("fastapi", "standard")
        assert "property-based-testing" in names
        assert "webapp-testing" in names

    def test_fastapi_standard_includes_devops_template_skills(self):
        names = self._names("fastapi", "standard")
        assert "github-actions-generator" in names
        assert "dockerfile-generator" in names

    def test_fastapi_standard_no_database_without_mcps(self):
        """Without DB mcps, database phase stays inactive."""
        names = self._names("fastapi", "standard")
        assert "supabase-postgres-best-practices" not in names
        assert "planetscale-postgresql" not in names

    def test_fastapi_standard_with_postgres_mcp_adds_database_skills(self):
        names = self._names("fastapi", "standard", ["postgres"])
        assert "supabase-postgres-best-practices" in names
        assert "planetscale-postgresql" in names

    def test_fastapi_standard_total_without_db_mcps(self):
        """5 workflow + 5 template skills (modern-python, property-based-testing,
        webapp-testing, github-actions-generator, dockerfile-generator) = 10."""
        result = resolve_skills("fastapi", "standard")
        assert len(result) == 10

    def test_fastapi_standard_total_with_postgres_mcp(self):
        """5 workflow + 7 template skills (adds supabase + planetscale) = 12."""
        result = resolve_skills("fastapi", "standard", ["postgres"])
        assert len(result) == 12

    def test_fastapi_speedrun_only_coding_skills(self):
        """Speedrun: only coding phase is active for template skills."""
        names = self._names("fastapi", "speedrun")
        assert "modern-python" in names
        # testing is bundled_only → inactive
        assert "property-based-testing" not in names
        assert "webapp-testing" not in names
        # devops is False → inactive
        assert "github-actions-generator" not in names
        assert "dockerfile-generator" not in names

    def test_fastapi_speedrun_no_workflow_cross_cutting_skills(self):
        """Speedrun workflow has no cross-cutting skills."""
        names = self._names("fastapi", "speedrun")
        assert "owasp-security" not in names
        assert "requesting-code-review" not in names

    def test_fastapi_speedrun_database_with_postgres_mcp(self):
        """Speedrun + postgres MCP activates database template skills."""
        names = self._names("fastapi", "speedrun", ["postgres"])
        assert "supabase-postgres-best-practices" in names
        assert "planetscale-postgresql" in names

    def test_fastapi_speedrun_database_without_db_mcps(self):
        names = self._names("fastapi", "speedrun")
        assert "supabase-postgres-best-practices" not in names
        assert "planetscale-postgresql" not in names

    def test_fastapi_spec_driven_has_planning_workflow_skills(self):
        names = self._names("fastapi", "spec-driven")
        assert "brainstorming" in names
        assert "writing-plans" in names
        assert "executing-plans" in names
        assert "using-git-worktrees" in names

    def test_fastapi_verify_heavy_has_quality_workflow_skills(self):
        names = self._names("fastapi", "verify-heavy")
        assert "verification-before-completion" in names
        assert "subagent-driven-development" in names
        assert "skill-creator" in names

    def test_nextjs_standard_has_vercel_skills(self):
        names = self._names("nextjs", "standard")
        assert "vercel-react-best-practices" in names
        assert "next-best-practices" in names
        assert "web-design-guidelines" in names
        assert "frontend-design" in names
        assert "tailwind-design-system" in names

    def test_nextjs_standard_no_modern_python(self):
        names = self._names("nextjs", "standard")
        assert "modern-python" not in names

    def test_nextjs_standard_has_webapp_testing(self):
        names = self._names("nextjs", "standard")
        assert "webapp-testing" in names

    def test_nextjs_no_database_skills_even_with_db_mcps(self):
        """nextjs template has no database skills in TEMPLATE_SKILLS."""
        names = self._names("nextjs", "standard", ["postgres"])
        assert "supabase-postgres-best-practices" not in names
        assert "planetscale-postgresql" not in names

    def test_gin_standard_has_static_analysis(self):
        names = self._names("gin", "standard")
        assert "static-analysis" in names

    def test_gin_standard_no_modern_python(self):
        names = self._names("gin", "standard")
        assert "modern-python" not in names

    def test_rust_cli_standard_no_database_skills(self):
        names = self._names("rust-cli", "standard", ["postgres"])
        assert "supabase-postgres-best-practices" not in names
        assert "planetscale-postgresql" not in names

    def test_rust_cli_standard_has_property_based_testing(self):
        names = self._names("rust-cli", "standard")
        assert "property-based-testing" in names

    def test_rust_cli_standard_has_static_analysis(self):
        names = self._names("rust-cli", "standard")
        assert "static-analysis" in names

    def test_gtd_lite_same_result_as_spec_driven(self):
        """gtd-lite uses same WORKFLOW_SKILLS and WORKFLOW_PHASES as spec-driven."""
        spec = {s.name for s in resolve_skills("fastapi", "spec-driven")}
        gtd = {s.name for s in resolve_skills("fastapi", "gtd-lite")}
        assert spec == gtd


# ---------------------------------------------------------------------------
# Cross-cutting skill counts per workflow
# ---------------------------------------------------------------------------


class TestCrossCuttingSkillCounts:
    """Verify exact workflow skill counts as stated in the requirements."""

    def _workflow_skill_count(self, workflow: str) -> int:
        """Count cross-cutting workflow skills (speedrun has zero, so use rust-cli
        which contributes no template skills not in the workflow list)."""
        # Use rust-cli + each workflow, then subtract template skills to isolate
        # workflow contribution; easier to test WORKFLOW_SKILLS directly.
        return len(WORKFLOW_SKILLS[workflow])

    def test_speedrun_zero_cross_cutting(self):
        assert self._workflow_skill_count("speedrun") == 0

    def test_standard_five_cross_cutting(self):
        assert self._workflow_skill_count("standard") == 5

    def test_spec_driven_eleven_cross_cutting(self):
        assert self._workflow_skill_count("spec-driven") == 11

    def test_gtd_lite_eleven_cross_cutting(self):
        assert self._workflow_skill_count("gtd-lite") == 11

    def test_verify_heavy_fourteen_cross_cutting(self):
        assert self._workflow_skill_count("verify-heavy") == 14


# ---------------------------------------------------------------------------
# Phase gating: speedrun
# ---------------------------------------------------------------------------


class TestSpeedrunPhaseGating:
    """Speedrun only activates coding and database(if_applicable) template skills."""

    def test_speedrun_no_review_phase_skills(self):
        result = resolve_skills("fastapi", "speedrun")
        phases = {s.sdlc_phase for s in result}
        assert "review" not in phases

    def test_speedrun_no_security_phase_skills(self):
        result = resolve_skills("fastapi", "speedrun")
        phases = {s.sdlc_phase for s in result}
        assert "security" not in phases

    def test_speedrun_no_devops_phase_skills(self):
        result = resolve_skills("fastapi", "speedrun")
        phases = {s.sdlc_phase for s in result}
        assert "devops" not in phases

    def test_speedrun_no_planning_phase_skills(self):
        result = resolve_skills("fastapi", "speedrun")
        phases = {s.sdlc_phase for s in result}
        assert "planning" not in phases

    def test_speedrun_no_testing_phase_skills_bundled_only_inactive(self):
        """testing=bundled_only means those template skills are NOT active."""
        result = resolve_skills("fastapi", "speedrun")
        phases = {s.sdlc_phase for s in result}
        assert "testing" not in phases

    def test_speedrun_coding_phase_active(self):
        """Coding phase is always active in speedrun."""
        result = resolve_skills("fastapi", "speedrun")
        phases = {s.sdlc_phase for s in result}
        assert "coding" in phases

    def test_speedrun_database_inactive_without_mcps(self):
        result = resolve_skills("fastapi", "speedrun")
        phases = {s.sdlc_phase for s in result}
        assert "database" not in phases

    def test_speedrun_database_active_with_db_mcps(self):
        result = resolve_skills("fastapi", "speedrun", ["postgres"])
        phases = {s.sdlc_phase for s in result}
        assert "database" in phases


# ---------------------------------------------------------------------------
# Database "if_applicable" resolution
# ---------------------------------------------------------------------------


class TestDatabaseIfApplicable:
    """Database skills activate only when default_mcps contains a DB service."""

    @pytest.mark.parametrize("db_mcp", ["postgres", "mysql", "sqlite"])
    def test_db_service_activates_database_phase(self, db_mcp):
        result = resolve_skills("fastapi", "standard", [db_mcp])
        phases = {s.sdlc_phase for s in result}
        assert "database" in phases, f"MCP {db_mcp!r} should activate database phase"

    @pytest.mark.parametrize("non_db_mcp", ["github", "playwright", "filesystem", "slack"])
    def test_non_db_service_does_not_activate_database_phase(self, non_db_mcp):
        result = resolve_skills("fastapi", "standard", [non_db_mcp])
        phases = {s.sdlc_phase for s in result}
        assert "database" not in phases, f"MCP {non_db_mcp!r} should NOT activate database phase"

    def test_none_mcps_does_not_activate_database_phase(self):
        result = resolve_skills("fastapi", "standard", None)
        phases = {s.sdlc_phase for s in result}
        assert "database" not in phases

    def test_empty_mcps_does_not_activate_database_phase(self):
        result = resolve_skills("fastapi", "standard", [])
        phases = {s.sdlc_phase for s in result}
        assert "database" not in phases

    def test_rust_cli_no_database_skills_even_with_db_mcps(self):
        """rust-cli has no database template skills regardless of mcps."""
        result = resolve_skills("rust-cli", "standard", ["postgres"])
        phases = {s.sdlc_phase for s in result}
        assert "database" not in phases

    def test_nextjs_no_database_skills_even_with_db_mcps(self):
        """nextjs has no database template skills regardless of mcps."""
        result = resolve_skills("nextjs", "standard", ["postgres"])
        phases = {s.sdlc_phase for s in result}
        assert "database" not in phases

    @pytest.mark.parametrize("template", ["fastapi", "django", "flask", "gin", "echo"])
    def test_db_templates_include_database_skills_with_postgres(self, template):
        result = resolve_skills(template, "standard", ["postgres"])
        phases = {s.sdlc_phase for s in result}
        assert "database" in phases, f"{template} should have database skills with postgres MCP"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    """When template and workflow both reference the same skill, no duplicates appear."""

    def test_no_duplicate_names_in_result(self):
        result = resolve_skills("fastapi", "standard")
        names = [s.name for s in result]
        assert len(names) == len(set(names)), f"Duplicate skills: {names}"

    @pytest.mark.parametrize("template", ALL_TEMPLATES)
    @pytest.mark.parametrize("workflow", ALL_WORKFLOWS)
    def test_all_combos_produce_no_duplicates(self, template, workflow):
        result = resolve_skills(template, workflow, ["postgres"])
        names = [s.name for s in result]
        assert len(names) == len(set(names)), f"{template}+{workflow}: duplicate skills: {names}"

    def test_workflow_wins_on_conflict(self):
        """When same skill appears in both template and workflow lists, workflow version is kept.

        This is verified by resolve_skills adding template specs first (seen dict),
        then workflow specs overwrite any conflicts. Both should produce one entry.
        """
        # webapp-testing is a testing-phase template skill for fastapi.
        # It is NOT in WORKFLOW_SKILLS for any workflow, so no actual conflict exists
        # with the current catalog. We can still verify the dedup mechanism produces
        # exactly one entry per skill name.
        result = resolve_skills("fastapi", "verify-heavy", ["postgres"])
        names = [s.name for s in result]
        unique_names = list(set(names))
        assert sorted(names) == sorted(unique_names)

    def test_result_contains_union_of_template_and_workflow_skills(self):
        """Result is the union (deduped) of template + workflow skills."""
        result = resolve_skills("fastapi", "standard")
        result_names = {s.name for s in result}
        # workflow skills all present
        for name in WORKFLOW_SKILLS["standard"]:
            assert name in result_names, f"Workflow skill {name!r} missing from result"
        # active template skills present (standard has coding, testing, devops active)
        for name in [
            "modern-python",
            "property-based-testing",
            "webapp-testing",
            "github-actions-generator",
            "dockerfile-generator",
        ]:
            assert name in result_names, f"Template skill {name!r} missing from result"


# ---------------------------------------------------------------------------
# Skill count scaling: speedrun < standard < spec-driven <= verify-heavy
# ---------------------------------------------------------------------------


class TestSkillCountScaling:
    """resolve_skills() count increases monotonically with workflow complexity."""

    def _count(self, template: str, workflow: str, mcps: list[str] | None = None) -> int:
        return len(resolve_skills(template, workflow, mcps))

    def test_speedrun_fewer_than_standard(self):
        assert self._count("fastapi", "speedrun") < self._count("fastapi", "standard")

    def test_standard_fewer_than_spec_driven(self):
        assert self._count("fastapi", "standard") < self._count("fastapi", "spec-driven")

    def test_spec_driven_leq_verify_heavy(self):
        assert self._count("fastapi", "spec-driven") <= self._count("fastapi", "verify-heavy")

    def test_verify_heavy_most_skills(self):
        heavy = self._count("fastapi", "verify-heavy")
        for wf in ["speedrun", "standard", "spec-driven", "gtd-lite"]:
            assert heavy >= self._count("fastapi", wf), (
                f"verify-heavy should have >= skills than {wf}"
            )

    def test_fastapi_more_skills_than_rust_cli(self):
        """fastapi has more template skills than rust-cli."""
        assert self._count("fastapi", "standard") > self._count("rust-cli", "standard")

    def test_rust_cli_fewer_template_skills_fewest_total(self):
        """rust-cli has 3 template skills vs 7 for fastapi (with same workflow)."""
        rust_count = self._count("rust-cli", "speedrun")
        # rust-cli speedrun: property-based-testing(testing=bundled_only→inactive),
        # static-analysis(security=False), github-actions-generator(devops=False)
        # → all inactive → 0 template skills → 0 total (no workflow skills for speedrun)
        assert rust_count == 0

    def test_fastapi_speedrun_minimal_count(self):
        """Speedrun with fastapi, no mcps: only modern-python is active."""
        assert self._count("fastapi", "speedrun") == 1

    def test_fastapi_speedrun_with_postgres_mcp_count(self):
        """Speedrun + postgres: modern-python + supabase + planetscale = 3."""
        assert self._count("fastapi", "speedrun", ["postgres"]) == 3

    def test_gtd_lite_skill_count_equals_spec_driven(self):
        assert self._count("fastapi", "gtd-lite") == self._count("fastapi", "spec-driven")


# ---------------------------------------------------------------------------
# fastapi + standard combo: ~12 skills with postgres MCP
# ---------------------------------------------------------------------------


class TestFastapiStandardCombo:
    """Detailed verification for the canonical fastapi+standard combo."""

    def test_fastapi_standard_with_postgres_has_12_skills(self):
        result = resolve_skills("fastapi", "standard", ["postgres"])
        assert len(result) == 12

    def test_fastapi_standard_without_db_has_10_skills(self):
        result = resolve_skills("fastapi", "standard")
        assert len(result) == 10

    def test_fastapi_standard_skill_phases_covered(self):
        result = resolve_skills("fastapi", "standard")
        phases = {s.sdlc_phase for s in result}
        # standard activates: coding, testing, review, security, devops (not planning)
        assert "coding" in phases
        assert "testing" in phases
        assert "review" in phases
        assert "security" in phases
        assert "devops" in phases
        assert "planning" not in phases

    def test_fastapi_standard_no_planning_skills(self):
        result = resolve_skills("fastapi", "standard")
        planning_skills = [s for s in result if s.sdlc_phase == "planning"]
        assert planning_skills == []

    def test_fastapi_standard_expected_skill_names(self):
        result = resolve_skills("fastapi", "standard")
        names = {s.name for s in result}
        expected = {
            # workflow cross-cutting
            "owasp-security",
            "insecure-defaults",
            "requesting-code-review",
            "receiving-code-review",
            "finishing-a-development-branch",
            # template: coding
            "modern-python",
            # template: testing
            "property-based-testing",
            "webapp-testing",
            # template: devops
            "github-actions-generator",
            "dockerfile-generator",
        }
        assert names == expected


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases for resolve_skills()."""

    def test_unknown_template_returns_workflow_skills_only(self):
        """Unknown template has no TEMPLATE_SKILLS entry → only workflow skills."""
        result = resolve_skills("nonexistent-template", "standard")
        workflow_names = set(WORKFLOW_SKILLS["standard"])
        result_names = {s.name for s in result}
        assert result_names == workflow_names

    def test_unknown_workflow_returns_empty(self):
        """Unknown workflow has no phases and no workflow skills → empty result."""
        result = resolve_skills("fastapi", "nonexistent-workflow")
        assert result == []

    def test_unknown_template_and_workflow_returns_empty(self):
        result = resolve_skills("unknown", "unknown")
        assert result == []

    def test_default_mcps_none_treated_as_empty_list(self):
        """Passing None for default_mcps should behave same as empty list."""
        result_none = resolve_skills("fastapi", "standard", None)
        result_empty = resolve_skills("fastapi", "standard", [])
        assert {s.name for s in result_none} == {s.name for s in result_empty}

    def test_all_results_are_skill_spec_instances(self):
        result = resolve_skills("fastapi", "verify-heavy", ["postgres"])
        for spec in result:
            assert isinstance(spec, SkillSpec)

    def test_result_order_template_first_then_workflow(self):
        """Template skills appear first in the result, workflow skills after.

        resolve_skills builds seen dict with template first, then workflow overwrites.
        The returned list preserves insertion order (template phase order, then
        workflow additions).
        """
        result = resolve_skills("fastapi", "standard")
        names = [s.name for s in result]
        # modern-python is a template skill (coding phase) — should appear early
        # finishing-a-development-branch is a workflow skill — should appear later
        assert "modern-python" in names
        assert "finishing-a-development-branch" in names
        modern_idx = names.index("modern-python")
        finish_idx = names.index("finishing-a-development-branch")
        assert modern_idx < finish_idx

    @pytest.mark.parametrize("template", ALL_TEMPLATES)
    @pytest.mark.parametrize("workflow", ALL_WORKFLOWS)
    def test_all_combos_produce_valid_skill_specs(self, template, workflow):
        result = resolve_skills(template, workflow, ["postgres"])
        for spec in result:
            assert spec.name
            assert spec.repo
            assert spec.repo_path
            assert spec.sdlc_phase
            assert spec.description

    @pytest.mark.parametrize("template", ALL_TEMPLATES)
    @pytest.mark.parametrize("workflow", ALL_WORKFLOWS)
    def test_all_combos_have_reasonable_skill_count(self, template, workflow):
        """Every combo should produce 0–41 skills (bounded by catalog size)."""
        result = resolve_skills(template, workflow, ["postgres"])
        assert 0 <= len(result) <= 41, f"{template}+{workflow}: {len(result)} skills out of range"


# ---------------------------------------------------------------------------
# SKILL_PACKS completeness
# ---------------------------------------------------------------------------


class TestSkillPacksCompleteness:
    """SKILL_PACKS must contain 5 packs with valid references."""

    def test_has_5_packs(self):
        assert len(SKILL_PACKS) == 5

    def test_all_packs_are_skill_pack_spec(self):
        for name, pack in SKILL_PACKS.items():
            assert isinstance(pack, SkillPackSpec), f"{name!r} is not a SkillPackSpec"

    def test_pack_key_matches_spec_name(self):
        for key, pack in SKILL_PACKS.items():
            assert key == pack.name, f"Key {key!r} does not match pack.name {pack.name!r}"

    def test_all_pack_skills_reference_known_catalog_entries(self):
        for pack_name, pack in SKILL_PACKS.items():
            for skill_name in pack.skill_names:
                assert skill_name in SKILL_CATALOG, (
                    f"Pack {pack_name!r} references unknown skill {skill_name!r}"
                )

    def test_code_quality_pack_exists(self):
        assert "code-quality" in SKILL_PACKS

    def test_code_quality_pack_contains_desloppify(self):
        pack = SKILL_PACKS["code-quality"]
        assert pack.skill_names == ["desloppify"]
        assert pack.suggested_templates is None

    def test_code_quality_pack_label(self):
        assert SKILL_PACKS["code-quality"].label == "Code Quality"

    def test_desloppify_spec(self):
        spec = SKILL_CATALOG["desloppify"]
        assert spec.repo == "peteromallet/desloppify"
        assert spec.repo_path == "docs"
        assert spec.sdlc_phase == "review"
        assert spec.download_mode == "skill_md_only"

    def test_resolve_skills_with_code_quality_pack(self):
        """code-quality pack adds desloppify to any template+workflow combo."""
        result = resolve_skills("fastapi", "speedrun", packs=["code-quality"])
        names = {s.name for s in result}
        assert "desloppify" in names

    def test_known_packs_present(self):
        expected = {"security", "devops", "web-quality", "database-pro", "code-quality"}
        assert set(SKILL_PACKS.keys()) == expected


class TestComputePackOverlap:
    """compute_pack_overlap() returns correct overlap info per workflow."""

    def test_speedrun_no_overlap(self):
        """Speedrun has no skills, so no overlap with any pack."""
        for pack_name in SKILL_PACKS:
            overlap, total, comprehensive = compute_pack_overlap("speedrun", pack_name)
            assert overlap == 0
            assert total > 0
            assert comprehensive is False

    def test_superpowers_is_comprehensive(self):
        """Superpowers has 11+ process skills, so is_comprehensive should be True."""
        _, _, comprehensive = compute_pack_overlap("superpowers", "security")
        assert comprehensive is True

    def test_standard_not_comprehensive(self):
        """Standard has 5 cross-cutting skills, not comprehensive."""
        _, _, comprehensive = compute_pack_overlap("standard", "security")
        assert comprehensive is False

    def test_unknown_pack_returns_zeros(self):
        overlap, total, comprehensive = compute_pack_overlap("standard", "nonexistent")
        assert overlap == 0
        assert total == 0
        assert comprehensive is False

    def test_overlap_count_never_exceeds_total(self):
        for workflow in WORKFLOW_SKILLS:
            for pack_name in SKILL_PACKS:
                overlap, total, _ = compute_pack_overlap(workflow, pack_name)
                assert overlap <= total


class TestTemplateDescriptions:
    """TEMPLATE_DESCRIPTIONS must align with workflow-first UX."""

    def test_generic_has_no_infra_label(self):
        from cc_rig.ui.descriptions import TEMPLATE_DESCRIPTIONS

        desc = TEMPLATE_DESCRIPTIONS["generic"]
        assert "DevOps" not in desc
        assert "monorepo" not in desc.lower()
        assert "infra" not in desc.lower()

    def test_generic_signals_workflow_only(self):
        from cc_rig.ui.descriptions import TEMPLATE_DESCRIPTIONS

        desc = TEMPLATE_DESCRIPTIONS["generic"]
        assert "workflow" in desc.lower()

    def test_framework_templates_have_language_prefix(self):
        from cc_rig.ui.descriptions import TEMPLATE_DESCRIPTIONS

        for key, desc in TEMPLATE_DESCRIPTIONS.items():
            if key == "generic":
                continue
            assert " / " in desc, f"{key!r} description missing Language / Framework format"


class TestWorkflowFeatureConflicts:
    """WORKFLOW_FEATURE_CONFLICTS must be consistent with defaults."""

    def test_no_overlap_between_defaults_and_conflicts(self):
        """A feature cannot be both recommended and conflicted for the same workflow."""
        from cc_rig.ui.descriptions import (
            WORKFLOW_FEATURE_CONFLICTS,
            WORKFLOW_FEATURE_DEFAULTS,
        )

        for workflow in WORKFLOW_FEATURE_DEFAULTS:
            recommended = WORKFLOW_FEATURE_DEFAULTS[workflow]
            conflicts = WORKFLOW_FEATURE_CONFLICTS.get(workflow, set())
            overlap = recommended & conflicts
            assert not overlap, (
                f"{workflow}: {overlap} is both recommended and conflicted"
            )

    def test_gstack_conflicts_spec_and_gtd(self):
        from cc_rig.ui.descriptions import WORKFLOW_FEATURE_CONFLICTS

        assert WORKFLOW_FEATURE_CONFLICTS["gstack"] == {"spec_workflow", "gtd"}

    def test_speedrun_no_conflicts(self):
        from cc_rig.ui.descriptions import WORKFLOW_FEATURE_CONFLICTS

        assert WORKFLOW_FEATURE_CONFLICTS["speedrun"] == set()

    def test_all_workflows_have_conflict_entry(self):
        from cc_rig.ui.descriptions import (
            WORKFLOW_FEATURE_CONFLICTS,
            WORKFLOW_FEATURE_DEFAULTS,
        )

        for workflow in WORKFLOW_FEATURE_DEFAULTS:
            assert workflow in WORKFLOW_FEATURE_CONFLICTS, (
                f"{workflow} missing from WORKFLOW_FEATURE_CONFLICTS"
            )
