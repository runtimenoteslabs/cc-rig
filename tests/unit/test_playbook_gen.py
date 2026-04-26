"""Tests for playbook generator (.claude/commands/cc-rig.md)."""

from __future__ import annotations

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.config.project import Features, HarnessConfig
from cc_rig.generators.playbook import generate_playbook
from cc_rig.presets.manager import BUILTIN_TEMPLATES, BUILTIN_WORKFLOWS
from tests.conftest import make_valid_config


def _generate_playbook(template: str, workflow: str, tmp_path, **overrides):
    config = compute_defaults(template, workflow, project_name="test-project", **overrides)
    files = generate_playbook(config, tmp_path)
    return config, files


def _generate_playbook_with_gtd(template: str, tmp_path):
    """Generate playbook with GTD features explicitly enabled."""
    config = compute_defaults(template, "standard", project_name="test-project")
    config.features.gtd = True
    config.features.worktrees = True
    config.commands = list(config.commands) + [
        "gtd-capture",
        "gtd-process",
        "daily-plan",
        "worktree",
    ]
    files = generate_playbook(config, tmp_path)
    return config, files


def _read_playbook(tmp_path) -> str:
    return (tmp_path / ".claude" / "commands" / "cc-rig.md").read_text()


# ── Basic structure ────────────────────────────────────────────────


class TestPlaybookFileGeneration:
    def test_returns_both_files(self, tmp_path):
        _, files = _generate_playbook("fastapi", "standard", tmp_path)
        assert ".claude/commands/cc-rig.md" in files
        assert "PLAYBOOK.md" in files
        assert (tmp_path / ".claude" / "commands" / "cc-rig.md").exists()
        assert (tmp_path / "PLAYBOOK.md").exists()
        assert (tmp_path / ".claude" / "commands" / "cc-rig.md").stat().st_size > 1000
        assert (tmp_path / "PLAYBOOK.md").stat().st_size > 1000


class TestPlaybookFrontmatter:
    def test_valid_frontmatter_structure(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert content.startswith("---\n")
        assert "description:" in content
        assert "allowed-tools:" in content

    def test_has_effort_for_high_rigor(self, tmp_path):
        _generate_playbook("fastapi", "spec-driven", tmp_path)
        content = _read_playbook(tmp_path)
        assert "effort: high" in content

    def test_no_effort_for_standard(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "effort:" not in content


class TestPlaybookDispatch:
    def test_has_arguments_placeholder(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "$ARGUMENTS" in content

    def test_mentions_all_subcommands(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        for sub in ("dashboard", "detail", "recipes", "savings", "hooks", "autonomous"):
            assert sub in content.lower(), f"Missing subcommand: {sub}"


# ── Dashboard section ──────────────────────────────────────────────


class TestDashboardSection:
    def test_shows_workflow_and_framework(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "standard" in content
        assert "fastapi" in content

    def test_shows_workflow_chain(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "/plan" in content
        assert "/review" in content

    def test_shows_quick_recipes(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "/fix-issue" in content

    def test_shows_all_counts(self, tmp_path):
        config, _ = _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert f"Agents: {len(config.agents)}" in content
        assert f"Plugins: {len(config.recommended_plugins)}" in content
        assert f"Hooks: {len(config.hooks)}" in content
        assert f"Commands: {len(config.commands)}" in content

    def test_shows_spec_recipe_when_spec_workflow(self, tmp_path):
        _generate_playbook("fastapi", "spec-driven", tmp_path)
        content = _read_playbook(tmp_path)
        assert "/spec-create" in content

    def test_shows_gtd_recipe_when_gtd(self, tmp_path):
        """GTD recipes appear when features.gtd is explicitly enabled."""
        _generate_playbook_with_gtd("generic", tmp_path)
        content = _read_playbook(tmp_path)
        assert "/daily-plan" in content


# ── Detail section ─────────────────────────────────────────────────


class TestDetailSection:
    def test_lists_all_agents(self, tmp_path):
        config, _ = _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        for agent in config.agents:
            assert agent in content, f"Missing agent: {agent}"

    def test_lists_all_plugins(self, tmp_path):
        config, _ = _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        for plugin in config.recommended_plugins:
            assert plugin.name in content, f"Missing plugin: {plugin.name}"

    def test_lists_all_hooks(self, tmp_path):
        config, _ = _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        # Hook names appear via their labels, not raw names
        assert "Auto-format" in content
        assert "Lint gate" in content

    def test_security_section_shows_deny_rules(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Security" in content
        assert "denyRead" in content

    def test_speedrun_also_has_deny_rules(self, tmp_path):
        """Deny rules are unconditional for all workflows."""
        _generate_playbook("fastapi", "speedrun", tmp_path)
        content = _read_playbook(tmp_path)
        assert "denyRead" in content


# ── Recipes section ────────────────────────────────────────────────


class TestRecipesSection:
    def test_has_bug_fix_recipe(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Fix a Bug" in content

    def test_has_feature_recipe(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Build a Feature" in content

    def test_has_understand_recipe(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Understand Unfamiliar Code" in content

    def test_has_refactor_recipe(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Refactor Safely" in content

    def test_spec_driven_has_architecture_recipe(self, tmp_path):
        _generate_playbook("fastapi", "spec-driven", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Architecture Decision" in content

    def test_spec_driven_uses_spec_create(self, tmp_path):
        _generate_playbook("fastapi", "spec-driven", tmp_path)
        content = _read_playbook(tmp_path)
        assert "/spec-create" in content
        assert "/spec-execute" in content

    def test_security_recipe_when_command_available(self, tmp_path):
        _generate_playbook("fastapi", "superpowers", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Security Review" in content

    def test_gtd_recipes_when_gtd(self, tmp_path):
        """GTD recipes appear when features.gtd is explicitly enabled."""
        _generate_playbook_with_gtd("generic", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Daily Planning" in content

    def test_assumptions_recipe_when_available(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Check Your Assumptions" in content


# ── Savings section ────────────────────────────────────────────────


class TestSavingsSection:
    def test_savings_section_present(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "## Savings" in content

    def test_mentions_cache(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "cache" in content.lower()

    def test_shows_pricing(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Opus" in content
        assert "Sonnet" in content

    def test_compaction_survival_with_explicit_flag(self, tmp_path):
        """Use explicit flag, not level, to test the context_awareness branch."""
        config = make_valid_config(
            harness=HarnessConfig(level="custom", context_awareness=True),
        )
        generate_playbook(config, tmp_path)
        content = _read_playbook(tmp_path)
        assert "Compaction survival" in content

    def test_session_telemetry_with_explicit_flag(self, tmp_path):
        """Use explicit flag, not level, to test the session_telemetry branch."""
        config = make_valid_config(
            harness=HarnessConfig(level="custom", session_telemetry=True),
        )
        generate_playbook(config, tmp_path)
        content = _read_playbook(tmp_path)
        assert "Session telemetry" in content

    def test_step_numbering_both_flags(self, tmp_path):
        """When both context_awareness and session_telemetry are on, numbering is 3 then 4."""
        config = make_valid_config(
            harness=HarnessConfig(level="custom", context_awareness=True, session_telemetry=True),
        )
        generate_playbook(config, tmp_path)
        content = _read_playbook(tmp_path)
        assert "3. **Compaction survival**" in content
        assert "4. **Session telemetry**" in content

    def test_step_numbering_telemetry_only(self, tmp_path):
        """When only session_telemetry is on, it gets number 3."""
        config = make_valid_config(
            harness=HarnessConfig(level="custom", context_awareness=False, session_telemetry=True),
        )
        generate_playbook(config, tmp_path)
        content = _read_playbook(tmp_path)
        assert "3. **Session telemetry**" in content
        assert "Compaction survival" not in content


# ── Hooks section ──────────────────────────────────────────────────


class TestHooksSection:
    def test_hooks_section_present(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "## Hooks" in content

    def test_categorizes_automatic_hooks(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Automatic" in content

    def test_categorizes_quality_gates(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Quality gates" in content

    def test_categorizes_safety_hooks(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "Safety" in content

    def test_explains_conditional_hooks(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "conditional" in content.lower()

    def test_unknown_hooks_fall_through_to_automatic(self, tmp_path):
        """Hooks not in the category registry should still appear (as automatic)."""
        config = make_valid_config(
            hooks=["format", "some-unknown-hook"],
        )
        generate_playbook(config, tmp_path)
        content = _read_playbook(tmp_path)
        assert "some-unknown-hook" in content


# ── Autonomous section ─────────────────────────────────────────────


class TestAutonomousSection:
    def test_absent_without_autonomy(self, tmp_path):
        _generate_playbook("fastapi", "standard", tmp_path)
        content = _read_playbook(tmp_path)
        assert "## Autonomous" not in content

    def test_present_with_autonomy(self, tmp_path):
        config = make_valid_config(
            harness=HarnessConfig(level="custom", autonomy_loop=True, task_tracking=True),
        )
        generate_playbook(config, tmp_path)
        content = _read_playbook(tmp_path)
        assert "## Autonomous" in content
        assert "Safety rails" in content
        assert "dangerously-skip-permissions" in content

    def test_worktrees_shown_when_enabled(self, tmp_path):
        config = make_valid_config(
            harness=HarnessConfig(level="custom", autonomy_loop=True, task_tracking=True),
            features=Features(memory=True, worktrees=True),
        )
        generate_playbook(config, tmp_path)
        content = _read_playbook(tmp_path)
        assert "worktree" in content.lower()

    def test_worktrees_absent_when_disabled(self, tmp_path):
        config = make_valid_config(
            harness=HarnessConfig(level="custom", autonomy_loop=True, task_tracking=True),
            features=Features(memory=True, worktrees=False),
        )
        generate_playbook(config, tmp_path)
        content = _read_playbook(tmp_path)
        assert "cc-rig worktree" not in content


# ── All workflows generate valid playbook ──────────────────────────


class TestAllWorkflows:
    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_playbook_generated_for_every_workflow(self, workflow, tmp_path):
        _, files = _generate_playbook("fastapi", workflow, tmp_path)
        assert len(files) == 2
        content = _read_playbook(tmp_path)
        assert content.startswith("---\n")
        assert "$ARGUMENTS" in content
        assert "## Dashboard" in content
        assert "## Detail" in content
        assert "## Recipes" in content
        assert "## Savings" in content
        assert "## Hooks" in content


# ── All templates generate valid playbook ──────────────────────────


class TestAllTemplates:
    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_playbook_generated_for_every_template(self, template, tmp_path):
        _, files = _generate_playbook(template, "standard", tmp_path)
        assert len(files) == 2
        content = _read_playbook(tmp_path)
        assert content.startswith("---\n")
        assert "## Dashboard" in content


# ── FileTracker integration ────────────────────────────────────────


class TestFileTrackerIntegration:
    def test_works_with_tracker(self, tmp_path):
        from cc_rig.generators.fileops import FileTracker

        config = make_valid_config()
        tracker = FileTracker(tmp_path)
        files = generate_playbook(config, tmp_path, tracker=tracker)
        assert ".claude/commands/cc-rig.md" in files
        assert "PLAYBOOK.md" in files
        assert (tmp_path / ".claude" / "commands" / "cc-rig.md").exists()
        assert (tmp_path / "PLAYBOOK.md").exists()
        assert ".claude/commands/cc-rig.md" in tracker.metadata()
        assert "PLAYBOOK.md" in tracker.metadata()

    def test_works_without_tracker(self, tmp_path):
        config = make_valid_config()
        files = generate_playbook(config, tmp_path, tracker=None)
        assert ".claude/commands/cc-rig.md" in files
        assert "PLAYBOOK.md" in files
        assert (tmp_path / ".claude" / "commands" / "cc-rig.md").exists()
        assert (tmp_path / "PLAYBOOK.md").exists()
