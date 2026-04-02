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
        "speedrun": 84,
        "standard": 123,
        "gstack": 151,
        "aihero": 164,
        "spec-driven": 161,
        "superpowers": 171,
        "gtd": 162,
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
    def test_every_template_has_rules_section(self, template, tmp_path):
        content = _generate_claude_md(template, "standard", tmp_path)
        # Generic uses "## Project Rules" instead of "## Framework Rules"
        if template == "generic":
            assert "## Project Rules" in content
        else:
            assert "## Framework Rules" in content


class TestAgentDocsImports:
    def test_agent_docs_uses_at_imports(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        assert "@agent_docs/architecture.md" in content
        assert "@agent_docs/conventions.md" in content

    def test_agent_docs_no_plain_text_pointers(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        assert "Read these files for project-specific guidance:" not in content


class TestMemorySection:
    def test_memory_section_explains_both_systems(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        assert "Auto-memory" in content
        assert "Team memory" in content

    def test_memory_section_has_file_list(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        assert "memory/decisions.md" in content
        assert "memory/patterns.md" in content


class TestSpecSectionContent:
    """Validate spec workflow section references correct commands and paths."""

    def test_references_spec_create_command(self, tmp_path):
        content = _generate_claude_md("fastapi", "spec-driven", tmp_path)
        assert "/spec-create" in content

    def test_references_spec_execute_command(self, tmp_path):
        content = _generate_claude_md("fastapi", "spec-driven", tmp_path)
        assert "/spec-execute" in content

    def test_references_specs_directory(self, tmp_path):
        content = _generate_claude_md("fastapi", "spec-driven", tmp_path)
        assert "specs/" in content

    def test_mentions_acceptance_criteria(self, tmp_path):
        content = _generate_claude_md("fastapi", "spec-driven", tmp_path)
        assert "acceptance criteria" in content.lower()


class TestGtdSectionContent:
    """Validate GTD section references all task files and commands."""

    def test_references_all_task_files(self, tmp_path):
        content = _generate_claude_md("fastapi", "gtd-lite", tmp_path)
        assert "tasks/inbox.md" in content
        assert "tasks/todo.md" in content
        assert "tasks/someday.md" in content

    def test_references_all_commands(self, tmp_path):
        content = _generate_claude_md("fastapi", "gtd-lite", tmp_path)
        assert "/gtd-capture" in content
        assert "/gtd-process" in content
        assert "/daily-plan" in content

    def test_mentions_getting_things_done(self, tmp_path):
        content = _generate_claude_md("fastapi", "gtd-lite", tmp_path)
        assert "Getting Things Done" in content


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


class TestSkipParameter:
    def test_skip_returns_empty(self, tmp_path):
        """skip=True returns empty list and does not create CLAUDE.md."""
        from cc_rig.generators.claude_md import generate_claude_md

        config = compute_defaults("fastapi", "standard", project_name="test-project")
        result = generate_claude_md(config, tmp_path, skip=True)
        assert result == []
        assert not (tmp_path / "CLAUDE.md").exists()

    def test_skip_does_not_overwrite_existing(self, tmp_path):
        """skip=True preserves an existing CLAUDE.md untouched."""
        from cc_rig.generators.claude_md import generate_claude_md

        (tmp_path / "CLAUDE.md").write_text("# My hand-crafted CLAUDE.md\n")
        config = compute_defaults("fastapi", "standard", project_name="test-project")
        result = generate_claude_md(config, tmp_path, skip=True)
        assert result == []
        assert (tmp_path / "CLAUDE.md").read_text() == "# My hand-crafted CLAUDE.md\n"


class TestHarnessGuardrails:
    """Harness level adds guardrail lines to CLAUDE.md."""

    def _make_with_harness(self, tmp_path, level):
        from cc_rig.config.project import HarnessConfig
        from cc_rig.generators.claude_md import generate_claude_md

        config = compute_defaults("fastapi", "standard", project_name="test")
        config.harness = HarnessConfig(level=level)
        generate_claude_md(config, tmp_path)
        return (tmp_path / "CLAUDE.md").read_text()

    def test_b0_no_harness_guardrails(self, tmp_path):
        content = self._make_with_harness(tmp_path, "none")
        assert "Budget-aware" not in content
        assert "gate-checked" not in content
        assert "Autonomy mode" not in content

    def test_b1_budget_guardrail(self, tmp_path):
        content = self._make_with_harness(tmp_path, "lite")
        assert "Budget-aware" in content
        assert "gate-checked" not in content

    def test_b2_gate_guardrail(self, tmp_path):
        content = self._make_with_harness(tmp_path, "standard")
        assert "Budget-aware" in content
        assert "gate-checked" in content
        assert "init-sh.sh" in content
        assert "Autonomy mode" not in content

    def test_b3_autonomy_guardrail(self, tmp_path):
        content = self._make_with_harness(tmp_path, "autonomy")
        assert "Budget-aware" in content
        assert "gate-checked" in content
        assert "Autonomy mode" in content
        assert "PROMPT.md" in content


class TestCacheGuardrails:
    """Cache guardrails are unconditional (present in all workflows)."""

    def test_cache_guardrails_in_standard(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        assert "Never edit CLAUDE.md during a session" in content
        assert "Never toggle hooks" in content
        assert "Never switch models mid-conversation" in content
        assert "Load memory via Read tool" in content

    def test_cache_guardrails_in_speedrun(self, tmp_path):
        content = _generate_claude_md("fastapi", "speedrun", tmp_path)
        assert "Never edit CLAUDE.md during a session" in content
        assert "Never toggle hooks" in content

    def test_cache_guardrails_in_superpowers(self, tmp_path):
        content = _generate_claude_md("fastapi", "superpowers", tmp_path)
        assert "Never edit CLAUDE.md during a session" in content

    def test_fork_session_in_spec_driven(self, tmp_path):
        content = _generate_claude_md("fastapi", "spec-driven", tmp_path)
        assert "fork-session" in content

    def test_fork_session_in_superpowers(self, tmp_path):
        content = _generate_claude_md("fastapi", "superpowers", tmp_path)
        assert "fork-session" in content

    def test_fork_session_in_aihero(self, tmp_path):
        content = _generate_claude_md("fastapi", "aihero", tmp_path)
        assert "fork-session" in content

    def test_no_fork_session_in_speedrun(self, tmp_path):
        content = _generate_claude_md("fastapi", "speedrun", tmp_path)
        assert "fork-session" not in content

    def test_no_fork_session_in_standard(self, tmp_path):
        content = _generate_claude_md("fastapi", "standard", tmp_path)
        assert "fork-session" not in content

    def test_no_fork_session_in_gtd(self, tmp_path):
        content = _generate_claude_md("fastapi", "gtd", tmp_path)
        assert "fork-session" not in content
