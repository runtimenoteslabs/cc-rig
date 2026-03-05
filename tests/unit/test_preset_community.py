"""Tests for community preset validation and lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cc_rig.presets.manager import (
    create_preset,
    install_preset,
    list_presets,
    load_template,
    load_workflow,
    validate_preset,
)

# ── Validation tests ─────────────────────────────────────────────


class TestPresetValidation:
    """Tests for validate_preset()."""

    def test_valid_workflow_passes(self) -> None:
        data = {
            "name": "my-workflow",
            "agents": ["code-reviewer"],
            "commands": ["review"],
        }
        assert validate_preset(data) == []

    def test_valid_template_passes(self) -> None:
        data = {
            "name": "my-template",
            "language": "python",
            "framework": "fastapi",
            "project_type": "web",
        }
        assert validate_preset(data) == []

    def test_missing_name_rejected(self) -> None:
        data = {"agents": [], "commands": []}
        errors = validate_preset(data)
        assert len(errors) == 1
        assert "name" in errors[0]

    def test_ambiguous_type_rejected(self) -> None:
        data = {"name": "ambiguous"}
        errors = validate_preset(data)
        assert len(errors) == 1
        assert "Cannot determine type" in errors[0]

    def test_missing_agents_field_rejected(self) -> None:
        """Workflow with commands but no agents key."""
        data = {"name": "bad", "commands": ["review"]}
        errors = validate_preset(data)
        assert any("Cannot determine type" in e for e in errors)

    def test_agents_not_list_rejected(self) -> None:
        data = {
            "name": "bad",
            "agents": "code-reviewer",
            "commands": ["review"],
        }
        errors = validate_preset(data)
        assert any("'agents' must be a list" in e for e in errors)

    def test_commands_not_list_rejected(self) -> None:
        data = {
            "name": "bad",
            "agents": ["code-reviewer"],
            "commands": "review",
        }
        errors = validate_preset(data)
        assert any("'commands' must be a list" in e for e in errors)

    def test_template_missing_project_type(self) -> None:
        data = {
            "name": "my-template",
            "language": "python",
            "framework": "fastapi",
        }
        errors = validate_preset(data)
        assert any("project_type" in e for e in errors)


# ── Lifecycle tests ──────────────────────────────────────────────


class TestPresetLifecycle:
    """Tests for create/install/list preset lifecycle."""

    def test_create_workflow_from_config(self, tmp_path: Path) -> None:
        config = {
            "project_name": "test",
            "template_preset": "fastapi",
            "workflow": "standard",
            "agents": ["code-reviewer"],
            "commands": ["review"],
            "hooks": [],
            "features": {},
            "permission_mode": "default",
        }
        config_path = tmp_path / ".cc-rig.json"
        config_path.write_text(json.dumps(config))

        dest = create_preset(config_path, "my-wf", preset_type="workflow")
        assert dest.exists()
        data = json.loads(dest.read_text())
        assert data["name"] == "my-wf"
        assert "agents" in data
        assert "commands" in data

    def test_create_template_from_config(self, tmp_path: Path) -> None:
        config = {
            "project_name": "test",
            "language": "python",
            "framework": "fastapi",
            "project_type": "web",
            "test_cmd": "pytest",
            "lint_cmd": "ruff check .",
            "format_cmd": "ruff format .",
            "typecheck_cmd": "mypy .",
            "source_dir": "app",
            "test_dir": "tests",
        }
        config_path = tmp_path / ".cc-rig.json"
        config_path.write_text(json.dumps(config))

        dest = create_preset(config_path, "my-tmpl", preset_type="template")
        assert dest.exists()
        data = json.loads(dest.read_text())
        assert data["name"] == "my-tmpl"
        assert data["language"] == "python"

    def test_install_valid_preset(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", tmp_path / "presets")

        preset_data = {
            "name": "community-wf",
            "agents": ["explorer"],
            "commands": ["research"],
        }
        src = tmp_path / "community-wf.json"
        src.write_text(json.dumps(preset_data))

        dest = install_preset(src)
        assert dest.exists()
        assert "workflows" in str(dest)

    def test_install_invalid_preset_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", tmp_path / "presets")

        # Missing name
        src = tmp_path / "bad.json"
        src.write_text(json.dumps({"agents": [], "commands": []}))

        with pytest.raises(ValueError, match="Invalid preset"):
            install_preset(src)

    def test_installed_preset_in_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", tmp_path / "presets")

        preset_data = {
            "name": "listed-wf",
            "description": "A listed workflow",
            "agents": ["explorer"],
            "commands": ["research"],
        }
        src = tmp_path / "listed-wf.json"
        src.write_text(json.dumps(preset_data))
        install_preset(src)

        result = list_presets(filter_type="workflows")
        wf_names = [w["name"] for w in result["workflows"]]
        assert "listed-wf" in wf_names

    def test_installed_preset_loadable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", tmp_path / "presets")

        preset_data = {
            "name": "loadable-tmpl",
            "language": "rust",
            "framework": "custom-rust",
            "project_type": "cli",
        }
        src = tmp_path / "loadable-tmpl.json"
        src.write_text(json.dumps(preset_data))
        install_preset(src)

        loaded = load_template("loadable-tmpl")
        assert loaded["language"] == "rust"

    def test_create_then_use_round_trip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("cc_rig.presets.manager._USER_PRESETS_DIR", tmp_path / "presets")

        config = {
            "project_name": "roundtrip",
            "agents": ["architect", "test-writer"],
            "commands": ["plan", "test"],
            "hooks": ["pre-commit"],
            "features": {"memory": True},
            "permission_mode": "default",
        }
        config_path = tmp_path / ".cc-rig.json"
        config_path.write_text(json.dumps(config))

        # Create a workflow preset
        dest = create_preset(config_path, "roundtrip-wf", preset_type="workflow")

        # Copy to a separate location (simulating sharing to another machine)
        shared = tmp_path / "shared" / "roundtrip-wf.json"
        shared.parent.mkdir(parents=True)
        import shutil

        shutil.copy2(dest, shared)

        # Remove original and re-install from the shared copy
        dest.unlink()
        install_preset(shared)

        # Load it back
        loaded = load_workflow("roundtrip-wf")
        assert loaded["name"] == "roundtrip-wf"
        assert "architect" in loaded["agents"]
        assert "test-writer" in loaded["agents"]
