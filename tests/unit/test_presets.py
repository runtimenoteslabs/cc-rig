"""Tests for preset loading and integrity."""

import json

import pytest

from cc_rig.presets.manager import (
    BUILTIN_TEMPLATES,
    BUILTIN_WORKFLOWS,
    list_presets,
    load_template,
    load_workflow,
)


class TestTemplatePresets:
    @pytest.mark.parametrize("name", BUILTIN_TEMPLATES)
    def test_template_loads(self, name):
        data = load_template(name)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("name", BUILTIN_TEMPLATES)
    def test_template_has_required_fields(self, name):
        data = load_template(name)
        assert "name" in data
        assert "language" in data
        assert "framework" in data
        assert "project_type" in data
        assert "tool_commands" in data
        assert "source_dir" in data
        assert "test_dir" in data
        assert "default_mcps" in data

    @pytest.mark.parametrize("name", BUILTIN_TEMPLATES)
    def test_template_tool_commands_complete(self, name):
        data = load_template(name)
        cmds = data["tool_commands"]
        for key in ("test", "lint", "format", "typecheck", "build"):
            assert key in cmds, f"Missing tool_commands.{key} in {name}"

    @pytest.mark.parametrize("name", [t for t in BUILTIN_TEMPLATES if t != "generic"])
    def test_template_has_test_and_lint(self, name):
        """Every non-generic template must have at least test and lint commands."""
        data = load_template(name)
        cmds = data["tool_commands"]
        assert cmds["test"], f"{name} has no test command"
        assert cmds["lint"], f"{name} has no lint command"
        assert cmds["format"], f"{name} has no format command"

    def test_generic_has_no_tool_commands(self):
        """Generic template has empty tool commands."""
        data = load_template("generic")
        cmds = data["tool_commands"]
        assert cmds["test"] == ""
        assert cmds["lint"] == ""
        assert cmds["format"] == ""
        assert cmds["typecheck"] == ""

    @pytest.mark.parametrize("name", BUILTIN_TEMPLATES)
    def test_template_name_matches(self, name):
        data = load_template(name)
        assert data["name"] == name

    def test_unknown_template_raises(self):
        with pytest.raises(ValueError, match="Unknown template"):
            load_template("nonexistent")

    def test_has_minimum_templates(self):
        assert len(BUILTIN_TEMPLATES) >= 7


class TestWorkflowPresets:
    @pytest.mark.parametrize("name", BUILTIN_WORKFLOWS)
    def test_workflow_loads(self, name):
        data = load_workflow(name)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("name", BUILTIN_WORKFLOWS)
    def test_workflow_has_required_fields(self, name):
        data = load_workflow(name)
        assert "name" in data
        assert "description" in data
        assert "agents" in data
        assert "commands" in data
        assert "hooks" in data
        assert "features" in data
        assert "permission_mode" in data

    @pytest.mark.parametrize("name", BUILTIN_WORKFLOWS)
    def test_workflow_name_matches(self, name):
        data = load_workflow(name)
        assert data["name"] == name

    @pytest.mark.parametrize("name", BUILTIN_WORKFLOWS)
    def test_workflow_features_complete(self, name):
        data = load_workflow(name)
        features = data["features"]
        for key in ("memory", "spec_workflow", "gtd", "worktrees"):
            assert key in features, f"Missing features.{key} in {name}"

    @pytest.mark.parametrize("name", BUILTIN_WORKFLOWS)
    def test_workflow_lists_nonempty(self, name):
        data = load_workflow(name)
        assert len(data["agents"]) > 0
        assert len(data["commands"]) > 0
        assert len(data["hooks"]) > 0

    def test_unknown_workflow_raises(self):
        with pytest.raises(ValueError, match="Unknown workflow"):
            load_workflow("nonexistent")

    def test_has_minimum_workflows(self):
        assert len(BUILTIN_WORKFLOWS) >= 3


class TestWorkflowOrdering:
    """Verify that workflow complexity increases as expected."""

    def test_agent_counts_increase(self):
        counts = {}
        for name in BUILTIN_WORKFLOWS:
            data = load_workflow(name)
            counts[name] = len(data["agents"])
        assert counts["quick"] < counts["standard"]
        assert counts["standard"] < counts["rigorous"]

    def test_speedrun_is_minimal(self):
        data = load_workflow("speedrun")
        assert len(data["agents"]) >= 3
        assert len(data["commands"]) >= 5
        assert data["features"]["memory"] is False

    def test_superpowers_is_maximal(self):
        data = load_workflow("superpowers")
        assert len(data["agents"]) >= 10
        assert data["features"]["memory"] is True
        assert data["features"]["spec_workflow"] is True
        assert data["features"]["worktrees"] is True

    def test_verify_heavy_alias_resolves(self):
        data = load_workflow("verify-heavy")
        assert data["name"] == "rigorous"

    def test_gtd_lite_alias_resolves(self):
        data = load_workflow("gtd-lite")
        assert data["name"] == "standard"


class TestListPresets:
    def test_list_returns_both_types(self):
        result = list_presets()
        assert "templates" in result
        assert "workflows" in result

    def test_list_templates_count(self):
        result = list_presets()
        assert len(result["templates"]) >= len(BUILTIN_TEMPLATES)

    def test_list_workflows_count(self):
        result = list_presets()
        assert len(result["workflows"]) >= len(BUILTIN_WORKFLOWS)

    def test_list_template_has_info(self):
        result = list_presets()
        tmpl = result["templates"][0]
        assert "name" in tmpl
        assert "language" in tmpl
        assert "framework" in tmpl

    def test_list_workflow_has_info(self):
        result = list_presets()
        wf = result["workflows"][0]
        assert "name" in wf
        assert "description" in wf


class TestPresetJsonValidity:
    """Verify all preset JSON files are valid JSON and well-formed."""

    @pytest.mark.parametrize("name", BUILTIN_TEMPLATES)
    def test_template_json_roundtrip(self, name):
        data = load_template(name)
        json_str = json.dumps(data)
        restored = json.loads(json_str)
        assert restored == data

    @pytest.mark.parametrize("name", BUILTIN_WORKFLOWS)
    def test_workflow_json_roundtrip(self, name):
        data = load_workflow(name)
        json_str = json.dumps(data)
        restored = json.loads(json_str)
        assert restored == data
