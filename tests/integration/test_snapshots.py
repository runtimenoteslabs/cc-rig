"""Snapshot tests: verify generated output structure is stable.

These tests capture the file manifest and key content properties for
representative template × workflow combinations. If the generated output
changes, these tests will fail — update the snapshots deliberately.
"""

import json
from unittest.mock import patch

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.orchestrator import generate_all
from cc_rig.skills.downloader import SkillInstallReport


@pytest.fixture(autouse=True)
def _mock_skill_downloads():
    """Mock skill downloads to avoid network calls in snapshot tests."""
    report = SkillInstallReport()
    object.__setattr__(report, "_files", [])
    with patch("cc_rig.generators.skills.download_skills", return_value=report):
        yield


def _generate(template, workflow, output_dir):
    config = compute_defaults(template, workflow, project_name="snapshot-test")
    manifest = generate_all(config, output_dir)
    return config, manifest


# ── Representative combos for snapshot testing ────────────────────


_SNAPSHOT_COMBOS = [
    ("fastapi", "standard"),
    ("fastapi", "speedrun"),
    ("nextjs", "spec-driven"),
    ("gin", "gtd-lite"),
    ("django", "verify-heavy"),
]


class TestFileManifestSnapshot:
    """Verify the exact file list is stable for each combo."""

    @pytest.mark.parametrize("template,workflow", _SNAPSHOT_COMBOS)
    def test_manifest_is_deterministic(self, template, workflow, tmp_path):
        """Two identical runs produce the same file list."""
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"
        _, m1 = _generate(template, workflow, out1)
        _, m2 = _generate(template, workflow, out2)
        assert sorted(m1["files"]) == sorted(m2["files"])

    def test_fastapi_standard_expected_files(self, tmp_path):
        """Snapshot: fastapi + standard must produce these files."""
        output = tmp_path / "out"
        _, manifest = _generate("fastapi", "standard", output)
        files = set(manifest["files"])
        # Core files must always exist
        assert "CLAUDE.md" in files
        assert ".cc-rig.json" in files
        assert ".claude/settings.json" in files
        assert ".mcp.json" in files
        # Agent docs
        assert "agent_docs/architecture.md" in files
        assert "agent_docs/conventions.md" in files
        assert "agent_docs/testing.md" in files
        assert "agent_docs/deployment.md" in files
        assert "agent_docs/cache-friendly-workflow.md" in files
        # Memory files (standard enables memory)
        assert "memory/decisions.md" in files
        assert "memory/patterns.md" in files
        assert "memory/session-log.md" in files
        assert "memory/gotchas.md" in files
        assert "memory/people.md" in files
        assert "memory/MEMORY-README.md" in files

    def test_fastapi_speedrun_minimal_files(self, tmp_path):
        """Snapshot: speedrun should produce fewer files (no memory)."""
        output = tmp_path / "out"
        config, manifest = _generate("fastapi", "speedrun", output)
        files = set(manifest["files"])
        assert "CLAUDE.md" in files
        assert ".cc-rig.json" in files
        assert ".claude/settings.json" in files
        # No memory files
        for f in files:
            assert not f.startswith("memory/"), f"Unexpected memory file: {f}"

    def test_nextjs_spec_driven_has_spec_template(self, tmp_path):
        """Snapshot: spec-driven should include specs/TEMPLATE.md."""
        output = tmp_path / "out"
        _, manifest = _generate("nextjs", "spec-driven", output)
        files = set(manifest["files"])
        assert "specs/TEMPLATE.md" in files

    def test_gin_gtd_lite_has_task_files(self, tmp_path):
        """Snapshot: gtd-lite should include tasks/ files."""
        output = tmp_path / "out"
        _, manifest = _generate("gin", "gtd-lite", output)
        files = set(manifest["files"])
        assert "tasks/inbox.md" in files
        assert "tasks/todo.md" in files
        assert "tasks/someday.md" in files


class TestSkillsSnapshot:
    """Verify skill file properties are stable across combos."""

    def test_project_patterns_always_present(self, tmp_path):
        """project-patterns stub is always generated."""
        for template, workflow in _SNAPSHOT_COMBOS:
            output = tmp_path / f"{template}-{workflow}"
            _, manifest = _generate(template, workflow, output)
            files = set(manifest["files"])
            assert ".claude/skills/project-patterns/SKILL.md" in files, (
                f"{template}+{workflow}: missing project-patterns"
            )

    def test_speedrun_has_bundled_tdd_and_debug(self, tmp_path):
        """Speedrun always generates bundled tdd + debug fallbacks."""
        output = tmp_path / "out"
        _, manifest = _generate("fastapi", "speedrun", output)
        files = set(manifest["files"])
        assert ".claude/skills/tdd/SKILL.md" in files
        assert ".claude/skills/systematic-debug/SKILL.md" in files

    def test_standard_no_bundled_tdd_debug(self, tmp_path):
        """Standard with mocked downloads: no tdd/debug fallbacks (not in resolved set)."""
        output = tmp_path / "out"
        _, manifest = _generate("fastapi", "standard", output)
        files = set(manifest["files"])
        assert ".claude/skills/tdd/SKILL.md" not in files
        assert ".claude/skills/systematic-debug/SKILL.md" not in files

    def test_no_deployment_checklist(self, tmp_path):
        """deployment-checklist stub was killed — never generated."""
        for template, workflow in _SNAPSHOT_COMBOS:
            output = tmp_path / f"{template}-{workflow}"
            _, manifest = _generate(template, workflow, output)
            files = set(manifest["files"])
            assert ".claude/skills/deployment-checklist/SKILL.md" not in files

    def test_no_recommended_skills_doc(self, tmp_path):
        """recommended-skills.md is no longer generated."""
        for template, workflow in _SNAPSHOT_COMBOS:
            output = tmp_path / f"{template}-{workflow}"
            _, manifest = _generate(template, workflow, output)
            files = set(manifest["files"])
            assert "docs/recommended-skills.md" not in files

    def test_claude_md_has_installed_skills_section(self, tmp_path):
        """CLAUDE.md includes the Installed Skills section (non-speedrun)."""
        output = tmp_path / "out"
        _generate("fastapi", "standard", output)
        content = (output / "CLAUDE.md").read_text()
        assert "## Installed Skills" in content

    def test_speedrun_no_installed_skills_section(self, tmp_path):
        """Generic + speedrun has no skills, so no Installed Skills section."""
        output = tmp_path / "out"
        _generate("generic", "speedrun", output)
        content = (output / "CLAUDE.md").read_text()
        # generic + speedrun resolves 0 skills -> section omitted
        assert "## Installed Skills" not in content


class TestSettingsSnapshot:
    """Verify settings.json structure is stable."""

    def test_fastapi_standard_hook_events(self, tmp_path):
        """Snapshot: standard workflow hook events."""
        output = tmp_path / "out"
        _generate("fastapi", "standard", output)
        settings = json.loads((output / ".claude" / "settings.json").read_text())
        hooks = settings.get("hooks", {})
        # Standard has hooks keyed by event type
        assert "PostToolUse" in hooks  # format hook
        assert "PreToolUse" in hooks  # lint, block-* hooks
        assert "permissions" in settings

    def test_speedrun_has_fewer_hooks(self, tmp_path):
        """Snapshot: speedrun should have fewer hook events."""
        output = tmp_path / "out"
        _generate("fastapi", "speedrun", output)
        settings = json.loads((output / ".claude" / "settings.json").read_text())
        hooks = settings.get("hooks", {})
        # Speedrun has fewer hooks than standard
        speedrun_events = set(hooks.keys())

        out2 = tmp_path / "out2"
        _generate("fastapi", "standard", out2)
        settings2 = json.loads((out2 / ".claude" / "settings.json").read_text())
        standard_events = set(settings2.get("hooks", {}).keys())

        assert len(speedrun_events) <= len(standard_events)

    def test_verify_heavy_has_most_hooks(self, tmp_path):
        """Snapshot: verify-heavy should have the most hooks."""
        output = tmp_path / "out"
        _generate("django", "verify-heavy", output)
        settings = json.loads((output / ".claude" / "settings.json").read_text())
        hooks = settings.get("hooks", {})
        # Count total hook entries across all events
        total = sum(len(matchers) for matchers in hooks.values())
        # verify-heavy has 14 hooks
        assert total >= 10

    def test_hook_types_are_valid(self, tmp_path):
        """All hook types must be command, prompt, or agent."""
        output = tmp_path / "out"
        _generate("fastapi", "standard", output)
        settings = json.loads((output / ".claude" / "settings.json").read_text())
        for _event, matchers in settings.get("hooks", {}).items():
            for matcher in matchers:
                for hook in matcher.get("hooks", []):
                    assert hook["type"] in ("command", "prompt", "agent"), (
                        f"Invalid hook type: {hook['type']}"
                    )

    def test_agent_type_hook_exists(self, tmp_path):
        """At least one combo uses agent-type hooks (subagent-review)."""
        output = tmp_path / "out"
        # verify-heavy has subagent-review which is agent type
        _generate("django", "verify-heavy", output)
        settings = json.loads((output / ".claude" / "settings.json").read_text())
        found_agent = False
        for _event, matchers in settings.get("hooks", {}).items():
            for matcher in matchers:
                for hook in matcher.get("hooks", []):
                    if hook["type"] == "agent":
                        found_agent = True
        assert found_agent, "No agent-type hooks found"


class TestCLAUDEmdSnapshot:
    """Verify CLAUDE.md content properties are stable."""

    def test_contains_project_name(self, tmp_path):
        output = tmp_path / "out"
        _generate("fastapi", "standard", output)
        content = (output / "CLAUDE.md").read_text()
        assert "snapshot-test" in content

    def test_contains_framework_rules(self, tmp_path):
        output = tmp_path / "out"
        _generate("fastapi", "standard", output)
        content = (output / "CLAUDE.md").read_text()
        assert "fastapi" in content.lower() or "FastAPI" in content

    def test_static_before_dynamic(self, tmp_path):
        """Cache-aware: static sections should come before dynamic."""
        output = tmp_path / "out"
        _generate("fastapi", "standard", output)
        content = (output / "CLAUDE.md").read_text()
        # The project identity section should come before memory pointers
        # This is the cache-aware ordering principle
        lines = content.split("\n")
        project_line = None
        memory_line = None
        for i, line in enumerate(lines):
            if "project" in line.lower() and project_line is None:
                project_line = i
            if "memory" in line.lower() and memory_line is None:
                memory_line = i
        if project_line is not None and memory_line is not None:
            assert project_line < memory_line, (
                "Static content should come before dynamic (memory) content"
            )

    _LINE_CAPS = {
        "speedrun": 86,
        "standard": 125,
        "spec-driven": 163,
        "gtd-lite": 164,
        "gtd": 164,
        "verify-heavy": 174,
        "superpowers": 174,
        "gstack": 153,
        "aihero": 166,
    }

    @pytest.mark.parametrize("template,workflow", _SNAPSHOT_COMBOS)
    def test_line_count_within_target(self, template, workflow, tmp_path):
        """CLAUDE.md must stay under per-workflow line cap (cache-aware)."""
        output = tmp_path / "out"
        _generate(template, workflow, output)
        content = (output / "CLAUDE.md").read_text()
        line_count = content.count("\n") + 1
        cap = self._LINE_CAPS[workflow]
        assert line_count <= cap, f"{template}+{workflow}: {line_count} lines > {cap}"


class TestConfigSnapshot:
    """Verify .cc-rig.json content is stable."""

    def test_config_roundtrip(self, tmp_path):
        """Config saved during generation can be loaded back."""
        output = tmp_path / "out"
        config, _ = _generate("fastapi", "standard", output)
        data = json.loads((output / ".cc-rig.json").read_text())
        assert data["framework"] == "fastapi"
        assert data["workflow"] == "standard"
        assert data["project_name"] == "snapshot-test"

    def test_config_has_all_fields(self, tmp_path):
        """Config must include key fields."""
        output = tmp_path / "out"
        _generate("fastapi", "standard", output)
        data = json.loads((output / ".cc-rig.json").read_text())
        required = [
            "project_name",
            "language",
            "framework",
            "workflow",
            "agents",
            "commands",
            "hooks",
            "features",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"
