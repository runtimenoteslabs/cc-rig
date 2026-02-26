"""Tests for schema validation: valid configs pass, each invalid case caught."""

import pytest

from cc_rig.config.project import Features
from cc_rig.config.schema import (
    VALID_AGENTS,
    VALID_COMMANDS,
    VALID_HOOKS,
    validate_config,
    validate_config_warnings,
)
from tests.conftest import make_valid_config as _make_valid_config


class TestValidConfig:
    def test_valid_config_passes(self):
        config = _make_valid_config()
        errors = validate_config(config)
        assert errors == []

    def test_valid_speedrun_config(self):
        config = _make_valid_config(
            workflow="speedrun",
            agents=["code-reviewer", "test-writer", "explorer"],
            commands=["fix-issue", "review", "test", "plan", "learn", "assumptions"],
            hooks=["format", "lint", "block-rm-rf", "block-env", "block-main", "session-context"],
            features=Features(memory=False),
            permission_mode="default",
        )
        errors = validate_config(config)
        assert errors == []


class TestRequiredFields:
    def test_missing_project_name(self):
        config = _make_valid_config(project_name="")
        errors = validate_config(config)
        assert any("project_name" in e for e in errors)

    def test_missing_language(self):
        config = _make_valid_config(language="")
        errors = validate_config(config)
        assert any("language is required" in e for e in errors)

    def test_missing_framework(self):
        config = _make_valid_config(framework="")
        errors = validate_config(config)
        assert any("framework is required" in e for e in errors)

    def test_missing_workflow(self):
        config = _make_valid_config(workflow="")
        errors = validate_config(config)
        assert any("workflow is required" in e for e in errors)


class TestEnumValidation:
    def test_invalid_language(self):
        config = _make_valid_config(language="cobol")
        errors = validate_config(config)
        assert any("unknown language" in e for e in errors)

    def test_invalid_framework(self):
        config = _make_valid_config(framework="express")
        errors = validate_config(config)
        assert any("unknown framework" in e for e in errors)

    def test_framework_language_mismatch(self):
        config = _make_valid_config(language="go", framework="fastapi")
        errors = validate_config(config)
        assert any("not valid for language" in e for e in errors)

    def test_invalid_workflow(self):
        config = _make_valid_config(workflow="yolo")
        errors = validate_config(config)
        assert any("unknown workflow" in e for e in errors)

    def test_invalid_project_type(self):
        config = _make_valid_config(project_type="mobile")
        errors = validate_config(config)
        assert any("unknown project_type" in e for e in errors)

    def test_invalid_permission_mode(self):
        config = _make_valid_config(permission_mode="unsafe")
        errors = validate_config(config)
        assert any("unknown permission_mode" in e for e in errors)

    def test_invalid_claude_plan(self):
        config = _make_valid_config(claude_plan="free")
        errors = validate_config(config)
        assert any("unknown claude_plan" in e for e in errors)


class TestListMembership:
    def test_unknown_agent(self):
        config = _make_valid_config(agents=["code-reviewer", "nonexistent-agent"])
        errors = validate_config(config)
        assert any("unknown agent" in e and "nonexistent-agent" in e for e in errors)

    def test_unknown_command(self):
        config = _make_valid_config(commands=["fix-issue", "deploy-prod"])
        errors = validate_config(config)
        assert any("unknown command" in e and "deploy-prod" in e for e in errors)

    def test_unknown_hook(self):
        config = _make_valid_config(hooks=["format", "auto-deploy"])
        errors = validate_config(config)
        assert any("unknown hook" in e and "auto-deploy" in e for e in errors)

    def test_all_valid_agents_accepted(self):
        """Every agent in the catalog should be accepted."""
        config = _make_valid_config(agents=list(VALID_AGENTS))
        errors = validate_config(config)
        assert not any("unknown agent" in e for e in errors)

    def test_all_valid_commands_accepted(self):
        """Every command in the catalog should be accepted."""
        config = _make_valid_config(
            commands=list(VALID_COMMANDS),
            features=Features(memory=True, spec_workflow=True, gtd=False, worktrees=True),
            agents=list(VALID_AGENTS),
        )
        errors = validate_config(config)
        assert not any("unknown command" in e for e in errors)

    def test_all_valid_hooks_accepted(self):
        """Every hook in the catalog should be accepted."""
        config = _make_valid_config(hooks=list(VALID_HOOKS))
        errors = validate_config(config)
        assert not any("unknown hook" in e for e in errors)


class TestFeatureFlagImplications:
    def test_memory_requires_hooks(self):
        config = _make_valid_config(
            features=Features(memory=True),
            hooks=["format"],  # missing memory hooks
            commands=["fix-issue"],  # missing remember
        )
        errors = validate_config(config)
        assert any("memory-stop" in e for e in errors)
        assert any("memory-precompact" in e for e in errors)
        assert any("remember" in e for e in errors)

    def test_spec_workflow_requires_agents_and_commands(self):
        config = _make_valid_config(
            features=Features(spec_workflow=True),
            agents=["code-reviewer"],  # missing pm-spec, implementer
            commands=["fix-issue"],  # missing spec-create, spec-execute
        )
        errors = validate_config(config)
        assert any("pm-spec" in e for e in errors)
        assert any("implementer" in e for e in errors)
        assert any("spec-create" in e for e in errors)
        assert any("spec-execute" in e for e in errors)

    def test_gtd_requires_commands(self):
        config = _make_valid_config(
            features=Features(gtd=True),
            commands=["fix-issue"],  # missing gtd commands
        )
        errors = validate_config(config)
        assert any("gtd-capture" in e for e in errors)
        assert any("gtd-process" in e for e in errors)
        assert any("daily-plan" in e for e in errors)

    def test_worktrees_requires_agent_and_command(self):
        config = _make_valid_config(
            features=Features(worktrees=True),
            agents=["code-reviewer"],  # missing parallel-worker
            commands=["fix-issue"],  # missing worktree
        )
        errors = validate_config(config)
        assert any("parallel-worker" in e for e in errors)
        assert any("worktree" in e for e in errors)

    def test_disabled_features_no_errors(self):
        """Disabled features should not impose requirements."""
        config = _make_valid_config(
            features=Features(memory=False, spec_workflow=False, gtd=False, worktrees=False),
            agents=["code-reviewer"],
            commands=["fix-issue"],
            hooks=["format"],
        )
        errors = validate_config(config)
        assert not any("features" in e for e in errors)


class TestModelOverrides:
    def test_valid_model_override(self):
        config = _make_valid_config(model_overrides={"architect": "opus"})
        errors = validate_config(config)
        assert not any("model_overrides" in e for e in errors)

    def test_model_override_unknown_agent(self):
        config = _make_valid_config(model_overrides={"nonexistent-agent": "opus"})
        errors = validate_config(config)
        assert any("model_overrides" in e and "nonexistent-agent" in e for e in errors)


class TestValidFrameworkLanguageCombos:
    @pytest.mark.parametrize(
        "language,framework",
        [
            ("python", "fastapi"),
            ("python", "django"),
            ("python", "flask"),
            ("typescript", "nextjs"),
            ("go", "gin"),
            ("go", "echo"),
            ("rust", "clap"),
        ],
    )
    def test_all_valid_combos(self, language, framework):
        config = _make_valid_config(language=language, framework=framework)
        errors = validate_config(config)
        assert not any("not valid for language" in e for e in errors)


class TestSpecGtdMutualExclusion:
    def test_spec_and_gtd_together_is_validation_error(self):
        config = _make_valid_config(
            features=Features(spec_workflow=True, gtd=True, memory=True),
            agents=list(VALID_AGENTS),
            commands=list(VALID_COMMANDS),
            hooks=list(VALID_HOOKS),
        )
        errors = validate_config(config)
        assert any("spec_workflow" in e and "gtd" in e for e in errors)

    def test_spec_and_gtd_together_no_warning(self):
        """The check moved to errors — warnings should be empty."""
        config = _make_valid_config(
            features=Features(spec_workflow=True, gtd=True, memory=True),
            agents=list(VALID_AGENTS),
            commands=list(VALID_COMMANDS),
            hooks=list(VALID_HOOKS),
        )
        warnings = validate_config_warnings(config)
        assert warnings == []


class TestConfigWarnings:
    def test_spec_only_no_warning(self):
        config = _make_valid_config(
            features=Features(spec_workflow=True, gtd=False, memory=True),
            agents=list(VALID_AGENTS),
            commands=list(VALID_COMMANDS),
            hooks=list(VALID_HOOKS),
        )
        warnings = validate_config_warnings(config)
        assert len(warnings) == 0

    def test_gtd_only_no_warning(self):
        config = _make_valid_config(
            features=Features(gtd=True, spec_workflow=False, memory=True),
            agents=list(VALID_AGENTS),
            commands=list(VALID_COMMANDS),
            hooks=list(VALID_HOOKS),
        )
        warnings = validate_config_warnings(config)
        assert len(warnings) == 0

    def test_neither_no_warning(self):
        config = _make_valid_config(
            features=Features(spec_workflow=False, gtd=False, memory=True),
        )
        warnings = validate_config_warnings(config)
        assert len(warnings) == 0
