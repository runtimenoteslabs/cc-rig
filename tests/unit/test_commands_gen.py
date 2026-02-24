"""Tests for command file generator."""

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.presets.manager import BUILTIN_WORKFLOWS


def _generate_commands(template, workflow, tmp_path):
    from cc_rig.generators.commands import generate_commands

    config = compute_defaults(template, workflow, project_name="test-project")
    files = generate_commands(config, tmp_path)
    return config, files


class TestCommandFileGeneration:
    def test_correct_number_of_files(self, tmp_path):
        config, files = _generate_commands("fastapi", "standard", tmp_path)
        assert len(files) == len(config.commands)

    def test_files_exist(self, tmp_path):
        config, files = _generate_commands("fastapi", "standard", tmp_path)
        for cmd in config.commands:
            path = tmp_path / ".claude" / "commands" / f"{cmd}.md"
            assert path.exists(), f"Missing: {cmd}.md"

    def test_files_not_empty(self, tmp_path):
        config, _ = _generate_commands("fastapi", "standard", tmp_path)
        for cmd in config.commands:
            path = tmp_path / ".claude" / "commands" / f"{cmd}.md"
            assert path.stat().st_size > 20, f"{cmd}.md too small"

    def test_commands_have_frontmatter(self, tmp_path):
        config, _ = _generate_commands("fastapi", "standard", tmp_path)
        for cmd in config.commands:
            content = (tmp_path / ".claude" / "commands" / f"{cmd}.md").read_text()
            assert content.startswith("---"), f"{cmd}.md missing frontmatter"

    def test_commands_have_description(self, tmp_path):
        config, _ = _generate_commands("fastapi", "standard", tmp_path)
        for cmd in config.commands:
            content = (tmp_path / ".claude" / "commands" / f"{cmd}.md").read_text()
            assert "description:" in content.lower(), f"{cmd}.md missing description"


class TestAllWorkflows:
    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_commands_generated_for_workflow(self, workflow, tmp_path):
        config, files = _generate_commands("fastapi", workflow, tmp_path)
        assert len(files) == len(config.commands)
        for f in files:
            path = tmp_path / f
            assert path.exists()
            assert path.stat().st_size > 0


class TestCommandContent:
    def test_fix_issue_has_arguments(self, tmp_path):
        _generate_commands("fastapi", "standard", tmp_path)
        content = (tmp_path / ".claude" / "commands" / "fix-issue.md").read_text()
        assert "$ARGUMENTS" in content

    def test_review_command_exists(self, tmp_path):
        _generate_commands("fastapi", "standard", tmp_path)
        path = tmp_path / ".claude" / "commands" / "review.md"
        assert path.exists()
