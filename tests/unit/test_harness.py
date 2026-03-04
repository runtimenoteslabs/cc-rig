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

    def test_generates_harness_doc(self, tmp_path):
        config = _make_config(level="lite")
        files = generate_harness(config, tmp_path)
        assert "agent_docs/harness.md" in files
        assert (tmp_path / "agent_docs" / "harness.md").exists()

    def test_no_budget_guide(self, tmp_path):
        """budget-guide.md replaced by consolidated harness.md."""
        config = _make_config(level="lite")
        generate_harness(config, tmp_path)
        assert not (tmp_path / "agent_docs" / "budget-guide.md").exists()

    def test_harness_doc_shows_unlimited(self, tmp_path):
        config = _make_config(level="lite")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "unlimited" in content.lower()

    def test_harness_doc_shows_token_limit(self, tmp_path):
        config = _make_config(level="lite")
        config.harness.budget_per_run_tokens = 100_000
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "100,000" in content

    def test_b1_file_count(self, tmp_path):
        config = _make_config(level="lite")
        files = generate_harness(config, tmp_path)
        assert len(files) == 2  # tasks/todo.md + agent_docs/harness.md

    def test_no_init_sh(self, tmp_path):
        config = _make_config(level="lite")
        generate_harness(config, tmp_path)
        assert not (tmp_path / ".claude" / "hooks" / "init-sh.sh").exists()

    def test_no_autonomy_doc(self, tmp_path):
        config = _make_config(level="lite")
        generate_harness(config, tmp_path)
        assert not (tmp_path / "agent_docs" / "autonomy-loop.md").exists()


class TestB2Standard:
    def test_includes_b1_files(self, tmp_path):
        config = _make_config(level="standard")
        files = generate_harness(config, tmp_path)
        assert "tasks/todo.md" in files
        assert "agent_docs/harness.md" in files

    def test_no_verification_gates_file(self, tmp_path):
        """verification-gates.md replaced by gates section in harness.md."""
        config = _make_config(level="standard")
        generate_harness(config, tmp_path)
        assert not (tmp_path / "agent_docs" / "verification-gates.md").exists()

    def test_no_review_notes_file(self, tmp_path):
        """review-notes.md removed in v2."""
        config = _make_config(level="standard")
        generate_harness(config, tmp_path)
        assert not (tmp_path / "agent_docs" / "review-notes.md").exists()

    def test_harness_md_has_gates(self, tmp_path):
        config = _make_config(level="standard")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "Verification Gates" in content

    def test_harness_md_shows_required(self, tmp_path):
        config = _make_config(level="standard")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "REQUIRED" in content

    def test_harness_md_shows_optional(self, tmp_path):
        config = _make_config(level="standard")
        config.harness.require_tests_pass = False
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "optional" in content

    def test_harness_md_includes_test_cmd(self, tmp_path):
        config = _make_config(level="standard")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert config.test_cmd in content

    def test_harness_md_references_init_sh(self, tmp_path):
        config = _make_config(level="standard")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "init-sh.sh" in content

    def test_generates_init_sh(self, tmp_path):
        config = _make_config(level="standard")
        files = generate_harness(config, tmp_path)
        assert ".claude/hooks/init-sh.sh" in files
        assert (tmp_path / ".claude" / "hooks" / "init-sh.sh").exists()

    def test_b2_file_count(self, tmp_path):
        config = _make_config(level="standard")
        files = generate_harness(config, tmp_path)
        # 2 from B1 (todo.md + harness.md) + init-sh.sh = 3
        # B2 enhances harness.md in-place, no new files
        assert len(files) == 3

    def test_no_autonomy_doc(self, tmp_path):
        config = _make_config(level="standard")
        generate_harness(config, tmp_path)
        assert not (tmp_path / "agent_docs" / "autonomy-loop.md").exists()


class TestB3Autonomy:
    def test_includes_b1_and_b2_files(self, tmp_path):
        config = _make_config(level="autonomy")
        files = generate_harness(config, tmp_path)
        assert "tasks/todo.md" in files
        assert "agent_docs/harness.md" in files
        assert ".claude/hooks/init-sh.sh" in files

    def test_no_autonomy_loop_doc(self, tmp_path):
        """autonomy-loop.md replaced by section in harness.md."""
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        assert not (tmp_path / "agent_docs" / "autonomy-loop.md").exists()

    def test_harness_md_has_autonomy_section(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "Autonomy Loop" in content

    def test_harness_md_credits_ralph_wiggum(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "Ralph Wiggum" in content
        assert "Geoffrey Huntley" in content
        assert "ghuntley/how-to-ralph-wiggum" in content

    def test_harness_md_shows_max_iterations(self, tmp_path):
        config = _make_config(level="autonomy")
        config.harness.max_iterations = 50
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "50" in content

    def test_harness_md_shows_if_blocked_stop(self, tmp_path):
        config = _make_config(level="autonomy")
        config.harness.if_blocked = "stop"
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "Stop" in content

    def test_harness_md_shows_if_blocked_skip(self, tmp_path):
        config = _make_config(level="autonomy")
        config.harness.if_blocked = "skip"
        generate_harness(config, tmp_path)
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "Skip" in content

    def test_generates_progress_file(self, tmp_path):
        config = _make_config(level="autonomy")
        files = generate_harness(config, tmp_path)
        assert "claude-progress.txt" in files
        assert (tmp_path / "claude-progress.txt").exists()

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

    def test_loop_sh_reads_config(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "loop.sh").read_text()
        assert "harness-config.json" in content
        assert "max_iterations" in content

    def test_loop_sh_detects_stuck(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "loop.sh").read_text()
        assert "STUCK_COUNT" in content

    def test_loop_sh_runs_tidy(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "loop.sh").read_text()
        assert "init-sh.sh tidy" in content

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

    def test_prompt_md_5_step_workflow(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "PROMPT.md").read_text()
        assert "Assess" in content
        assert "Advance" in content
        assert "Tidy" in content
        assert "Verify" in content
        assert "Record" in content

    def test_prompt_md_references_init_sh(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "PROMPT.md").read_text()
        assert "init-sh.sh" in content

    def test_prompt_md_references_progress(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "PROMPT.md").read_text()
        assert "claude-progress.txt" in content

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
        # 2 B1 + init-sh.sh + 4 B3 (PROMPT.md, progress.txt, loop.sh, config.json)
        assert len(files) == 7

    def test_loop_sh_uses_output_format_json(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "loop.sh").read_text()
        assert "--output-format json" in content

    def test_loop_sh_has_budget_enforcement(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "loop.sh").read_text()
        assert "BUDGET EXCEEDED" in content

    def test_loop_sh_has_budget_tracking(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "loop.sh").read_text()
        assert "CUMULATIVE_COST_USD" in content

    def test_loop_sh_has_auto_checkpoint(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "loop.sh").read_text()
        assert "auto-commit" in content
        assert "git add -A" in content

    def test_loop_sh_has_cost_summary(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "loop.sh").read_text()
        assert "Cost Summary" in content

    def test_loop_sh_has_progress_logging(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "loop.sh").read_text()
        assert "tokens_in=" in content

    def test_loop_sh_has_cleanup_trap(self, tmp_path):
        config = _make_config(level="autonomy")
        generate_harness(config, tmp_path)
        content = (tmp_path / "loop.sh").read_text()
        assert "trap cleanup" in content

    def test_loop_sh_passes_bash_syntax(self, tmp_path):
        import subprocess

        config = _make_config(level="autonomy")
        config.harness.budget_per_run_tokens = 500000
        generate_harness(config, tmp_path)
        script = tmp_path / "loop.sh"
        result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error:\n{result.stderr}"


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
        assert (tmp_path / "agent_docs" / "harness.md").exists()
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "Verification Gates" in content

    def test_harness_init_autonomy(self, capsys, tmp_path, monkeypatch):
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_all(config, tmp_path)
        from cc_rig.cli import main

        monkeypatch.setattr("builtins.input", lambda _: "I understand")
        rc = main(["harness", "init", "--autonomy", "-d", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert (tmp_path / "PROMPT.md").exists()

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
        assert (tmp_path / "PROMPT.md").exists()

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


class TestFeatureIntegration:
    """Feature flags affect harness output (PROMPT.md, hooks)."""

    def test_prompt_md_memory_integration(self, tmp_path):
        config = _make_config(level="autonomy")
        config.features.memory = True
        generate_harness(config, tmp_path)
        content = (tmp_path / "PROMPT.md").read_text()
        assert "memory/session-log.md" in content
        assert "memory/" in content

    def test_prompt_md_no_memory_without_feature(self, tmp_path):
        config = _make_config(level="autonomy")
        config.features.memory = False
        generate_harness(config, tmp_path)
        content = (tmp_path / "PROMPT.md").read_text()
        assert "memory/session-log.md" not in content

    def test_prompt_md_spec_workflow_integration(self, tmp_path):
        config = _make_config(level="autonomy")
        config.features.spec_workflow = True
        generate_harness(config, tmp_path)
        content = (tmp_path / "PROMPT.md").read_text()
        assert "spec-create" in content

    def test_prompt_md_gtd_integration(self, tmp_path):
        config = _make_config(level="autonomy")
        config.features.gtd = True
        generate_harness(config, tmp_path)
        content = (tmp_path / "PROMPT.md").read_text()
        assert "inbox.md" in content

    def test_prompt_md_worktrees_integration(self, tmp_path):
        config = _make_config(level="autonomy")
        config.features.worktrees = True
        generate_harness(config, tmp_path)
        content = (tmp_path / "PROMPT.md").read_text()
        assert "worktree" in content.lower()

    def test_session_tasks_hook_gtd(self, tmp_path):
        """session-tasks hook includes inbox count when GTD enabled."""
        from cc_rig.generators.settings import _script_session_tasks

        config = _make_config(level="lite")
        config.features.gtd = True
        script = _script_session_tasks(config)
        assert "inbox.md" in script

    def test_session_tasks_hook_memory(self, tmp_path):
        """session-tasks hook includes memory line count when memory enabled."""
        from cc_rig.generators.settings import _script_session_tasks

        config = _make_config(level="lite")
        config.features.memory = True
        script = _script_session_tasks(config)
        assert "memory" in script

    def test_session_tasks_hook_no_extras_without_features(self, tmp_path):
        """session-tasks hook is minimal without features."""
        from cc_rig.generators.settings import _script_session_tasks

        config = _make_config(level="lite")
        config.features.memory = False
        config.features.gtd = False
        script = _script_session_tasks(config)
        assert "inbox.md" not in script
        assert "memory" not in script.lower()


class TestHarnessConfigFlags:
    """Test à la carte harness: level→flags derivation, round-trip, backward compat."""

    def test_none_sets_all_false(self):
        h = HarnessConfig(level="none")
        assert h.task_tracking is False
        assert h.budget_awareness is False
        assert h.verification_gates is False
        assert h.autonomy_loop is False

    def test_lite_sets_task_and_budget(self):
        h = HarnessConfig(level="lite")
        assert h.task_tracking is True
        assert h.budget_awareness is True
        assert h.verification_gates is False
        assert h.autonomy_loop is False

    def test_standard_sets_task_budget_gates(self):
        h = HarnessConfig(level="standard")
        assert h.task_tracking is True
        assert h.budget_awareness is True
        assert h.verification_gates is True
        assert h.autonomy_loop is False

    def test_autonomy_sets_all_true(self):
        h = HarnessConfig(level="autonomy")
        assert h.task_tracking is True
        assert h.budget_awareness is True
        assert h.verification_gates is True
        assert h.autonomy_loop is True

    def test_custom_preserves_individual_flags(self):
        h = HarnessConfig(
            level="custom",
            task_tracking=False,
            budget_awareness=True,
            verification_gates=False,
            autonomy_loop=False,
        )
        assert h.task_tracking is False
        assert h.budget_awareness is True
        assert h.verification_gates is False
        assert h.autonomy_loop is False

    def test_custom_autonomy_auto_enables_task_tracking(self):
        """autonomy_loop=True should auto-enable task_tracking."""
        h = HarnessConfig(
            level="custom",
            task_tracking=False,
            autonomy_loop=True,
        )
        assert h.task_tracking is True
        assert h.autonomy_loop is True

    def test_round_trip_with_flags(self):
        h = HarnessConfig(
            level="custom",
            task_tracking=True,
            budget_awareness=False,
            verification_gates=False,
            autonomy_loop=True,
        )
        d = h.to_dict()
        assert d["level"] == "custom"
        assert d["task_tracking"] is True
        assert d["budget_awareness"] is False
        assert d["autonomy_loop"] is True
        h2 = HarnessConfig.from_dict(d)
        assert h2.level == "custom"
        assert h2.task_tracking is True
        assert h2.budget_awareness is False
        assert h2.autonomy_loop is True

    def test_round_trip_standard_level(self):
        h = HarnessConfig(level="standard")
        d = h.to_dict()
        h2 = HarnessConfig.from_dict(d)
        assert h2.level == "standard"
        assert h2.task_tracking is True
        assert h2.verification_gates is True

    def test_old_config_without_flags_derives_from_level(self):
        """Old .cc-rig.json files without flag keys still work."""
        data = {"level": "standard", "max_iterations": 20}
        h = HarnessConfig.from_dict(data)
        assert h.level == "standard"
        assert h.task_tracking is True
        assert h.budget_awareness is True
        assert h.verification_gates is True
        assert h.autonomy_loop is False

    def test_old_config_lite_derives_correctly(self):
        data = {"level": "lite"}
        h = HarnessConfig.from_dict(data)
        assert h.task_tracking is True
        assert h.budget_awareness is True
        assert h.verification_gates is False

    def test_old_config_none_derives_all_false(self):
        data = {"level": "none"}
        h = HarnessConfig.from_dict(data)
        assert h.task_tracking is False
        assert h.budget_awareness is False


class TestCustomHarness:
    """Test à la carte harness generation: individual feature combos."""

    def _make_custom_config(self, **flags):
        config = compute_defaults("fastapi", "standard", project_name="test-proj")
        config.harness = HarnessConfig(level="custom", **flags)
        return config

    def test_autonomy_only(self, tmp_path):
        """autonomy_loop=True only → PROMPT.md + loop.sh + init-sh.sh + todo.md, no commit-gate."""
        config = self._make_custom_config(autonomy_loop=True)
        files = generate_harness(config, tmp_path)

        # Autonomy auto-enables task_tracking
        assert "tasks/todo.md" in files
        assert "agent_docs/harness.md" in files
        assert ".claude/hooks/init-sh.sh" in files
        assert "PROMPT.md" in files
        assert "loop.sh" in files
        assert "claude-progress.txt" in files
        assert ".claude/harness-config.json" in files

    def test_autonomy_only_no_commit_gate_hook(self, tmp_path):
        """Custom autonomy-only should NOT generate commit-gate hook."""
        from cc_rig.generators.settings import generate_settings

        config = self._make_custom_config(autonomy_loop=True)
        generate_settings(config, tmp_path)
        assert not (tmp_path / ".claude" / "hooks" / "commit-gate.sh").exists()

    def test_autonomy_only_has_session_tasks_hook(self, tmp_path):
        """Custom autonomy-only should have session-tasks (task_tracking auto-enabled)."""
        from cc_rig.generators.settings import generate_settings

        config = self._make_custom_config(autonomy_loop=True)
        generate_settings(config, tmp_path)
        assert (tmp_path / ".claude" / "hooks" / "session-tasks.sh").exists()

    def test_task_tracking_only(self, tmp_path):
        """task_tracking=True only → todo.md + harness.md, no init-sh.sh, no loop.sh."""
        config = self._make_custom_config(task_tracking=True)
        files = generate_harness(config, tmp_path)

        assert "tasks/todo.md" in files
        assert "agent_docs/harness.md" in files
        assert ".claude/hooks/init-sh.sh" not in files
        assert "PROMPT.md" not in files
        assert "loop.sh" not in files

    def test_gates_only(self, tmp_path):
        """verification_gates=True only → init-sh.sh + gate section, no task files."""
        config = self._make_custom_config(verification_gates=True)
        files = generate_harness(config, tmp_path)

        # Gates alone doesn't generate todo/harness base (no task_tracking/budget)
        assert "tasks/todo.md" not in files
        assert ".claude/hooks/init-sh.sh" in files

    def test_budget_only(self, tmp_path):
        """budget_awareness=True only → todo.md + harness.md with budget section."""
        config = self._make_custom_config(budget_awareness=True)
        files = generate_harness(config, tmp_path)

        assert "tasks/todo.md" in files
        assert "agent_docs/harness.md" in files
        assert "PROMPT.md" not in files

    def test_all_flags_false_no_files(self, tmp_path):
        """No flags → no harness files."""
        config = self._make_custom_config()
        files = generate_harness(config, tmp_path)
        assert files == []

    def test_gates_plus_task_tracking(self, tmp_path):
        """gates + task_tracking → full B2 equivalent."""
        config = self._make_custom_config(
            task_tracking=True,
            verification_gates=True,
        )
        files = generate_harness(config, tmp_path)

        assert "tasks/todo.md" in files
        assert "agent_docs/harness.md" in files
        assert ".claude/hooks/init-sh.sh" in files
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "Verification Gates" in content


class TestRalphLoopPlugin:
    """Ralph-loop plugin harness — no loop.sh, but B1/B2 features work."""

    def test_ralph_loop_no_loop_sh(self, tmp_path):
        """ralph_loop_plugin=True should not generate loop.sh or PROMPT.md."""
        config = _make_config()
        config.harness = HarnessConfig(
            level="ralph-loop",
            task_tracking=True,
            budget_awareness=True,
        )
        files = generate_harness(config, tmp_path)
        assert "loop.sh" not in files
        assert "PROMPT.md" not in files
        assert "claude-progress.txt" not in files
        assert ".claude/harness-config.json" not in files

    def test_ralph_loop_with_task_tracking(self, tmp_path):
        """ralph_loop_plugin with task_tracking generates B1 files."""
        config = _make_config()
        config.harness = HarnessConfig(
            level="ralph-loop",
            task_tracking=True,
            budget_awareness=True,
        )
        files = generate_harness(config, tmp_path)
        assert "tasks/todo.md" in files
        assert "agent_docs/harness.md" in files

    def test_ralph_loop_with_verification_gates(self, tmp_path):
        """ralph_loop_plugin with verification_gates generates init-sh.sh."""
        config = _make_config()
        config.harness = HarnessConfig(
            level="ralph-loop",
            task_tracking=True,
            verification_gates=True,
        )
        files = generate_harness(config, tmp_path)
        assert ".claude/hooks/init-sh.sh" in files

    def test_ralph_loop_no_features_no_files(self, tmp_path):
        """ralph_loop_plugin without any B1/B2 flags generates no files."""
        config = _make_config()
        config.harness = HarnessConfig(
            level="ralph-loop",
            task_tracking=False,
            budget_awareness=False,
            verification_gates=False,
        )
        files = generate_harness(config, tmp_path)
        assert files == []

    def test_ralph_loop_flag_serialization(self):
        """ralph_loop_plugin round-trips through to_dict/from_dict."""
        h = HarnessConfig(
            level="ralph-loop",
            task_tracking=True,
            budget_awareness=True,
        )
        d = h.to_dict()
        restored = HarnessConfig.from_dict(d)
        assert restored.ralph_loop_plugin is True
        assert restored.task_tracking is True
        assert restored.budget_awareness is True
        assert restored.autonomy_loop is False

    def test_ralph_loop_plus_autonomy_loop_invalid(self):
        """ralph_loop_plugin + autonomy_loop should fail validation."""
        from cc_rig.config.schema import validate_config

        config = _make_config()
        config.harness = HarnessConfig(
            level="custom",
            ralph_loop_plugin=True,
            autonomy_loop=True,
            task_tracking=True,
        )
        errors = validate_config(config)
        assert any("ralph_loop_plugin" in e for e in errors)
