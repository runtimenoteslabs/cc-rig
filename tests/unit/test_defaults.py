"""Tests for smart defaults engine: compute_defaults() → ProjectConfig.

Tests verify the SMART-DEFAULTS-MATRIX.md contract + SKILLS-MATRIX.md §8.
"""

import pytest

import cc_rig
from cc_rig.config.defaults import compute_defaults
from cc_rig.config.project import SkillRecommendation
from cc_rig.config.schema import validate_config
from cc_rig.presets.manager import BUILTIN_TEMPLATES, BUILTIN_WORKFLOWS

TEMPLATES = BUILTIN_TEMPLATES
WORKFLOWS = BUILTIN_WORKFLOWS


# ---------------------------------------------------------------------------
# All 35 combos produce valid configs
# ---------------------------------------------------------------------------


class TestAllCombosValid:
    @pytest.mark.parametrize("template", TEMPLATES)
    @pytest.mark.parametrize("workflow", WORKFLOWS)
    def test_combo_produces_valid_config(self, template, workflow):
        config = compute_defaults(template, workflow, project_name="test-project")
        errors = validate_config(config)
        assert errors == [], f"{template}+{workflow}: {errors}"

    @pytest.mark.parametrize("template", TEMPLATES)
    @pytest.mark.parametrize("workflow", WORKFLOWS)
    def test_combo_has_metadata(self, template, workflow):
        config = compute_defaults(template, workflow, project_name="test-project")
        assert config.cc_rig_version
        assert config.created_at
        assert config.template_preset
        assert config.workflow_preset


# ---------------------------------------------------------------------------
# Agent counts per workflow (from matrix §2e)
# ---------------------------------------------------------------------------


class TestAgentCounts:
    def test_agent_counts_increase_with_complexity(self):
        """Workflows with more complexity should have more agents."""
        counts = {}
        for wf in WORKFLOWS:
            config = compute_defaults("fastapi", wf, project_name="test")
            base_agents = [a for a in config.agents if a != "parallel-worker"]
            counts[wf] = len(base_agents)
        assert counts["speedrun"] < counts["standard"]
        assert counts["standard"] <= counts["spec-driven"]
        assert counts["standard"] <= counts["verify-heavy"]

    def test_speedrun_has_minimum_agents(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        base_agents = [a for a in config.agents if a != "parallel-worker"]
        assert len(base_agents) >= 3

    def test_verify_heavy_has_most_agents(self):
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        base_agents = [a for a in config.agents if a != "parallel-worker"]
        assert len(base_agents) >= 10

    def test_worktrees_adds_parallel_worker(self):
        config = compute_defaults("fastapi", "spec-driven", project_name="test")
        assert "parallel-worker" in config.agents

    def test_speedrun_no_parallel_worker(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        assert "parallel-worker" not in config.agents


# ---------------------------------------------------------------------------
# Specific agents per workflow (from matrix §2a)
# ---------------------------------------------------------------------------


class TestAgentMembership:
    def test_speedrun_agents(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        assert set(config.agents) == {"code-reviewer", "test-writer", "explorer"}

    def test_standard_agents(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert set(config.agents) == {
            "code-reviewer",
            "test-writer",
            "explorer",
            "architect",
            "refactorer",
        }

    def test_spec_driven_has_pm_spec(self):
        config = compute_defaults("fastapi", "spec-driven", project_name="test")
        assert "pm-spec" in config.agents
        assert "implementer" in config.agents

    def test_gtd_lite_no_pm_spec(self):
        config = compute_defaults("fastapi", "gtd-lite", project_name="test")
        assert "pm-spec" not in config.agents

    def test_verify_heavy_has_all_expected_agents(self):
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        base = [a for a in config.agents if a != "parallel-worker"]
        assert len(base) >= 10
        assert "security-auditor" in config.agents
        assert "doc-writer" in config.agents
        assert "db-reader" in config.agents


# ---------------------------------------------------------------------------
# Commands per workflow (from matrix §2b)
# ---------------------------------------------------------------------------


class TestCommandCounts:
    def test_speedrun_commands(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        assert len(config.commands) >= 5
        assert "remember" not in config.commands
        assert "fix-issue" in config.commands

    def test_standard_commands(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert len(config.commands) > len(
            compute_defaults("fastapi", "speedrun", project_name="test").commands
        )
        assert "remember" in config.commands
        assert "fix-issue" in config.commands
        assert "refactor" in config.commands

    def test_spec_driven_has_spec_commands(self):
        config = compute_defaults("fastapi", "spec-driven", project_name="test")
        assert "spec-create" in config.commands
        assert "spec-execute" in config.commands
        assert "worktree" in config.commands
        assert "techdebt" in config.commands

    def test_gtd_lite_has_gtd_commands(self):
        config = compute_defaults("fastapi", "gtd-lite", project_name="test")
        assert "gtd-capture" in config.commands
        assert "gtd-process" in config.commands
        assert "daily-plan" in config.commands
        assert "worktree" in config.commands

    def test_verify_heavy_has_quality_commands(self):
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        assert "security" in config.commands
        assert "document" in config.commands
        assert "optimize" in config.commands

    def test_verify_heavy_strips_gtd_commands_when_gtd_disabled(self):
        """verify-heavy has gtd=False, so GTD commands should be stripped."""
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        assert config.features.gtd is False
        assert "gtd-capture" not in config.commands
        assert "gtd-process" not in config.commands
        assert "daily-plan" not in config.commands

    def test_disabled_spec_workflow_strips_spec_commands(self):
        """When spec_workflow is off, spec commands should be stripped."""
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert config.features.spec_workflow is False
        assert "spec-create" not in config.commands
        assert "spec-execute" not in config.commands

    def test_disabled_worktrees_strips_worktree_command(self):
        """When worktrees is off, worktree command should be stripped."""
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert config.features.worktrees is False
        assert "worktree" not in config.commands


# ---------------------------------------------------------------------------
# Hooks per workflow (from matrix §2c)
# ---------------------------------------------------------------------------


class TestHookCounts:
    def test_speedrun_hooks(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        assert len(config.hooks) >= 4
        assert "typecheck" not in config.hooks

    def test_standard_hooks(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert len(config.hooks) > len(
            compute_defaults("fastapi", "speedrun", project_name="test").hooks
        )
        assert "typecheck" in config.hooks
        assert "stop-validator" in config.hooks
        assert "memory-precompact" in config.hooks

    def test_spec_driven_hooks(self):
        config = compute_defaults("fastapi", "spec-driven", project_name="test")
        assert "push-review" in config.hooks
        assert len(config.hooks) >= len(
            compute_defaults("fastapi", "standard", project_name="test").hooks
        )

    def test_verify_heavy_hooks(self):
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        assert "subagent-review" in config.hooks
        assert "commit-message" in config.hooks
        assert "doc-review" in config.hooks
        assert len(config.hooks) >= len(
            compute_defaults("fastapi", "standard", project_name="test").hooks
        )


# ---------------------------------------------------------------------------
# Feature flags per workflow (from matrix §2d)
# ---------------------------------------------------------------------------


class TestFeatureFlags:
    @pytest.mark.parametrize(
        "workflow,feature,expected",
        [
            ("speedrun", "memory", False),
            ("speedrun", "spec_workflow", False),
            ("speedrun", "gtd", False),
            ("speedrun", "worktrees", False),
            ("standard", "memory", True),
            ("standard", "spec_workflow", False),
            ("standard", "worktrees", False),
            ("spec-driven", "memory", True),
            ("spec-driven", "spec_workflow", True),
            ("spec-driven", "worktrees", True),
            ("gtd-lite", "memory", True),
            ("gtd-lite", "gtd", True),
            ("gtd-lite", "worktrees", True),
            ("gtd-lite", "spec_workflow", False),
            ("verify-heavy", "memory", True),
            ("verify-heavy", "spec_workflow", True),
            ("verify-heavy", "worktrees", True),
            ("verify-heavy", "gtd", False),
        ],
    )
    def test_feature_flag(self, workflow, feature, expected):
        config = compute_defaults("fastapi", workflow, project_name="test")
        assert getattr(config.features, feature) == expected


# ---------------------------------------------------------------------------
# Feature flag implications (memory → hooks, spec → agents, etc.)
# ---------------------------------------------------------------------------


class TestFeatureImplications:
    def test_memory_implies_hooks_and_command(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert config.features.memory is True
        assert "memory-precompact" in config.hooks
        assert "remember" in config.commands

    def test_no_memory_no_hooks(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        assert config.features.memory is False
        assert "memory-precompact" not in config.hooks
        assert "remember" not in config.commands

    def test_spec_implies_agents_and_commands(self):
        config = compute_defaults("fastapi", "spec-driven", project_name="test")
        assert config.features.spec_workflow is True
        assert "pm-spec" in config.agents
        assert "implementer" in config.agents
        assert "spec-create" in config.commands
        assert "spec-execute" in config.commands

    def test_gtd_implies_commands(self):
        config = compute_defaults("fastapi", "gtd-lite", project_name="test")
        assert config.features.gtd is True
        assert "gtd-capture" in config.commands
        assert "gtd-process" in config.commands
        assert "daily-plan" in config.commands

    def test_worktrees_implies_agent_and_command(self):
        config = compute_defaults("fastapi", "spec-driven", project_name="test")
        assert config.features.worktrees is True
        assert "parallel-worker" in config.agents
        assert "worktree" in config.commands


# ---------------------------------------------------------------------------
# Template → stack data (from matrix §3)
# ---------------------------------------------------------------------------


class TestTemplateStackData:
    def test_fastapi_stack(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert config.language == "python"
        assert config.framework == "fastapi"
        assert config.project_type == "api"
        assert config.test_cmd == "pytest"
        assert config.lint_cmd == "ruff check ."
        assert config.format_cmd == "ruff format ."
        assert config.typecheck_cmd == "mypy ."
        assert config.source_dir == "app"
        assert config.test_dir == "tests"

    def test_nextjs_stack(self):
        config = compute_defaults("nextjs", "standard", project_name="test")
        assert config.language == "typescript"
        assert config.framework == "nextjs"
        assert config.project_type == "web_fullstack"
        assert config.test_cmd == "npm test"
        assert config.build_cmd == "next build"

    def test_gin_stack(self):
        config = compute_defaults("gin", "standard", project_name="test")
        assert config.language == "go"
        assert config.framework == "gin"
        assert config.test_cmd == "go test ./..."
        assert config.build_cmd == "go build ./cmd/server"

    def test_rust_cli_stack(self):
        config = compute_defaults("rust-cli", "standard", project_name="test")
        assert config.language == "rust"
        assert config.framework == "clap"
        assert config.project_type == "cli"
        assert config.test_cmd == "cargo test"
        assert config.build_cmd == "cargo build"

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_recommended_skills_present(self, template):
        config = compute_defaults(template, "standard", project_name="test")
        assert len(config.recommended_skills) > 0

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_github_plugin_replaces_github_mcp(self, template):
        """GitHub plugin replaces GitHub MCP — github should not be in default_mcps."""
        config = compute_defaults(template, "standard", project_name="test")
        # github MCP removed because github plugin has replaces_mcp="github"
        assert "github" not in config.default_mcps
        # github plugin should be present instead
        plugin_names = [p.name for p in config.recommended_plugins]
        assert "github" in plugin_names


# ---------------------------------------------------------------------------
# Hook filtering by template tool commands
# ---------------------------------------------------------------------------


class TestHookFiltering:
    def test_typecheck_hook_present_when_cmd_exists(self):
        """All built-in templates have typecheck, so hook should be present."""
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert config.typecheck_cmd == "mypy ."
        assert "typecheck" in config.hooks

    def test_all_templates_have_format_hook(self):
        """Every template with a format command has the format hook."""
        for template in TEMPLATES:
            config = compute_defaults(template, "standard", project_name="test")
            if config.format_cmd:
                assert "format" in config.hooks, f"{template} missing format hook"

    def test_generic_has_no_tool_hooks(self):
        """Generic template has no tool commands, so no format/lint/typecheck hooks."""
        config = compute_defaults("generic", "standard", project_name="test")
        assert "format" not in config.hooks
        assert "lint" not in config.hooks
        assert "typecheck" not in config.hooks


# ---------------------------------------------------------------------------
# Permission mode per workflow
# ---------------------------------------------------------------------------


class TestPermissionMode:
    def test_speedrun_default_permission(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        assert config.permission_mode == "default"

    @pytest.mark.parametrize(
        "workflow",
        ["standard", "spec-driven", "gtd-lite", "verify-heavy"],
    )
    def test_non_speedrun_permissive(self, workflow):
        config = compute_defaults("fastapi", workflow, project_name="test")
        assert config.permission_mode == "permissive"


# ---------------------------------------------------------------------------
# Identity and metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_project_name_passed_through(self):
        config = compute_defaults("fastapi", "standard", project_name="my-app")
        assert config.project_name == "my-app"

    def test_output_dir_passed_through(self):
        config = compute_defaults(
            "fastapi",
            "standard",
            project_name="test",
            output_dir="/tmp/out",
        )
        assert config.output_dir == "/tmp/out"

    def test_claude_plan_passed_through(self):
        config = compute_defaults(
            "fastapi",
            "standard",
            project_name="test",
            claude_plan="max",
        )
        assert config.claude_plan == "max"

    def test_template_preset_recorded(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert config.template_preset == "fastapi"

    def test_workflow_preset_recorded(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert config.workflow_preset == "standard"

    def test_version_recorded(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert config.cc_rig_version == cc_rig.__version__


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestErrors:
    def test_unknown_template_raises(self):
        with pytest.raises(ValueError, match="Unknown template"):
            compute_defaults("nonexistent", "standard", project_name="test")

    def test_unknown_workflow_raises(self):
        with pytest.raises(ValueError, match="Unknown workflow"):
            compute_defaults("fastapi", "nonexistent", project_name="test")


# ---------------------------------------------------------------------------
# Phase 9: SDLC-aware skill merging (SKILLS-MATRIX.md §8)
# ---------------------------------------------------------------------------


class TestSkillMerging:
    """Skills are SkillRecommendation objects, not bare strings."""

    @pytest.mark.parametrize("template", TEMPLATES)
    @pytest.mark.parametrize("workflow", WORKFLOWS)
    def test_all_skills_are_recommendation_objects(self, template, workflow):
        config = compute_defaults(template, workflow, project_name="test")
        for skill in config.recommended_skills:
            assert isinstance(skill, SkillRecommendation), (
                f"{template}+{workflow}: expected SkillRecommendation, got {type(skill)}"
            )

    @pytest.mark.parametrize("template", TEMPLATES)
    @pytest.mark.parametrize("workflow", WORKFLOWS)
    def test_all_skills_have_install_command(self, template, workflow):
        config = compute_defaults(template, workflow, project_name="test")
        for skill in config.recommended_skills:
            assert skill.install, f"{template}+{workflow}: skill {skill.name!r} has no install"

    @pytest.mark.parametrize("template", TEMPLATES)
    @pytest.mark.parametrize("workflow", WORKFLOWS)
    def test_no_duplicate_skill_names(self, template, workflow):
        config = compute_defaults(template, workflow, project_name="test")
        names = [s.name for s in config.recommended_skills]
        assert len(names) == len(set(names)), f"{template}+{workflow}: duplicate skills: {names}"


class TestSpeedrunSkills:
    """Speedrun: coding + database(if_applicable) only."""

    def test_no_review_skills(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "review" not in phases

    def test_no_devops_skills(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "devops" not in phases

    def test_no_planning_skills(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "planning" not in phases

    def test_no_security_skills(self):
        """Security is 'reference' for speedrun — not included in config."""
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "security" not in phases

    def test_coding_skills_present(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "coding" in phases

    def test_database_if_applicable(self):
        """fastapi has postgres MCP → database skills included."""
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "database" in phases

    def test_no_database_for_rust_cli(self):
        """rust-cli has no DB MCP → no database skills."""
        config = compute_defaults("rust-cli", "speedrun", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "database" not in phases


class TestStandardSkills:
    """Standard: coding + testing + review + security + devops + database(if_applicable)."""

    def test_has_review_skills(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "review" in phases

    def test_has_security_skills(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "security" in phases

    def test_has_devops_skills(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "devops" in phases

    def test_owasp_included(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "owasp-security" in names

    def test_superpowers_review_skills(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "requesting-code-review" in names
        assert "receiving-code-review" in names
        assert "finishing-a-development-branch" in names

    def test_no_planning_skills(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "planning" not in phases


class TestVerifyHeavySkills:
    """Verify-heavy: all phases + full superpowers + trailofbits core."""

    def test_has_planning_skills(self):
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "planning" in phases

    def test_has_all_phases(self):
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        for phase in ("coding", "testing", "review", "security", "devops", "planning"):
            assert phase in phases, f"verify-heavy missing phase: {phase}"

    def test_verify_heavy_unique_skills(self):
        """Verify-heavy includes skills not in lower tiers."""
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "verification-before-completion" in names
        assert "subagent-driven-development" in names

    def test_full_superpowers(self):
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "brainstorming" in names
        assert "writing-plans" in names
        assert "verification-before-completion" in names

    def test_more_skills_than_standard(self):
        standard = compute_defaults("fastapi", "standard", project_name="test")
        heavy = compute_defaults("fastapi", "verify-heavy", project_name="test")
        assert len(heavy.recommended_skills) > len(standard.recommended_skills)


class TestAnthropicOfficialSkills:
    """Anthropic official skills from anthropics/skills pack."""

    def test_verify_heavy_has_all_anthropic_skills(self):
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "webapp-testing" in names
        assert "skill-creator" in names

    def test_standard_has_webapp_testing(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "webapp-testing" in names

    def test_standard_no_skill_creator(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "skill-creator" not in names

    def test_speedrun_no_anthropic_skills(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        sources = {s.source for s in config.recommended_skills}
        assert "anthropics/skills" not in sources

    def test_spec_driven_has_webapp_testing(self):
        config = compute_defaults("fastapi", "spec-driven", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "webapp-testing" in names

    def test_gtd_lite_has_webapp_testing(self):
        config = compute_defaults("fastapi", "gtd-lite", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "webapp-testing" in names


class TestSpecDrivenSkills:
    """Spec-driven: includes planning phase."""

    def test_has_planning_skills(self):
        config = compute_defaults("fastapi", "spec-driven", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "planning" in phases

    def test_brainstorming_included(self):
        config = compute_defaults("fastapi", "spec-driven", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "brainstorming" in names
        assert "writing-plans" in names
        assert "executing-plans" in names


# ---------------------------------------------------------------------------
# S05: Template-Specific Skill Identity (skills-test-matrix.md)
# ---------------------------------------------------------------------------


class TestTemplateSkillIdentity:
    """Verify each template contributes expected skills."""

    def test_fastapi_has_modern_python(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "modern-python" in names

    def test_fastapi_has_property_testing(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "property-based-testing" in names

    def test_fastapi_has_webapp_testing(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "webapp-testing" in names

    def test_fastapi_has_db_skills(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "supabase-postgres-best-practices" in names
        assert "planetscale-postgresql" in names

    def test_django_matches_fastapi_skills(self):
        """Django has same template skills as FastAPI (both Python + postgres)."""
        fa = compute_defaults("fastapi", "standard", project_name="test")
        dj = compute_defaults("django", "standard", project_name="test")
        fa_names = {s.name for s in fa.recommended_skills}
        dj_names = {s.name for s in dj.recommended_skills}
        assert fa_names == dj_names

    def test_flask_matches_fastapi_skills(self):
        """Flask has same template skills as FastAPI."""
        fa = compute_defaults("fastapi", "standard", project_name="test")
        fl = compute_defaults("flask", "standard", project_name="test")
        fa_names = {s.name for s in fa.recommended_skills}
        fl_names = {s.name for s in fl.recommended_skills}
        assert fa_names == fl_names

    def test_nextjs_has_vercel_skills(self):
        config = compute_defaults("nextjs", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "vercel-react-best-practices" in names

    def test_nextjs_has_frontend_skills(self):
        config = compute_defaults("nextjs", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "frontend-design" in names
        assert "tailwind-design-system" in names

    def test_nextjs_has_webapp_testing(self):
        config = compute_defaults("nextjs", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "webapp-testing" in names

    def test_nextjs_no_modern_python(self):
        config = compute_defaults("nextjs", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "modern-python" not in names

    def test_gin_has_static_analysis(self):
        config = compute_defaults("gin", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "static-analysis" in names

    def test_gin_no_modern_python(self):
        config = compute_defaults("gin", "standard", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "modern-python" not in names

    def test_rust_cli_minimal_skills(self):
        """rust-cli has fewest template skills (no DB, fewer coding)."""
        rust = compute_defaults("rust-cli", "standard", project_name="test")
        fastapi = compute_defaults("fastapi", "standard", project_name="test")
        assert len(rust.recommended_skills) < len(fastapi.recommended_skills)

    def test_rust_cli_no_db_skills(self):
        config = compute_defaults("rust-cli", "standard", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "database" not in phases


# ---------------------------------------------------------------------------
# S06: Database if_applicable Conditional (skills-test-matrix.md)
# ---------------------------------------------------------------------------


class TestDatabaseConditional:
    """Verify database phase resolves correctly per template."""

    @pytest.mark.parametrize(
        "template",
        ["fastapi", "django", "flask", "gin", "echo"],
    )
    def test_db_templates_have_database_skills(self, template):
        """Templates with postgres MCP should have database skills."""
        config = compute_defaults(template, "standard", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "database" in phases, f"{template} should have database skills"

    def test_nextjs_no_db_skills(self):
        """nextjs has playwright MCP, not postgres — no database skills."""
        config = compute_defaults("nextjs", "standard", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "database" not in phases

    def test_rust_cli_no_db_skills(self):
        """rust-cli has no DB MCP — no database skills."""
        config = compute_defaults("rust-cli", "standard", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "database" not in phases


# ---------------------------------------------------------------------------
# S10: Skill Count Scaling (skills-test-matrix.md)
# ---------------------------------------------------------------------------


class TestSkillCountScaling:
    """Verify skill counts scale with workflow complexity."""

    def _count(self, template: str, workflow: str) -> int:
        config = compute_defaults(template, workflow, project_name="test")
        return len(config.recommended_skills)

    def test_speedrun_fewest_skills(self):
        assert self._count("fastapi", "speedrun") < self._count("fastapi", "standard")

    def test_verify_heavy_most_skills(self):
        heavy = self._count("fastapi", "verify-heavy")
        for wf in ["speedrun", "standard", "spec-driven", "gtd-lite"]:
            assert heavy >= self._count("fastapi", wf), (
                f"verify-heavy should have >= skills than {wf}"
            )

    def test_standard_more_than_speedrun(self):
        assert self._count("fastapi", "standard") > self._count("fastapi", "speedrun")

    def test_spec_driven_more_than_standard(self):
        assert self._count("fastapi", "spec-driven") >= self._count("fastapi", "standard")

    def test_gtd_lite_similar_to_spec_driven(self):
        """GTD-lite and spec-driven should have similar skill counts."""
        gtd = self._count("fastapi", "gtd-lite")
        spec = self._count("fastapi", "spec-driven")
        assert abs(gtd - spec) <= 2

    def test_fastapi_more_skills_than_rust_cli(self):
        assert self._count("fastapi", "standard") > self._count("rust-cli", "standard")

    def test_nextjs_has_frontend_bonus(self):
        """nextjs has more coding-phase skills than gin."""
        nextjs = compute_defaults("nextjs", "standard", project_name="test")
        gin = compute_defaults("gin", "standard", project_name="test")
        nextjs_coding = [s for s in nextjs.recommended_skills if s.sdlc_phase == "coding"]
        gin_coding = [s for s in gin.recommended_skills if s.sdlc_phase == "coding"]
        assert len(nextjs_coding) > len(gin_coding)

    def test_skill_counts_per_workflow(self):
        """Exact count ranges per workflow (with fastapi template)."""
        assert 1 <= self._count("fastapi", "speedrun") <= 5
        assert 10 <= self._count("fastapi", "standard") <= 16
        assert 15 <= self._count("fastapi", "spec-driven") <= 22
        assert 15 <= self._count("fastapi", "gtd-lite") <= 22
        assert 18 <= self._count("fastapi", "verify-heavy") <= 25

    @pytest.mark.parametrize("template", TEMPLATES)
    @pytest.mark.parametrize("workflow", WORKFLOWS)
    def test_all_combos_have_reasonable_count(self, template, workflow):
        """Every combo should have 0-41 skills (sanity bounds)."""
        count = self._count(template, workflow)
        assert 0 <= count <= 41, f"{template}+{workflow}: {count} skills out of range"


# ---------------------------------------------------------------------------
# S11: GTD-Lite Full Coverage (skills-test-matrix.md)
# ---------------------------------------------------------------------------


class TestGtdLiteSkills:
    """GTD-lite skill coverage (previously only tested via anthropic pack)."""

    def test_has_all_standard_phases(self):
        config = compute_defaults("fastapi", "gtd-lite", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        for phase in ("coding", "testing", "review", "security", "devops"):
            assert phase in phases, f"gtd-lite missing phase: {phase}"

    def test_has_planning_phase(self):
        config = compute_defaults("fastapi", "gtd-lite", project_name="test")
        phases = {s.sdlc_phase for s in config.recommended_skills}
        assert "planning" in phases

    def test_superpowers_list(self):
        """GTD-lite includes 7 specific superpowers skills."""
        config = compute_defaults("fastapi", "gtd-lite", project_name="test")
        names = {s.name for s in config.recommended_skills}
        expected = {
            "brainstorming",
            "writing-plans",
            "executing-plans",
            "requesting-code-review",
            "receiving-code-review",
            "using-git-worktrees",
            "finishing-a-development-branch",
        }
        assert expected.issubset(names), f"Missing: {expected - names}"

    def test_no_static_analysis_for_python_template(self):
        """static-analysis is template-specific to Go/Rust, not Python."""
        config = compute_defaults("fastapi", "gtd-lite", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "static-analysis" not in names

    def test_similar_skills_to_spec_driven(self):
        """GTD-lite and spec-driven should produce identical skill sets."""
        gtd = compute_defaults("fastapi", "gtd-lite", project_name="test")
        spec = compute_defaults("fastapi", "spec-driven", project_name="test")
        gtd_names = {s.name for s in gtd.recommended_skills}
        spec_names = {s.name for s in spec.recommended_skills}
        assert gtd_names == spec_names


# ---------------------------------------------------------------------------
# Tier-aware model overrides (SMART-DEFAULTS-MATRIX §1a)
# ---------------------------------------------------------------------------


class TestModelOverridesByTier:
    """Verify _compute_model_overrides produces correct overrides per plan tier."""

    def test_pro_overrides_opus_and_haiku(self):
        """Pro tier overrides 5 agents: architect, pr-reviewer, pm-spec,
        security-auditor, explorer."""
        config = compute_defaults("fastapi", "verify-heavy", project_name="test", claude_plan="pro")
        assert len(config.model_overrides) == 5
        assert config.model_overrides["architect"] == "sonnet"
        assert config.model_overrides["pr-reviewer"] == "sonnet"
        assert config.model_overrides["pm-spec"] == "sonnet"
        assert config.model_overrides["security-auditor"] == "sonnet"
        assert config.model_overrides["explorer"] == "sonnet"

    def test_team_same_as_pro(self):
        """Team tier gets same overrides as pro."""
        pro = compute_defaults("fastapi", "standard", project_name="test", claude_plan="pro")
        team = compute_defaults("fastapi", "standard", project_name="test", claude_plan="team")
        assert pro.model_overrides == team.model_overrides

    def test_max_no_overrides(self):
        """Max tier keeps _AGENT_DEFS defaults — no overrides."""
        config = compute_defaults("fastapi", "verify-heavy", project_name="test", claude_plan="max")
        assert config.model_overrides == {}

    def test_enterprise_no_overrides(self):
        """Enterprise tier keeps _AGENT_DEFS defaults — no overrides."""
        config = compute_defaults(
            "fastapi", "verify-heavy", project_name="test", claude_plan="enterprise"
        )
        assert config.model_overrides == {}


# ---------------------------------------------------------------------------
# Plugin resolution in compute_defaults
# ---------------------------------------------------------------------------


class TestPluginResolution:
    """Verify compute_defaults() resolves plugins correctly."""

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_all_templates_have_plugins(self, template):
        """Every template gets at least one plugin (github)."""
        config = compute_defaults(template, "standard", project_name="test")
        assert len(config.recommended_plugins) > 0

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_all_templates_have_github_plugin(self, template):
        config = compute_defaults(template, "standard", project_name="test")
        plugin_names = [p.name for p in config.recommended_plugins]
        assert "github" in plugin_names

    def test_python_gets_pyright_lsp(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        plugin_names = [p.name for p in config.recommended_plugins]
        assert "pyright-lsp" in plugin_names

    def test_typescript_gets_typescript_lsp(self):
        config = compute_defaults("nextjs", "standard", project_name="test")
        plugin_names = [p.name for p in config.recommended_plugins]
        assert "typescript-lsp" in plugin_names

    def test_go_gets_gopls_lsp(self):
        config = compute_defaults("gin", "standard", project_name="test")
        plugin_names = [p.name for p in config.recommended_plugins]
        assert "gopls-lsp" in plugin_names

    def test_ruby_no_lsp(self):
        config = compute_defaults("rails", "standard", project_name="test")
        lsp_plugins = [p for p in config.recommended_plugins if p.category == "lsp"]
        assert len(lsp_plugins) == 0

    def test_generic_no_lsp(self):
        config = compute_defaults("generic", "standard", project_name="test")
        lsp_plugins = [p for p in config.recommended_plugins if p.category == "lsp"]
        assert len(lsp_plugins) == 0

    def test_nextjs_gets_vercel_plugin(self):
        config = compute_defaults("nextjs", "standard", project_name="test")
        plugin_names = [p.name for p in config.recommended_plugins]
        assert "vercel" in plugin_names

    def test_fastapi_no_vercel_plugin(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        plugin_names = [p.name for p in config.recommended_plugins]
        assert "vercel" not in plugin_names

    def test_github_mcp_removed(self):
        """GitHub MCP should be removed when github plugin is present."""
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert "github" not in config.default_mcps

    def test_other_mcps_preserved(self):
        """Non-github MCPs like postgres should be preserved."""
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert "postgres" in config.default_mcps

    def test_workflow_plugins_scale(self):
        """More complex workflows should have more plugins."""
        speedrun = compute_defaults("fastapi", "speedrun", project_name="test")
        standard = compute_defaults("fastapi", "standard", project_name="test")
        verify = compute_defaults("fastapi", "verify-heavy", project_name="test")
        assert len(speedrun.recommended_plugins) <= len(standard.recommended_plugins)
        assert len(standard.recommended_plugins) <= len(verify.recommended_plugins)

    def test_ralph_loop_not_in_defaults(self):
        """ralph-loop plugin should not appear in compute_defaults output."""
        for wf in WORKFLOWS:
            config = compute_defaults("fastapi", wf, project_name="test")
            plugin_names = [p.name for p in config.recommended_plugins]
            assert "ralph-loop" not in plugin_names

    def test_plugin_count_fastapi_standard(self):
        """FastAPI + standard should produce an exact known plugin count."""
        config = compute_defaults("fastapi", "standard", project_name="test")
        names = [p.name for p in config.recommended_plugins]
        # language: python → pyright-lsp
        # template: fastapi → github
        # workflow: standard → commit-commands, code-review
        assert len(names) == 4, f"Expected 4 plugins, got {len(names)}: {names}"
        assert "pyright-lsp" in names
        assert "github" in names
        assert "commit-commands" in names
        assert "code-review" in names
