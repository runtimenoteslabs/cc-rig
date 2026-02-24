"""Tests for harness generation: B0-B3 runtime discipline levels."""

import json

from cc_rig.config.defaults import compute_defaults
from cc_rig.config.project import HarnessConfig, ProjectConfig
from cc_rig.generators.harness import generate_harness
from cc_rig.generators.orchestrator import generate_all


def _make_config(template="fastapi", workflow="standard", level="none"):
    """Create a config with a specific harness level."""
    config = compute_defaults(template, workflow, project_name="test-proj")
    config.harness = HarnessConfig(level=level)
    return config


class TestB0NoHarness:
    def test_no_files_generated(self, tmp_path):
        config = _make_config(level="none")
        files = generate_harness(config, tmp_path)
        assert files == []

    def test_default_config_is_b0(self, tmp_path):
        config = compute_defaults("fastapi", "standard", project_name="test")
        files = generate_harness(config, tmp_path)
        assert files == []


class TestB1Lite:
    def test_generates_task_list(self, tmp_path):
        config = _make_config(level="lite")
        files = generate_harness(config, tmp_path)
        assert "tasks/todo.md" in files
        assert (tmp_path / "tasks" / "todo.md").exists()

    def test_generates_budget_guide(self, tmp_path):
        config = _make_config(level="lite")
        files = generate_harness(config, tmp_path)
        assert "agent_docs/budget-guide.md" in files
        assert (tmp_path / "agent_docs" / "budget-guide.md").exists()

    def test_budget_guide_shows_unlimited(self, tmp_path):
        config = _make_config(level="lite")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "budget-guide.md").read_text()
        assert "unlimited" in content.lower()

    def test_budget_guide_shows_token_limit(self, tmp_path):
        config = _make_config(level="lite")
        config.harness.budget_per_run_tokens = 100_000
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "budget-guide.md").read_text()
        assert "100,000" in content

    def test_b1_file_count(self, tmp_path):
        config = _make_config(level="lite")
        files = generate_harness(config, tmp_path)
        assert len(files) == 2

    def test_no_verification_gates(self, tmp_path):
        config = _make_config(level="lite")
        generate_harness(config, tmp_path)
        assert not (tmp_path / "agent_docs" / "verification-gates.md").exists()

    def test_no_autonomy_doc(self, tmp_path):
        config = _make_config(level="lite")
        generate_harness(config, tmp_path)
        assert not (tmp_path / "agent_docs" / "autonomy-loop.md").exists()


class TestB2Standard:
    def test_includes_b1_files(self, tmp_path):
        config = _make_config(level="standard")
        files = generate_harness(config, tmp_path)
        assert "tasks/todo.md" in files
        assert "agent_docs/budget-guide.md" in files

    def test_generates_verification_gates(self, tmp_path):
        config = _make_config(level="standard")
        files = generate_harness(config, tmp_path)
        assert "agent_docs/verification-gates.md" in files
        assert (tmp_path / "agent_docs" / "verification-gates.md").exists()

    def test_generates_review_notes(self, tmp_path):
        config = _make_config(level="standard")
        files = generate_harness(config, tmp_path)
        assert "agent_docs/review-notes.md" in files
        assert (tmp_path / "agent_docs" / "review-notes.md").exists()

    def test_verification_shows_required(self, tmp_path):
        config = _make_config(level="standard")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "verification-gates.md").read_text()
        assert "REQUIRED" in content

    def test_verification_shows_optional(self, tmp_path):
        config = _make_config(level="standard")
        config.harness.require_tests_pass = False
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "verification-gates.md").read_text()
        assert "optional" in content

    def test_verification_includes_test_cmd(self, tmp_path):
        config = _make_config(level="standard")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "verification-gates.md").read_text()
        assert config.test_cmd in content

    def test_b2_file_count(self, tmp_path):
        config = _make_config(level="standard")
        files = generate_harness(config, tmp_path)
        assert len(files) == 4  # 2 from B1 + 2 from B2

    def test_no_autonomy_doc(self, tmp_path):
        config = _make_config(level="standard")
        generate_harness(config, tmp_path)
        assert not (tmp_path / "agent_docs" / "autonomy-loop.md").exists()


class TestB3Autonomy:
    def test_includes_b1_and_b2_files(self, tmp_path):
        config = _make_config(level="autonomy")
        files = generate_harness(config, tmp_path)
        assert "tasks/todo.md" in files
        assert "agent_docs/budget-guide.md" in files
        assert "agent_docs/verification-gates.md" in files
        assert "agent_docs/review-notes.md" in files

    def test_generates_autonomy_loop_doc(self, tmp_path):
        config = _make_config(level="autonomy")
        files = generate_harness(config, tmp_path)
        assert "agent_docs/autonomy-loop.md" in files
        assert (tmp_path / "agent_docs" / "autonomy-loop.md").exists()

    def test_autonomy_doc_has_warning(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "autonomy-loop.md").read_text()
        assert "WARNING" in content
        assert "AUTONOMOUS" in content

    def test_autonomy_doc_credits_ralph_wiggum(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "autonomy-loop.md").read_text()
        assert "Ralph Wiggum" in content
        assert "Geoffrey Huntley" in content
        assert "ghuntley/how-to-ralph-wiggum" in content

    def test_autonomy_doc_shows_max_iterations(self, tmp_path):
        config = _make_config(level="autonomy")
        config.harness.max_iterations = 50
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "autonomy-loop.md").read_text()
        assert "50" in content

    def test_autonomy_doc_shows_if_blocked_stop(self, tmp_path):
        config = _make_config(level="autonomy")
        config.harness.if_blocked = "stop"
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "autonomy-loop.md").read_text()
        assert "stop" in content.lower() or "Stop" in content

    def test_autonomy_doc_shows_if_blocked_skip(self, tmp_path):
        config = _make_config(level="autonomy")
        config.harness.if_blocked = "skip"
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "autonomy-loop.md").read_text()
        assert "skip" in content.lower() or "Skip" in content

    def test_generates_loop_sh(self, tmp_path):
        config = _make_config(level="autonomy")
        files = generate_harness(config, tmp_path)
        assert "loop.sh" in files
        loop_path = tmp_path / "loop.sh"
        assert loop_path.exists()
        content = loop_path.read_text()
        assert "#!/usr/bin/env bash" in content
        assert "Ralph Wiggum" in content
        assert "Geoffrey Huntley" in content
        assert "cat PROMPT.md | claude" in content
        assert "tasks/todo.md" in content

    def test_loop_sh_is_executable(self, tmp_path):
        import os
        import stat

        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        mode = os.stat(tmp_path / "loop.sh").st_mode
        assert mode & stat.S_IXUSR  # Owner execute bit set

    def test_loop_sh_uses_max_iterations(self, tmp_path):
        config = _make_config(level="autonomy")
        config.harness.max_iterations = 42
        generate_harness(config, tmp_path)
        content = (tmp_path / "loop.sh").read_text()
        assert "42" in content

    def test_generates_prompt_md(self, tmp_path):
        config = _make_config(level="autonomy")
        files = generate_harness(config, tmp_path)
        assert "PROMPT.md" in files
        prompt_path = tmp_path / "PROMPT.md"
        assert prompt_path.exists()
        content = prompt_path.read_text()
        assert "tasks/todo.md" in content
        assert "ONE task" in content
        assert "EXIT" in content

    def test_prompt_md_includes_verification_commands(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "PROMPT.md").read_text()
        assert config.test_cmd in content
        assert config.lint_cmd in content

    def test_prompt_md_if_blocked_stop(self, tmp_path):
        config = _make_config(level="autonomy")
        config.harness.if_blocked = "stop"
        generate_harness(config, tmp_path)
        content = (tmp_path / "PROMPT.md").read_text()
        assert "EXIT" in content

    def test_prompt_md_if_blocked_skip(self, tmp_path):
        config = _make_config(level="autonomy")
        config.harness.if_blocked = "skip"
        generate_harness(config, tmp_path)
        content = (tmp_path / "PROMPT.md").read_text()
        assert "skip" in content.lower()

    def test_generates_safety_config_json(self, tmp_path):
        config = _make_config(level="autonomy")
        files = generate_harness(config, tmp_path)
        assert ".claude/harness-config.json" in files
        path = tmp_path / ".claude" / "harness-config.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["harness_level"] == "autonomy"
        assert data["max_iterations"] == 20
        assert data["checkpoint_commits"] is True

    def test_safety_config_custom_values(self, tmp_path):
        config = _make_config(level="autonomy")
        config.harness.max_iterations = 10
        config.harness.checkpoint_commits = False
        config.harness.if_blocked = "skip"
        config.harness.budget_per_run_tokens = 50_000
        generate_harness(config, tmp_path)
        data = json.loads((tmp_path / ".claude" / "harness-config.json").read_text())
        assert data["max_iterations"] == 10
        assert data["checkpoint_commits"] is False
        assert data["if_blocked"] == "skip"
        assert data["budget"]["per_run_tokens"] == 50_000

    def test_b3_file_count(self, tmp_path):
        config = _make_config(level="autonomy")
        files = generate_harness(config, tmp_path)
        # 2 B1 + 2 B2 + 4 B3 (autonomy-loop.md, PROMPT.md, loop.sh, config.json)
        assert len(files) == 8


class TestHarnessConfig:
    def test_default_harness_is_none(self):
        h = HarnessConfig()
        assert h.level == "none"
        assert h.max_iterations == 20
        assert h.checkpoint_commits is True
        assert h.if_blocked == "stop"

    def test_harness_round_trip(self):
        h = HarnessConfig(
            level="autonomy",
            budget_per_run_tokens=100_000,
            max_iterations=30,
            if_blocked="skip",
        )
        d = h.to_dict()
        h2 = HarnessConfig.from_dict(d)
        assert h2.level == "autonomy"
        assert h2.budget_per_run_tokens == 100_000
        assert h2.max_iterations == 30
        assert h2.if_blocked == "skip"

    def test_harness_in_project_config(self):
        config = ProjectConfig(
            project_name="test",
            harness=HarnessConfig(level="lite"),
        )
        d = config.to_dict()
        assert d["harness"]["level"] == "lite"
        loaded = ProjectConfig.from_dict(d)
        assert loaded.harness.level == "lite"

    def test_harness_missing_from_dict(self):
        """Old configs without harness field should get defaults."""
        d = {"project_name": "old-project"}
        config = ProjectConfig.from_dict(d)
        assert config.harness.level == "none"


class TestHarnessCLI:
    def test_harness_init_lite(self, capsys, tmp_path):
        # Generate a project first
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_all(config, tmp_path)
        from cc_rig.cli import main

        rc = main(["harness", "init", "--lite", "-d", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "lite" in captured.out
        assert (tmp_path / "tasks" / "todo.md").exists()

    def test_harness_init_standard(self, capsys, tmp_path):
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_all(config, tmp_path)
        from cc_rig.cli import main

        rc = main(["harness", "init", "-d", str(tmp_path)])
        assert rc == 0
        assert (tmp_path / "agent_docs" / "verification-gates.md").exists()

    def test_harness_init_autonomy(self, capsys, tmp_path, monkeypatch):
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_all(config, tmp_path)
        from cc_rig.cli import main

        monkeypatch.setattr("builtins.input", lambda _: "I understand")
        rc = main(["harness", "init", "--autonomy", "-d", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert (tmp_path / "agent_docs" / "autonomy-loop.md").exists()

    def test_harness_init_autonomy_cancelled(self, capsys, tmp_path, monkeypatch):
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_all(config, tmp_path)
        from cc_rig.cli import main

        monkeypatch.setattr("builtins.input", lambda _: "no")
        rc = main(["harness", "init", "--autonomy", "-d", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Cancelled" in captured.out

    def test_harness_init_ralph_alias(self, capsys, tmp_path, monkeypatch):
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_all(config, tmp_path)
        from cc_rig.cli import main

        monkeypatch.setattr("builtins.input", lambda _: "I understand")
        rc = main(["harness", "init", "--ralph", "-d", str(tmp_path)])
        assert rc == 0
        assert (tmp_path / "agent_docs" / "autonomy-loop.md").exists()

    def test_harness_no_project(self, capsys, tmp_path):
        from cc_rig.cli import main

        rc = main(["harness", "init", "-d", str(tmp_path)])
        assert rc == 1

    def test_harness_updates_config(self, tmp_path):
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_all(config, tmp_path)
        from cc_rig.cli import main

        main(["harness", "init", "--lite", "-d", str(tmp_path)])
        data = json.loads((tmp_path / ".cc-rig.json").read_text())
        assert data["harness"]["level"] == "lite"

    def test_harness_updates_manifest(self, tmp_path):
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_all(config, tmp_path)
        from cc_rig.cli import main

        main(["harness", "init", "--lite", "-d", str(tmp_path)])
        manifest = json.loads((tmp_path / ".claude" / ".cc-rig-manifest.json").read_text())
        assert "tasks/todo.md" in manifest["files"]

    def test_harness_default_shows_help(self, capsys):
        from cc_rig.cli import main

        rc = main(["harness"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "harness" in captured.out.lower()
