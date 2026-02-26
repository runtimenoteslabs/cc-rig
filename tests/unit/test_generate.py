"""Tests for post-generation next-steps output."""

from cc_rig.config.project import Features
from cc_rig.wizard.generate import run_generation
from tests.conftest import make_io, make_valid_config


def _run_and_capture(config, tmp_path):
    """Run generation and return captured output lines."""
    io = make_io([])
    run_generation(config, tmp_path, io)
    return io._output


class TestNextSteps:
    def test_next_steps_includes_git_commit(self, tmp_path):
        config = make_valid_config()
        lines = _run_and_capture(config, tmp_path)
        assert any("git add" in line and "git commit" in line for line in lines)

    def test_next_steps_includes_doctor(self, tmp_path):
        config = make_valid_config()
        lines = _run_and_capture(config, tmp_path)
        assert any("cc-rig doctor" in line for line in lines)

    def test_memory_note_shown_when_enabled(self, tmp_path):
        config = make_valid_config(features=Features(memory=True))
        lines = _run_and_capture(config, tmp_path)
        assert any("Memory files" in line or "memory/" in line for line in lines)

    def test_memory_note_hidden_when_disabled(self, tmp_path):
        config = make_valid_config(
            features=Features(memory=False),
            hooks=["format", "lint", "typecheck", "block-rm-rf", "block-env", "block-main",
                   "session-context", "stop-validator"],
            commands=["fix-issue", "review", "test", "plan", "learn", "assumptions", "refactor"],
        )
        lines = _run_and_capture(config, tmp_path)
        assert not any("Memory files" in line for line in lines)

    def test_team_sharing_shown(self, tmp_path):
        config = make_valid_config()
        lines = _run_and_capture(config, tmp_path)
        assert any("cc-rig init --config" in line for line in lines)
