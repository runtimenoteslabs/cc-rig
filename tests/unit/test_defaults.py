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


# ---------------------------------------------------------------------------
# Hooks per workflow (from matrix §2c)
# ---------------------------------------------------------------------------


class TestHookCounts:
    def test_speedrun_hooks(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        assert len(config.hooks) >= 4
        assert "typecheck" not in config.hooks
        assert "memory-stop" not in config.hooks

    def test_standard_hooks(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert len(config.hooks) > len(
            compute_defaults("fastapi", "speedrun", project_name="test").hooks
        )
        assert "typecheck" in config.hooks
        assert "stop-validator" in config.hooks
        assert "memory-stop" in config.hooks
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
        assert "memory-stop" in config.hooks
        assert "memory-precompact" in config.hooks
        assert "remember" in config.commands

    def test_no_memory_no_hooks(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        assert config.features.memory is False
        assert "memory-stop" not in config.hooks
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
    def test_default_mcps_include_github(self, template):
        config = compute_defaults(template, "standard", project_name="test")
        assert "github" in config.default_mcps


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
        """Every template has a format command, so format hook always present."""
        for template in TEMPLATES:
            config = compute_defaults(template, "standard", project_name="test")
            assert "format" in config.hooks, f"{template} missing format hook"


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
        assert "claude-code-owasp" in names

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

    def test_trailofbits_core_included(self):
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        names = {s.name for s in config.recommended_skills}
        assert "static-analysis" in names
        assert "second-opinion" in names

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
