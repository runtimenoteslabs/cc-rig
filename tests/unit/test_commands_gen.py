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


def _read_command(tmp_path, name):
    return (tmp_path / ".claude" / "commands" / f"{name}.md").read_text()


def _generate_commands_with_gtd(tmp_path):
    """Generate commands with GTD features enabled explicitly."""
    from cc_rig.generators.commands import generate_commands

    config = compute_defaults("fastapi", "standard", project_name="test-project")
    config.features.gtd = True
    config.features.worktrees = True
    config.commands = list(config.commands) + [
        "gtd-capture",
        "gtd-process",
        "daily-plan",
        "worktree",
    ]
    files = generate_commands(config, tmp_path)
    return config, files


class TestSpecCommandContent:
    """Validate spec-create and spec-execute command content."""

    def test_spec_create_description_mentions_specification(self, tmp_path):
        _generate_commands("fastapi", "spec-driven", tmp_path)
        content = _read_command(tmp_path, "spec-create")
        assert "specification" in content.lower()

    def test_spec_create_tools_include_read_write(self, tmp_path):
        _generate_commands("fastapi", "spec-driven", tmp_path)
        content = _read_command(tmp_path, "spec-create")
        assert "Read" in content
        assert "Write" in content

    def test_spec_create_tools_exclude_bash(self, tmp_path):
        _generate_commands("fastapi", "spec-driven", tmp_path)
        content = _read_command(tmp_path, "spec-create")
        # Extract allowed-tools line from frontmatter
        for line in content.splitlines():
            if line.startswith("allowed-tools:"):
                assert "Bash" not in line
                break

    def test_spec_create_body_references_specs_dir(self, tmp_path):
        _generate_commands("fastapi", "spec-driven", tmp_path)
        content = _read_command(tmp_path, "spec-create")
        assert "specs/" in content

    def test_spec_create_has_arguments(self, tmp_path):
        _generate_commands("fastapi", "spec-driven", tmp_path)
        content = _read_command(tmp_path, "spec-create")
        assert "$ARGUMENTS" in content

    def test_spec_execute_description_mentions_task_and_spec(self, tmp_path):
        _generate_commands("fastapi", "spec-driven", tmp_path)
        content = _read_command(tmp_path, "spec-execute")
        lower = content.lower()
        assert "task" in lower
        assert "spec" in lower

    def test_spec_execute_tools_include_bash(self, tmp_path):
        _generate_commands("fastapi", "spec-driven", tmp_path)
        content = _read_command(tmp_path, "spec-execute")
        for line in content.splitlines():
            if line.startswith("allowed-tools:"):
                assert "Bash" in line
                break

    def test_spec_execute_body_references_tests(self, tmp_path):
        _generate_commands("fastapi", "spec-driven", tmp_path)
        content = _read_command(tmp_path, "spec-execute")
        assert "test" in content.lower()

    def test_spec_commands_absent_in_speedrun(self, tmp_path):
        config, _ = _generate_commands("fastapi", "speedrun", tmp_path)
        assert "spec-create" not in config.commands
        assert "spec-execute" not in config.commands


class TestGtdCommandContent:
    """Validate gtd-capture, gtd-process, and daily-plan command content.

    GTD commands are only generated when features.gtd is explicitly enabled.
    gtd-lite now maps to the standard tier without enabling gtd by default.
    """

    def test_gtd_capture_body_references_inbox(self, tmp_path):
        _generate_commands_with_gtd(tmp_path)
        content = _read_command(tmp_path, "gtd-capture")
        assert "tasks/inbox.md" in content

    def test_gtd_capture_tools_exclude_bash(self, tmp_path):
        _generate_commands_with_gtd(tmp_path)
        content = _read_command(tmp_path, "gtd-capture")
        for line in content.splitlines():
            if line.startswith("allowed-tools:"):
                assert "Bash" not in line
                break

    def test_gtd_capture_has_arguments(self, tmp_path):
        _generate_commands_with_gtd(tmp_path)
        content = _read_command(tmp_path, "gtd-capture")
        assert "$ARGUMENTS" in content

    def test_gtd_process_references_inbox(self, tmp_path):
        _generate_commands_with_gtd(tmp_path)
        content = _read_command(tmp_path, "gtd-process")
        assert "tasks/inbox.md" in content

    def test_gtd_process_references_todo(self, tmp_path):
        _generate_commands_with_gtd(tmp_path)
        content = _read_command(tmp_path, "gtd-process")
        assert "tasks/todo.md" in content

    def test_gtd_process_references_someday(self, tmp_path):
        _generate_commands_with_gtd(tmp_path)
        content = _read_command(tmp_path, "gtd-process")
        assert "tasks/someday.md" in content

    def test_daily_plan_references_todo(self, tmp_path):
        _generate_commands_with_gtd(tmp_path)
        content = _read_command(tmp_path, "daily-plan")
        assert "todo.md" in content

    def test_daily_plan_references_session_log(self, tmp_path):
        _generate_commands_with_gtd(tmp_path)
        content = _read_command(tmp_path, "daily-plan")
        assert "session-log.md" in content

    def test_gtd_commands_absent_in_standard(self, tmp_path):
        config, _ = _generate_commands("fastapi", "standard", tmp_path)
        assert "gtd-capture" not in config.commands
        assert "gtd-process" not in config.commands
        assert "daily-plan" not in config.commands
