"""Tests for config management: save, load, list, inspect, diff, lock."""

import json

import pytest

from cc_rig.cli import main
from cc_rig.config.defaults import compute_defaults
from cc_rig.config.manager import (
    diff_configs,
    inspect_config,
    is_locked,
    list_configs,
    load_config,
    lock_config,
    save_config,
    unlock_config,
)
from cc_rig.config.project import ProjectConfig


def _make_config(template="fastapi", workflow="standard"):
    return compute_defaults(template, workflow, project_name="test-project")


class TestSaveLoad:
    def test_save_and_load_round_trip(self, tmp_path):
        config = _make_config()
        path = save_config(config, path=tmp_path / "test.json")
        loaded = load_config(str(path))
        assert loaded.project_name == config.project_name
        assert loaded.framework == config.framework
        assert loaded.workflow == config.workflow
        assert loaded.agents == config.agents
        assert loaded.features.memory == config.features.memory

    def test_save_by_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cc_rig.config.manager._CONFIG_DIR",
            tmp_path,
        )
        config = _make_config()
        path = save_config(config, name="my-config")
        assert path == tmp_path / "my-config.json"
        assert path.exists()

    def test_save_default_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cc_rig.config.manager._CONFIG_DIR",
            tmp_path,
        )
        config = _make_config()
        path = save_config(config)
        assert path.name == "test-project.json"

    def test_save_portable_strips_output_dir(self, tmp_path):
        config = _make_config()
        config.output_dir = "/home/user/specific/path"
        path = save_config(
            config,
            path=tmp_path / "portable.json",
            portable=True,
        )
        data = json.loads(path.read_text())
        assert "output_dir" not in data

    def test_save_portable_strips_created_at(self, tmp_path):
        config = _make_config()
        config.created_at = "2026-02-22T12:00:00"
        path = save_config(
            config,
            path=tmp_path / "portable.json",
            portable=True,
        )
        data = json.loads(path.read_text())
        assert "created_at" not in data

    def test_load_by_path(self, tmp_path):
        config = _make_config()
        path = save_config(config, path=tmp_path / "direct.json")
        loaded = load_config(str(path))
        assert loaded.framework == "fastapi"

    def test_load_by_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cc_rig.config.manager._CONFIG_DIR",
            tmp_path,
        )
        config = _make_config()
        save_config(config, name="named-config")
        loaded = load_config("named-config")
        assert loaded.framework == "fastapi"

    def test_load_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(str(tmp_path / "nonexistent.json"))

    def test_load_invalid_json_raises(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_config(str(bad))


class TestListConfigs:
    def test_list_personal(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cc_rig.config.manager._CONFIG_DIR",
            tmp_path,
        )
        config = _make_config()
        save_config(config, name="alpha")
        save_config(config, name="beta")

        result = list_configs()
        assert len(result["personal"]) == 2
        names = {c["name"] for c in result["personal"]}
        assert names == {"alpha", "beta"}

    def test_list_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cc_rig.config.manager._CONFIG_DIR",
            tmp_path / "empty_personal",
        )
        config = _make_config()
        save_config(config, path=tmp_path / ".cc-rig.json")

        result = list_configs(project_dir=tmp_path)
        assert len(result["project"]) == 1
        assert result["project"][0]["template"] == "fastapi"

    def test_list_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cc_rig.config.manager._CONFIG_DIR",
            tmp_path / "empty_configs",
        )
        result = list_configs()
        assert result["personal"] == []
        assert result["project"] == []

    def test_list_shows_locked(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cc_rig.config.manager._CONFIG_DIR",
            tmp_path,
        )
        config = _make_config()
        save_config(config, name="locked-cfg")
        lock_config(str(tmp_path / "locked-cfg.json"))

        result = list_configs()
        locked_items = [c for c in result["personal"] if c["locked"]]
        assert len(locked_items) == 1


class TestInspect:
    def test_inspect_contains_key_fields(self, tmp_path):
        config = _make_config()
        path = save_config(config, path=tmp_path / "test.json")
        output = inspect_config(str(path))
        assert "test-project" in output
        assert "fastapi" in output
        assert "standard" in output
        assert "python" in output

    def test_inspect_locked_badge(self, tmp_path):
        config = _make_config()
        path = save_config(config, path=tmp_path / "test.json")
        lock_config(str(path))
        output = inspect_config(str(path))
        assert "[LOCKED]" in output

    def test_inspect_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            inspect_config(str(tmp_path / "nope.json"))


class TestDiff:
    def test_identical_configs_empty_diff(self):
        a = _make_config()
        b = ProjectConfig.from_dict(a.to_dict())
        result = diff_configs(a, b)
        assert result == ""

    def test_different_workflow_shows_diff(self):
        a = _make_config("fastapi", "standard")
        b = _make_config("fastapi", "rigorous")
        result = diff_configs(a, b)
        assert "workflow" in result
        assert "standard" in result
        assert "rigorous" in result

    def test_different_template_shows_diff(self):
        a = _make_config("fastapi", "standard")
        b = _make_config("django", "standard")
        result = diff_configs(a, b)
        assert "framework" in result
        assert "fastapi" in result
        assert "django" in result

    def test_diff_shows_agent_differences(self):
        a = _make_config("fastapi", "speedrun")
        b = _make_config("fastapi", "verify-heavy")
        result = diff_configs(a, b)
        assert "agents" in result


class TestLock:
    def test_lock_and_check(self, tmp_path):
        config = _make_config()
        path = save_config(config, path=tmp_path / "test.json")
        assert not is_locked(str(path))
        lock_config(str(path))
        assert is_locked(str(path))

    def test_unlock(self, tmp_path):
        config = _make_config()
        path = save_config(config, path=tmp_path / "test.json")
        lock_config(str(path))
        assert is_locked(str(path))
        unlock_config(str(path))
        assert not is_locked(str(path))

    def test_lock_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            lock_config(str(tmp_path / "nope.json"))

    def test_lock_preserved_on_load(self, tmp_path):
        config = _make_config()
        path = save_config(config, path=tmp_path / "test.json")
        lock_config(str(path))
        data = json.loads(path.read_text())
        assert data["locked"] is True

    def test_locked_not_in_default_config(self, tmp_path):
        config = _make_config()
        path = save_config(config, path=tmp_path / "test.json")
        data = json.loads(path.read_text())
        assert "locked" not in data


class TestCLIConfigCommands:
    def test_config_list_runs(self, capsys, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cc_rig.config.manager._CONFIG_DIR",
            tmp_path / "empty",
        )
        rc = main(["config", "list"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "personal" in captured.out.lower() or "No" in captured.out

    def test_config_default_is_list(self, capsys, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cc_rig.config.manager._CONFIG_DIR",
            tmp_path / "empty",
        )
        rc = main(["config"])
        assert rc == 0

    def test_config_inspect_works(self, capsys, tmp_path):
        config = _make_config()
        path = save_config(config, path=tmp_path / "test.json")
        rc = main(["config", "inspect", str(path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "fastapi" in captured.out

    def test_config_lock_and_inspect(self, capsys, tmp_path):
        config = _make_config()
        path = save_config(config, path=tmp_path / "test.json")
        rc = main(["config", "lock", str(path)])
        assert rc == 0
        rc = main(["config", "inspect", str(path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "LOCKED" in captured.out
