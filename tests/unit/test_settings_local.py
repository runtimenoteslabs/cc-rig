"""Unit tests for .claude/settings.local.json generation."""

import json

from cc_rig.generators.fileops import FileTracker
from cc_rig.generators.settings_local import generate_settings_local


class TestSettingsLocalGeneration:
    def test_generates_file(self, tmp_path):
        generate_settings_local(tmp_path)
        assert (tmp_path / ".claude" / "settings.local.json").exists()

    def test_returns_correct_path(self, tmp_path):
        paths = generate_settings_local(tmp_path)
        assert paths == [".claude/settings.local.json"]

    def test_generates_valid_json(self, tmp_path):
        generate_settings_local(tmp_path)
        content = (tmp_path / ".claude" / "settings.local.json").read_text()
        data = json.loads(content)  # should not raise
        assert isinstance(data, dict)

    def test_has_permissions_key(self, tmp_path):
        generate_settings_local(tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.local.json").read_text())
        assert "permissions" in data
        assert "allow" in data["permissions"]
        assert "deny" in data["permissions"]

    def test_permissions_are_empty(self, tmp_path):
        generate_settings_local(tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.local.json").read_text())
        assert data["permissions"]["allow"] == []
        assert data["permissions"]["deny"] == []

    def test_has_env_key(self, tmp_path):
        generate_settings_local(tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.local.json").read_text())
        assert "env" in data
        assert data["env"] == {}

    def test_trailing_newline(self, tmp_path):
        generate_settings_local(tmp_path)
        content = (tmp_path / ".claude" / "settings.local.json").read_text()
        assert content.endswith("\n")


class TestSettingsLocalWithTracker:
    def test_uses_tracker(self, tmp_path):
        tracker = FileTracker(tmp_path)
        paths = generate_settings_local(tmp_path, tracker=tracker)
        assert (tmp_path / ".claude" / "settings.local.json").exists()
        assert paths == [".claude/settings.local.json"]

    def test_preserve_on_clean_metadata(self, tmp_path):
        tracker = FileTracker(tmp_path)
        generate_settings_local(tmp_path, tracker=tracker)
        meta = tracker.metadata()
        assert ".claude/settings.local.json" in meta
        assert meta[".claude/settings.local.json"].get("preserve_on_clean") is True

    def test_content_identical_with_and_without_tracker(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        generate_settings_local(dir_a)
        generate_settings_local(dir_b, tracker=FileTracker(dir_b))
        content_a = (dir_a / ".claude" / "settings.local.json").read_text()
        content_b = (dir_b / ".claude" / "settings.local.json").read_text()
        assert content_a == content_b
