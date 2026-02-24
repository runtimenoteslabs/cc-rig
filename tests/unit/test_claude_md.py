"""Tests for CLAUDE.md generator: ordering, sections, line counts."""

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.presets.manager import BUILTIN_TEMPLATES, BUILTIN_WORKFLOWS


def _generate_claude_md(template, workflow, tmp_path):
    from cc_rig.generators.claude_md import generate_claude_md

    config = compute_defaults(template, workflow, project_name="test-project")
    generate_claude_md(config, tmp_path)
    return (tmp_path / "CLAUDE.md").read_text()


class TestStaticFirstOrdering:
    def test_static_before_dynamic(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        # Project identity is the h1 title at top, Current Context
        # is a ## section at the end. Verify ordering.
        assert content.startswith("# ")
        assert "## Current Context" in content
        # All ## headers should appear after the h1 title
        first_h1 = content.index("# ")
        last_dynamic = content.index("## Current Context")
        assert first_h1 < last_dynamic

    def test_commands_before_context(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        assert content.index("## Commands") < content.index("## Current Context")

    def test_guardrails_before_context(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        assert content.index("## Guardrails") < content.index("## Current Context")


class TestConditionalSections:
    def test_memory_section_when_enabled(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        assert "## Memory" in content

    def test_no_memory_section_when_disabled(self, tmp_path):
        content = _generate_claude_md("fastapi", "speedrun", tmp_path)
        assert "## Memory" not in content

    def test_spec_section_when_enabled(self, tmp_path):
        content = _generate_claude_md("fastapi", "spec-driven", tmp_path)
        assert "## Spec Workflow" in content

    def test_gtd_section_when_enabled(self, tmp_path):
        content = _generate_claude_md("fastapi", "gtd-lite", tmp_path)
        assert "## GTD System" in content

    def test_worktree_section_when_enabled(self, tmp_path):
        content = _generate_claude_md("fastapi", "spec-driven", tmp_path)
        assert "## Worktrees" in content

    def test_no_gtd_in_speedrun(self, tmp_path):
        content = _generate_claude_md("fastapi", "speedrun", tmp_path)
        assert "## GTD" not in content


class TestLineCounts:
    _TARGETS = {
        "speedrun": 65,
        "standard": 85,
        "spec-driven": 100,
        "gtd-lite": 100,
        "verify-heavy": 110,
    }

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_line_count_within_target(self, workflow, tmp_path):
        content = _generate_claude_md("fastapi", workflow, tmp_path)
        line_count = content.count("\n") + 1
        target = self._TARGETS[workflow]
        assert line_count <= target, f"{workflow}: {line_count} lines exceeds target {target}"


class TestFrameworkSpecificContent:
    def test_fastapi_mentions_framework(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        assert "fastapi" in content.lower() or "FastAPI" in content

    def test_nextjs_mentions_framework(self, tmp_path):
        content = _generate_claude_md("nextjs", "standard", tmp_path)
        assert "next" in content.lower() or "Next" in content

    def test_rust_mentions_framework(self, tmp_path):
        content = _generate_claude_md("rust-cli", "standard", tmp_path)
        assert "cargo" in content.lower() or "rust" in content.lower()

    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_every_template_has_framework_rules(self, template, tmp_path):
        content = _generate_claude_md(template, "standard", tmp_path)
        assert "## Framework Rules" in content


class TestProjectIdentity:
    def test_project_name_in_output(self, tmp_path):
        from cc_rig.generators.claude_md import generate_claude_md

        config = compute_defaults("fastapi", "standard", project_name="my-cool-api")
        generate_claude_md(config, tmp_path)
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "my-cool-api" in content

    def test_language_in_output(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        assert "python" in content.lower() or "Python" in content
