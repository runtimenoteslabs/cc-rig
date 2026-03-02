"""Tests for command file YAML frontmatter validation.

Adds proper YAML parsing (matching agents test pattern) and systematic
$ARGUMENTS validation for all commands.
"""

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.commands import _COMMAND_DEFS
from cc_rig.presets.manager import BUILTIN_WORKFLOWS


def _parse_frontmatter(content):
    """Parse YAML frontmatter from command markdown file.

    Returns (fields_dict, body) or raises ValueError.
    """
    if not content.startswith("---\n"):
        raise ValueError("Missing opening ---")
    end = content.index("\n---\n", 4)
    yaml_block = content[4:end]
    body = content[end + 5 :]
    fields = {}
    for line in yaml_block.splitlines():
        key, _, value = line.partition(": ")
        fields[key.strip()] = value.strip()
    return fields, body


def _generate_commands(template, workflow, tmp_path):
    from cc_rig.generators.commands import generate_commands

    config = compute_defaults(template, workflow, project_name="test")
    files = generate_commands(config, tmp_path)
    return config, files


class TestFrontmatterParsing:
    """All commands should have valid YAML frontmatter."""

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_all_commands_parse_frontmatter(self, workflow, tmp_path):
        config, _ = _generate_commands("fastapi", workflow, tmp_path)
        for cmd in config.commands:
            content = (tmp_path / ".claude" / "commands" / f"{cmd}.md").read_text()
            fields, body = _parse_frontmatter(content)
            assert fields, f"{cmd}.md has empty frontmatter"
            assert body.strip(), f"{cmd}.md has empty body"

    def test_all_commands_have_description_field(self, tmp_path):
        config, _ = _generate_commands("fastapi", "standard", tmp_path)
        for cmd in config.commands:
            content = (tmp_path / ".claude" / "commands" / f"{cmd}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            assert "description" in fields, f"{cmd}.md missing description in frontmatter"
            assert len(fields["description"]) > 5, f"{cmd}.md description too short"

    def test_all_commands_have_allowed_tools(self, tmp_path):
        config, _ = _generate_commands("fastapi", "standard", tmp_path)
        for cmd in config.commands:
            content = (tmp_path / ".claude" / "commands" / f"{cmd}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            assert "allowed-tools" in fields, f"{cmd}.md missing allowed-tools"

    def test_allowed_tools_are_valid(self, tmp_path):
        valid_tools = {
            "Read",
            "Write",
            "Edit",
            "Bash",
            "Glob",
            "Grep",
            "WebSearch",
            "WebFetch",
            "Task",
            "NotebookEdit",
        }
        config, _ = _generate_commands("fastapi", "standard", tmp_path)
        for cmd in config.commands:
            content = (tmp_path / ".claude" / "commands" / f"{cmd}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            tools = {t.strip() for t in fields.get("allowed-tools", "").split(",")}
            for tool in tools:
                assert tool in valid_tools, f"{cmd}.md has invalid tool '{tool}'"


class TestArgumentsSubstitution:
    """All commands should include $ARGUMENTS in their body."""

    def test_all_commands_have_arguments(self, tmp_path):
        config, _ = _generate_commands("fastapi", "standard", tmp_path)
        for cmd in config.commands:
            content = (tmp_path / ".claude" / "commands" / f"{cmd}.md").read_text()
            _, body = _parse_frontmatter(content)
            assert "$ARGUMENTS" in body, f"{cmd}.md missing $ARGUMENTS"

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_arguments_present_all_workflows(self, workflow, tmp_path):
        config, _ = _generate_commands("fastapi", workflow, tmp_path)
        for cmd in config.commands:
            content = (tmp_path / ".claude" / "commands" / f"{cmd}.md").read_text()
            _, body = _parse_frontmatter(content)
            assert "$ARGUMENTS" in body, f"{cmd}.md missing $ARGUMENTS in {workflow}"


class TestCommandDefConsistency:
    """_COMMAND_DEFS should be well-formed."""

    def test_all_defs_have_three_fields(self):
        for name, defn in _COMMAND_DEFS.items():
            assert len(defn) == 3, f"{name} should have 3 fields"

    def test_all_defs_have_nonempty_description(self):
        for name, (desc, _, _) in _COMMAND_DEFS.items():
            assert len(desc) > 5, f"{name} has empty/short description"

    def test_all_defs_have_nonempty_body(self):
        for name, (_, _, body) in _COMMAND_DEFS.items():
            assert len(body) > 10, f"{name} has empty/short body"

    def test_all_defs_have_arguments_in_body(self):
        for name, (_, _, body) in _COMMAND_DEFS.items():
            assert "$ARGUMENTS" in body, f"{name} missing $ARGUMENTS in body"

    def test_no_duplicate_descriptions(self):
        descriptions = [desc for desc, _, _ in _COMMAND_DEFS.values()]
        assert len(descriptions) == len(set(descriptions)), "Duplicate descriptions"
