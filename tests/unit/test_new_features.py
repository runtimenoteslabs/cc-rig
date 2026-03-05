"""Tests for new features: TUI auto-detection, launcher, harness wizard, preset management."""

import io as _io
import json
import sys

import pytest

from cc_rig.config.project import HarnessConfig
from cc_rig.presets.manager import (
    BUILTIN_TEMPLATES,
    BUILTIN_WORKFLOWS,
    create_preset,
    inspect_preset,
    install_preset,
    list_presets,
)
from cc_rig.ui.tui import _has_rich, get_tui_backend
from cc_rig.wizard.harness import ask_harness
from cc_rig.wizard.launcher import run_launcher
from tests.conftest import make_io as _make_io


class FakeTTY(_io.StringIO):
    """A StringIO that reports itself as a TTY."""

    def isatty(self):
        return True


# ===========================================================================
# 1. TUI auto-detection  (cc_rig/ui/tui.py)
# ===========================================================================


class TestHasRich:
    def test_consistent_across_calls(self):
        """_has_rich should return the same value on repeated calls."""
        assert _has_rich() == _has_rich()


class TestGetTuiBackend:
    def test_returns_valid_backend(self):
        result = get_tui_backend()
        assert result in ("rich", "ansi", "plain")

    def test_no_color_env_forces_plain(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        result = get_tui_backend()
        assert result == "plain"

    def test_no_color_empty_string_does_not_force_plain(self, monkeypatch):
        """NO_COLOR set to empty string is falsy, should not force plain."""
        monkeypatch.setenv("NO_COLOR", "")
        monkeypatch.delenv("TERM", raising=False)
        monkeypatch.setattr(sys, "stdout", FakeTTY())
        monkeypatch.setattr("cc_rig.ui.tui._has_rich", lambda: True)
        result = get_tui_backend()
        assert result == "rich"

    def test_term_dumb_forces_plain(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "dumb")
        monkeypatch.setattr(sys, "stdout", FakeTTY())
        result = get_tui_backend()
        assert result == "plain"

    def test_non_tty_returns_plain(self, monkeypatch):
        """When stdout is not a TTY, backend should be 'plain'."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setattr(sys, "stdout", _io.StringIO())
        result = get_tui_backend()
        assert result == "plain"

    def test_tty_without_rich_returns_ansi(self, monkeypatch):
        """With a TTY but no rich, backend should be 'ansi'."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("TERM", raising=False)
        monkeypatch.setattr(sys, "stdout", FakeTTY())
        monkeypatch.setattr("cc_rig.ui.tui._has_rich", lambda: False)
        result = get_tui_backend()
        assert result == "ansi"

    def test_tty_with_rich_returns_rich(self, monkeypatch):
        """With a TTY and rich available, backend should be 'rich'."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("TERM", raising=False)
        monkeypatch.setattr(sys, "stdout", FakeTTY())
        monkeypatch.setattr("cc_rig.ui.tui._has_rich", lambda: True)
        result = get_tui_backend()
        assert result == "rich"


# ===========================================================================
# 2. Launcher screen  (cc_rig/wizard/launcher.py)
# ===========================================================================


class TestRunLauncher:
    """Test that run_launcher returns the correct mode for each option."""

    def test_fresh_mode(self):
        io = _make_io(["1"])
        result = run_launcher(io)
        assert result == "fresh"

    def test_quick_mode(self):
        io = _make_io(["2"])
        result = run_launcher(io)
        assert result == "quick"

    def test_config_mode(self):
        io = _make_io(["3"])
        result = run_launcher(io)
        assert result == "config"

    def test_file_mode(self):
        io = _make_io(["4"])
        result = run_launcher(io)
        assert result == "file"

    def test_migrate_mode(self):
        io = _make_io(["5"])
        result = run_launcher(io)
        assert result == "migrate"

    def test_default_is_fresh(self):
        """Empty input should return default ('fresh')."""
        io = _make_io([""])
        result = run_launcher(io)
        assert result == "fresh"

    def test_select_by_name(self):
        """Typing the mode name directly should work."""
        io = _make_io(["migrate"])
        result = run_launcher(io)
        assert result == "migrate"

    def test_invalid_then_valid(self):
        """Invalid input followed by valid input should work."""
        io = _make_io(["99", "3"])
        result = run_launcher(io)
        assert result == "config"


# ===========================================================================
# 3. Harness choice  (cc_rig/wizard/harness.py)
# ===========================================================================


class TestAskHarness:
    def test_none_returns_harness_config(self):
        io = _make_io(["1"])
        result = ask_harness(io)
        assert isinstance(result, HarnessConfig)
        assert result.level == "none"

    def test_lite_returns_harness_config(self):
        io = _make_io(["2"])
        result = ask_harness(io)
        assert isinstance(result, HarnessConfig)
        assert result.level == "lite"

    def test_standard_returns_harness_config(self):
        io = _make_io(["3"])
        result = ask_harness(io)
        assert isinstance(result, HarnessConfig)
        assert result.level == "standard"

    def test_autonomy_returns_harness_config(self):
        io = _make_io(["4", "I understand"])
        result = ask_harness(io)
        assert isinstance(result, HarnessConfig)
        assert result.level == "autonomy"

    def test_autonomy_accepted_lowercase(self):
        io = _make_io(["4", "i understand"])
        result = ask_harness(io)
        assert isinstance(result, HarnessConfig)
        assert result.level == "autonomy"

    def test_autonomy_cancelled_on_wrong_confirmation(self):
        io = _make_io(["4", "nope"])
        result = ask_harness(io)
        assert isinstance(result, HarnessConfig)
        assert result.level == "none"

    def test_autonomy_shows_warning(self):
        io = _make_io(["4", "I understand"])
        result = ask_harness(io)
        assert result.level == "autonomy"
        # Check that the warning text was printed
        combined = "\n".join(io._output)
        assert "WARNING" in combined
        assert "AUTONOMOUS" in combined

    def test_non_autonomy_no_warning(self):
        io = _make_io(["1"])
        ask_harness(io)
        combined = "\n".join(io._output)
        assert "WARNING" not in combined
        assert "AUTONOMOUS" not in combined

    def test_lite_no_warning(self):
        io = _make_io(["2"])
        ask_harness(io)
        combined = "\n".join(io._output)
        assert "AUTONOMOUS" not in combined

    def test_standard_no_warning(self):
        io = _make_io(["3"])
        ask_harness(io)
        combined = "\n".join(io._output)
        assert "AUTONOMOUS" not in combined

    def test_default_is_none(self):
        """Empty input should return default ('none')."""
        io = _make_io([""])
        result = ask_harness(io)
        assert result.level == "none"

    def test_select_by_name(self):
        """Typing the level name directly should work."""
        io = _make_io(["autonomy", "I understand"])
        result = ask_harness(io)
        assert result.level == "autonomy"


# ===========================================================================
# 4. Preset management  (cc_rig/presets/manager.py)
# ===========================================================================


class TestListPresetsNoFilter:
    def test_returns_both_types(self):
        result = list_presets()
        assert "templates" in result
        assert "workflows" in result

    def test_templates_nonempty(self):
        result = list_presets()
        assert len(result["templates"]) >= len(BUILTIN_TEMPLATES)

    def test_workflows_nonempty(self):
        result = list_presets()
        assert len(result["workflows"]) >= len(BUILTIN_WORKFLOWS)


class TestListPresetsFiltered:
    def test_filter_templates_only(self):
        result = list_presets(filter_type="templates")
        assert len(result["templates"]) >= len(BUILTIN_TEMPLATES)
        assert len(result["workflows"]) == 0

    def test_filter_workflows_only(self):
        result = list_presets(filter_type="workflows")
        assert len(result["templates"]) == 0
        assert len(result["workflows"]) >= len(BUILTIN_WORKFLOWS)

    def test_filter_templates_has_template_info(self):
        result = list_presets(filter_type="templates")
        for tmpl in result["templates"]:
            assert "name" in tmpl
            assert "language" in tmpl
            assert "framework" in tmpl

    def test_filter_workflows_has_workflow_info(self):
        result = list_presets(filter_type="workflows")
        for wf in result["workflows"]:
            assert "name" in wf
            assert "description" in wf


class TestInspectPreset:
    def test_inspect_fastapi(self):
        result = inspect_preset("fastapi")
        assert isinstance(result, str)
        assert "fastapi" in result.lower()
        assert "Template:" in result

    def test_inspect_standard(self):
        result = inspect_preset("standard")
        assert isinstance(result, str)
        assert "standard" in result.lower()
        assert "Workflow:" in result

    def test_inspect_nonexistent_raises(self):
        with pytest.raises(ValueError, match="Preset not found"):
            inspect_preset("nonexistent")

    def test_inspect_template_contains_tool_commands(self):
        result = inspect_preset("fastapi")
        assert "Tool Commands:" in result

    def test_inspect_workflow_contains_agents(self):
        result = inspect_preset("standard")
        assert "Agents" in result

    @pytest.mark.parametrize("name", BUILTIN_TEMPLATES)
    def test_inspect_all_templates(self, name):
        result = inspect_preset(name)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("name", BUILTIN_WORKFLOWS)
    def test_inspect_all_workflows(self, name):
        result = inspect_preset(name)
        assert isinstance(result, str)
        assert len(result) > 0


class TestCreatePreset:
    def test_creates_workflow_preset(self, tmp_path, monkeypatch):
        # Point _USER_PRESETS_DIR to tmp so we don't pollute real home dir
        user_dir = tmp_path / "user_presets"
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", user_dir)

        # Create a mock .cc-rig.json
        config_data = {
            "project_name": "my-app",
            "language": "python",
            "framework": "fastapi",
            "project_type": "api",
            "test_cmd": "pytest",
            "lint_cmd": "ruff check .",
            "format_cmd": "ruff format .",
            "typecheck_cmd": "mypy .",
            "build_cmd": "",
            "workflow": "standard",
            "agents": ["code-review", "tdd"],
            "commands": ["/test", "/lint"],
            "hooks": ["pre-commit"],
            "features": {"memory": True, "spec_workflow": False},
            "permission_mode": "default",
        }
        config_path = tmp_path / ".cc-rig.json"
        config_path.write_text(json.dumps(config_data))

        dest = create_preset(config_path, "my-workflow", preset_type="workflow")
        assert dest.exists()
        assert dest.suffix == ".json"
        data = json.loads(dest.read_text())
        assert data["name"] == "my-workflow"
        assert "agents" in data
        assert "commands" in data

    def test_creates_template_preset(self, tmp_path, monkeypatch):
        # Point _USER_PRESETS_DIR to tmp so we don't pollute real home dir
        user_dir = tmp_path / "user_presets"
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", user_dir)

        config_data = {
            "project_name": "my-app",
            "language": "python",
            "framework": "fastapi",
            "project_type": "api",
            "test_cmd": "pytest",
            "lint_cmd": "ruff check .",
            "format_cmd": "ruff format .",
            "typecheck_cmd": "mypy .",
            "build_cmd": "",
            "source_dir": "src",
            "test_dir": "tests",
            "recommended_skills": ["tdd"],
            "default_mcps": [],
        }
        config_path = tmp_path / ".cc-rig.json"
        config_path.write_text(json.dumps(config_data))

        dest = create_preset(config_path, "my-template", preset_type="template")
        assert dest.exists()
        assert dest.suffix == ".json"
        data = json.loads(dest.read_text())
        assert data["name"] == "my-template"
        assert data["language"] == "python"
        assert data["framework"] == "fastapi"
        assert "tool_commands" in data
        assert data["tool_commands"]["test"] == "pytest"

    def test_creates_parent_directories(self, tmp_path, monkeypatch):
        """create_preset should create parent dirs if they don't exist."""
        config_data = {
            "project_name": "test",
            "agents": [],
            "commands": [],
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data))

        # Point _USER_PRESETS_DIR to a fresh tmp location
        user_dir = tmp_path / "user_presets"
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", user_dir)

        dest = create_preset(config_path, "custom-wf", preset_type="workflow")
        assert dest.exists()
        assert user_dir in dest.parents or dest.parent.parent == user_dir


class TestInstallPreset:
    def test_installs_workflow_preset(self, tmp_path, monkeypatch):
        # Create a workflow preset file
        preset_data = {
            "name": "my-installed-wf",
            "description": "A custom workflow",
            "agents": ["code-review"],
            "commands": ["/test"],
            "hooks": ["pre-commit"],
            "features": {"memory": False},
            "permission_mode": "default",
        }
        source = tmp_path / "my-wf.json"
        source.write_text(json.dumps(preset_data))

        # Point _USER_PRESETS_DIR to tmp so we don't pollute real home dir
        user_dir = tmp_path / "user_presets"
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", user_dir)

        dest = install_preset(source)
        assert dest.exists()
        assert "workflows" in str(dest)
        data = json.loads(dest.read_text())
        assert data["name"] == "my-installed-wf"

    def test_installs_template_preset(self, tmp_path, monkeypatch):
        preset_data = {
            "name": "my-installed-tmpl",
            "language": "python",
            "framework": "flask",
            "project_type": "web",
        }
        source = tmp_path / "my-tmpl.json"
        source.write_text(json.dumps(preset_data))

        user_dir = tmp_path / "user_presets"
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", user_dir)

        dest = install_preset(source)
        assert dest.exists()
        assert "templates" in str(dest)
        data = json.loads(dest.read_text())
        assert data["name"] == "my-installed-tmpl"

    def test_install_missing_file_raises(self, tmp_path):
        missing = tmp_path / "does-not-exist.json"
        with pytest.raises(FileNotFoundError):
            install_preset(missing)

    def test_install_invalid_json_raises(self, tmp_path, monkeypatch):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {{{")

        user_dir = tmp_path / "user_presets"
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", user_dir)

        with pytest.raises(ValueError, match="Invalid JSON"):
            install_preset(bad_file)

    def test_install_no_name_raises(self, tmp_path, monkeypatch):
        no_name = tmp_path / "noname.json"
        no_name.write_text(json.dumps({"language": "python"}))

        user_dir = tmp_path / "user_presets"
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", user_dir)

        with pytest.raises(ValueError, match="name"):
            install_preset(no_name)

    def test_install_ambiguous_type_raises(self, tmp_path, monkeypatch):
        """Preset without agents/commands or language/framework should fail."""
        ambiguous = tmp_path / "ambiguous.json"
        ambiguous.write_text(json.dumps({"name": "mystery"}))

        user_dir = tmp_path / "user_presets"
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", user_dir)

        with pytest.raises(ValueError, match="Cannot determine type"):
            install_preset(ambiguous)

    def test_installed_preset_file_name_matches_name_field(self, tmp_path, monkeypatch):
        """The installed file should be named after the preset's name field."""
        preset_data = {
            "name": "special-name",
            "language": "go",
            "framework": "gin",
            "project_type": "web",
        }
        source = tmp_path / "whatever-filename.json"
        source.write_text(json.dumps(preset_data))

        user_dir = tmp_path / "user_presets"
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", user_dir)

        dest = install_preset(source)
        assert dest.stem == "special-name"
