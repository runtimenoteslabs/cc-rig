"""Tests for post-generation validator."""

import json

from cc_rig.config.defaults import compute_defaults
from cc_rig.validator import validate_output


def _make_config():
    return compute_defaults("fastapi", "standard", project_name="test")


class TestValidatorCatchesErrors:
    def test_missing_claude_md(self, tmp_path):
        config = _make_config()
        result = validate_output(config, tmp_path)
        assert not result.passed
        assert any("CLAUDE.md" in i.message for i in result.errors)

    def test_empty_claude_md(self, tmp_path):
        config = _make_config()
        (tmp_path / "CLAUDE.md").write_text("")
        result = validate_output(config, tmp_path)
        assert any("empty" in i.message.lower() for i in result.errors)

    def test_invalid_json(self, tmp_path):
        config = _make_config()
        (tmp_path / "CLAUDE.md").write_text("# Test\nContent\n")
        # Place bad JSON in a managed directory so the scoped validator finds it
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "bad.json").write_text("{invalid json")
        result = validate_output(config, tmp_path)
        assert any("Invalid JSON" in i.message for i in result.errors)

    def test_invalid_hook_event(self, tmp_path):
        config = _make_config()
        (tmp_path / "CLAUDE.md").write_text("# Test\nContent\n")
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings = {
            "hooks": {
                "InvalidEvent": [{"matcher": "", "hooks": [{"type": "prompt", "prompt": "test"}]}]
            }
        }
        (claude_dir / "settings.json").write_text(json.dumps(settings))
        result = validate_output(config, tmp_path)
        assert any("Unknown hook event" in i.message for i in result.errors)

    def test_invalid_hook_type(self, tmp_path):
        config = _make_config()
        (tmp_path / "CLAUDE.md").write_text("# Test\nContent\n")
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings = {
            "hooks": {"Stop": [{"matcher": "", "hooks": [{"type": "invalid", "command": "x"}]}]}
        }
        (claude_dir / "settings.json").write_text(json.dumps(settings))
        result = validate_output(config, tmp_path)
        assert any("Invalid hook type" in i.message for i in result.errors)

    def test_empty_file_detected(self, tmp_path):
        config = _make_config()
        (tmp_path / "CLAUDE.md").write_text("# Test\nContent\n")
        # Place empty file in a managed directory so the scoped validator finds it
        agent_docs = tmp_path / "agent_docs"
        agent_docs.mkdir(parents=True, exist_ok=True)
        (agent_docs / "empty.md").write_text("")
        result = validate_output(config, tmp_path)
        assert any("Empty file" in i.message for i in result.errors)

    def test_missing_agent_files(self, tmp_path):
        config = _make_config()
        (tmp_path / "CLAUDE.md").write_text("# Test\nContent\n")
        result = validate_output(config, tmp_path)
        assert any("Agent file missing" in i.message for i in result.errors)

    def test_missing_command_files(self, tmp_path):
        config = _make_config()
        (tmp_path / "CLAUDE.md").write_text("# Test\nContent\n")
        result = validate_output(config, tmp_path)
        assert any("Command file missing" in i.message for i in result.errors)

    def test_missing_memory_files(self, tmp_path):
        config = _make_config()
        assert config.features.memory is True
        (tmp_path / "CLAUDE.md").write_text("# Test\nContent\n")
        result = validate_output(config, tmp_path)
        assert any("Memory file missing" in i.message for i in result.errors)


class TestValidatorPasses:
    def test_no_memory_check_when_disabled(self, tmp_path):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        assert config.features.memory is False
        (tmp_path / "CLAUDE.md").write_text("# Test\nContent\n")
        result = validate_output(config, tmp_path)
        assert not any("Memory" in i.message for i in result.issues)


class TestManifestCheck:
    def test_untracked_file_warned(self, tmp_path):
        config = _make_config()
        (tmp_path / "CLAUDE.md").write_text("# Test\nContent\n")
        # Place untracked file in a managed directory so scoped check finds it
        memory_dir = tmp_path / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "extra.txt").write_text("untracked")
        manifest = {"files": ["CLAUDE.md"]}
        result = validate_output(config, tmp_path, manifest)
        assert any("not in manifest" in i.message for i in result.warnings)


class TestPlaceholderDetection:
    def test_detects_todo_placeholder(self, tmp_path):
        config = _make_config()
        (tmp_path / "CLAUDE.md").write_text("# Test\n<!-- TODO fill in -->\n")
        result = validate_output(config, tmp_path)
        assert any("Placeholder" in i.message for i in result.warnings)

    def test_clean_file_no_placeholder_warning(self, tmp_path):
        config = _make_config()
        (tmp_path / "CLAUDE.md").write_text("# Project\nReal content here.\n")
        result = validate_output(config, tmp_path)
        assert not any("Placeholder" in i.message for i in result.warnings)
