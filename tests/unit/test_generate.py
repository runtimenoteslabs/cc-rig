"""Tests for post-generation next-steps output."""

import os

from cc_rig.config.project import Features
from cc_rig.ui.display import strip_ansi
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
            hooks=[
                "format",
                "lint",
                "typecheck",
                "block-rm-rf",
                "block-env",
                "block-main",
                "session-context",
                "stop-validator",
            ],
            commands=["fix-issue", "review", "test", "plan", "learn", "assumptions", "refactor"],
        )
        lines = _run_and_capture(config, tmp_path)
        assert not any("Memory files" in line for line in lines)

    def test_team_sharing_shown(self, tmp_path):
        config = make_valid_config()
        lines = _run_and_capture(config, tmp_path)
        assert any("cc-rig init --config" in line for line in lines)

    def test_log_saved_message_shown(self, tmp_path):
        config = make_valid_config()
        lines = _run_and_capture(config, tmp_path)
        assert any("Log saved:" in line for line in lines)


class TestGenerationLog:
    def test_generation_log_saved(self, tmp_path):
        config = make_valid_config()
        io = make_io([])
        run_generation(config, tmp_path, io)
        log_file = tmp_path / ".claude" / "cc-rig-init.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "files generated" in content
        assert "All checks passed" in content

    def test_generation_log_has_no_ansi(self, tmp_path):
        config = make_valid_config()
        io = make_io([])
        run_generation(config, tmp_path, io)
        log_file = tmp_path / ".claude" / "cc-rig-init.log"
        content = log_file.read_text()
        assert "\033[" not in content

    def test_generation_log_symlink_created(self, tmp_path):
        config = make_valid_config()
        io = make_io([])
        run_generation(config, tmp_path, io)
        symlink = tmp_path / "cc-rig-init.log"
        assert symlink.is_symlink()
        assert os.readlink(str(symlink)) == os.path.join(".claude", "cc-rig-init.log")
        # Symlink resolves to actual file
        assert symlink.resolve() == (tmp_path / ".claude" / "cc-rig-init.log").resolve()


class TestStripAnsi:
    def test_strips_color_codes(self):
        assert strip_ansi("\033[32mgreen\033[0m") == "green"

    def test_strips_bold(self):
        assert strip_ansi("\033[1mbold\033[0m") == "bold"

    def test_strips_multiple_codes(self):
        text = "\033[1m\033[32mBold Green\033[0m normal \033[31mred\033[0m"
        assert strip_ansi(text) == "Bold Green normal red"

    def test_passthrough_plain_text(self):
        assert strip_ansi("no ansi here") == "no ansi here"

    def test_strips_dim(self):
        assert strip_ansi("\033[2mdim\033[0m") == "dim"
