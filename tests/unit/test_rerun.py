"""Tests for re-init warning and orphan file cleanup."""

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from cc_rig.clean import CleanResult, _remove_empty_dirs, cleanup_files, load_manifest
from cc_rig.generators.fileops import _BACKUP_DIR
from cc_rig.skills.downloader import SkillInstallReport
from cc_rig.ui.prompts import IO
from cc_rig.wizard.generate import run_generation
from tests.conftest import generate_project, make_io


@pytest.fixture(autouse=True)
def _mock_skill_downloads():
    """Mock skill downloads to avoid network calls and ensure deterministic manifests."""
    report = SkillInstallReport()
    object.__setattr__(report, "_files", [])
    with patch("cc_rig.generators.skills.download_skills", return_value=report):
        yield


def _make_io_with_prompts(inputs: list[str]) -> IO:
    """Like make_io but also captures input prompts."""
    it = iter(inputs)
    output: list[str] = []
    prompts: list[str] = []

    def _input_fn(prompt: str) -> str:
        prompts.append(prompt)
        return next(it)

    io = IO(
        input_fn=_input_fn,
        print_fn=lambda *args: output.append(str(args[0]) if args else ""),
    )
    io._output = output
    io._prompts = prompts
    return io


def _generate(tmp_path, workflow="standard"):
    """Generate a project and return (config, manifest)."""
    return generate_project(tmp_path, workflow=workflow)


# ── Pre-flight confirmation ──────────────────────────────────────


class TestReInitConfirmation:
    def test_fresh_directory_no_prompt(self, tmp_path):
        """First run in an empty directory should not show a confirmation prompt."""
        config, _ = generate_project(tmp_path, workflow="standard")
        # Now run_generation on a *different* empty directory — no prompt expected.
        fresh = tmp_path / "fresh"
        fresh.mkdir()
        io = make_io(inputs=[])  # no inputs needed — no prompt should fire
        exit_code = run_generation(config, fresh, io)
        assert exit_code == 0
        # No "Overwrite?" in output
        output = "\n".join(io._output)
        assert "Overwrite?" not in output

    def test_rerun_shows_prompt(self, tmp_path):
        """Re-running init shows a confirmation prompt with old config info."""
        config, _ = _generate(tmp_path, workflow="standard")
        # Re-run — two prompts: manifest overwrite (default=True, "" → yes)
        # and CLAUDE.md overwrite ("y" → yes)
        io = _make_io_with_prompts(inputs=["", "y"])
        exit_code = run_generation(config, tmp_path, io)
        assert exit_code == 0
        # confirm() passes the prompt through io.ask(), captured in _prompts
        prompt_text = "\n".join(io._prompts)
        assert "Existing cc-rig configuration found" in prompt_text
        assert "standard" in prompt_text

    def test_rerun_declined_aborts(self, tmp_path):
        """Declining the confirmation prompt aborts without changes."""
        config, manifest = _generate(tmp_path, workflow="standard")
        old_files = set(manifest["files"])

        # Decline with "n"
        io = make_io(inputs=["n"])
        exit_code = run_generation(config, tmp_path, io)
        assert exit_code == 0
        output = "\n".join(io._output)
        assert "Cancelled." in output
        # Files should still be the same
        new_manifest = load_manifest(tmp_path)
        assert set(new_manifest["files"]) == old_files


# ── Orphan cleanup ───────────────────────────────────────────────


class TestOrphanCleanup:
    def test_orphans_removed_on_workflow_switch(self, tmp_path):
        """Switching workflows removes orphaned files from the old config."""
        config_std, manifest_std = _generate(tmp_path, workflow="standard")
        std_files = set(manifest_std["files"])

        # Switch to speedrun (fewer files)
        from cc_rig.config.defaults import compute_defaults

        config_sr = compute_defaults("fastapi", "speedrun", project_name="test-proj")
        io = make_io(inputs=["", "y"])  # confirm manifest overwrite + CLAUDE.md overwrite
        exit_code = run_generation(config_sr, tmp_path, io)
        assert exit_code == 0

        new_manifest = load_manifest(tmp_path)
        new_files = set(new_manifest["files"])
        orphans = std_files - new_files

        # Orphans should exist in old but not in new
        assert len(orphans) > 0
        # Orphaned files should be removed from disk
        for orphan in orphans:
            assert not (tmp_path / orphan).exists(), f"Orphan {orphan} still on disk"

        # Output should mention cleanup
        output = "\n".join(io._output)
        assert "orphaned file(s)" in output

    def test_no_orphan_cleanup_same_config(self, tmp_path):
        """Re-running with same config produces no orphans."""
        config, _ = _generate(tmp_path, workflow="standard")

        io = make_io(inputs=["", "y"])  # confirm manifest overwrite + CLAUDE.md overwrite
        exit_code = run_generation(config, tmp_path, io)
        assert exit_code == 0

        # No orphan message in output
        output = "\n".join(io._output)
        assert "orphaned file(s)" not in output

    def test_user_modified_preserve_on_clean_survives(self, tmp_path):
        """User-modified preserve_on_clean files survive orphan cleanup."""
        _generate(tmp_path, workflow="standard")

        # Modify a memory file (preserve_on_clean=True)
        decisions = tmp_path / "memory" / "decisions.md"
        if decisions.exists():
            decisions.write_text("# Decisions\n\nMy real decision.\n")

        # Switch to speedrun (no memory files)
        from cc_rig.config.defaults import compute_defaults

        config_sr = compute_defaults("fastapi", "speedrun", project_name="test-proj")
        io = make_io(inputs=["", "y"])  # confirm manifest overwrite + CLAUDE.md overwrite
        run_generation(config_sr, tmp_path, io)

        new_manifest = load_manifest(tmp_path)
        new_files = set(new_manifest["files"])

        # If memory/decisions.md is not in the new manifest, it's an orphan
        if "memory/decisions.md" not in new_files:
            assert decisions.exists(), "User-modified memory file was deleted"
            assert "My real decision." in decisions.read_text()

    def test_empty_dirs_cleaned_after_orphan_removal(self, tmp_path):
        """Empty managed directories are cleaned up after orphan removal."""
        _generate(tmp_path, workflow="standard")
        assert (tmp_path / "memory").exists()

        # Switch to speedrun (no memory)
        from cc_rig.config.defaults import compute_defaults

        config_sr = compute_defaults("fastapi", "speedrun", project_name="test-proj")
        io = make_io(inputs=["", "y"])  # confirm manifest overwrite + CLAUDE.md overwrite
        run_generation(config_sr, tmp_path, io)

        new_manifest = load_manifest(tmp_path)
        new_files = set(new_manifest["files"])
        # If no memory files in the new manifest, directory should be gone
        has_memory = any(f.startswith("memory/") for f in new_files)
        if not has_memory:
            # Check that the memory dir was cleaned up (empty) or doesn't exist
            mem_dir = tmp_path / "memory"
            if mem_dir.exists():
                # Should only contain user-modified files
                remaining = list(mem_dir.rglob("*"))
                assert all(f.is_dir() or "My real" in f.read_text() for f in remaining)


# ── cleanup_files() unit tests ───────────────────────────────────


class TestCleanupFiles:
    def test_path_traversal_guard(self, tmp_path):
        """Files with path traversal are silently skipped."""
        # Create a file outside the project
        (tmp_path / "legit.txt").write_text("ok")
        result = cleanup_files(
            tmp_path,
            ["../../etc/passwd", "legit.txt"],
            {},
        )
        assert "legit.txt" in result.removed
        assert len(result.removed) == 1

    def test_restore_from_backup(self, tmp_path):
        """Pre-existing files with backups are restored (.bak format)."""
        # Set up file and backup with .bak extension
        (tmp_path / "file.txt").write_text("generated content")
        backup_dir = tmp_path / _BACKUP_DIR
        backup_dir.mkdir()
        (backup_dir / "file.txt.bak").write_text("original content")

        result = cleanup_files(
            tmp_path,
            ["file.txt"],
            {"file.txt": {"pre_existed": True, "backed_up": True}},
        )
        assert "file.txt" in result.restored
        assert (tmp_path / "file.txt").read_text() == "original content"

    def test_restore_from_legacy_backup(self, tmp_path):
        """Pre-existing files with legacy backups (no .bak) are restored."""
        (tmp_path / "file.txt").write_text("generated content")
        backup_dir = tmp_path / _BACKUP_DIR
        backup_dir.mkdir()
        (backup_dir / "file.txt").write_text("original content")

        result = cleanup_files(
            tmp_path,
            ["file.txt"],
            {"file.txt": {"pre_existed": True, "backed_up": True}},
        )
        assert "file.txt" in result.restored
        assert (tmp_path / "file.txt").read_text() == "original content"

    def test_skip_preexisting_no_backup(self, tmp_path):
        """Pre-existing files without backups are skipped."""
        (tmp_path / "file.txt").write_text("still here")
        result = cleanup_files(
            tmp_path,
            ["file.txt"],
            {"file.txt": {"pre_existed": True, "backed_up": False}},
        )
        assert "file.txt" in result.skipped_preexisting
        assert (tmp_path / "file.txt").exists()

    def test_skip_user_modified(self, tmp_path):
        """User-modified preserve_on_clean files are skipped."""
        original = "original content"
        h = hashlib.sha256(original.encode()).hexdigest()
        (tmp_path / "file.txt").write_text("user edited this")
        result = cleanup_files(
            tmp_path,
            ["file.txt"],
            {"file.txt": {"preserve_on_clean": True, "content_hash": h}},
        )
        assert "file.txt" in result.skipped_user_modified
        assert (tmp_path / "file.txt").exists()

    def test_delete_unmodified_preserve_on_clean(self, tmp_path):
        """Unmodified preserve_on_clean files are deleted."""
        content = "original content"
        h = hashlib.sha256(content.encode()).hexdigest()
        (tmp_path / "file.txt").write_text(content)
        result = cleanup_files(
            tmp_path,
            ["file.txt"],
            {"file.txt": {"preserve_on_clean": True, "content_hash": h}},
        )
        assert "file.txt" in result.removed
        assert not (tmp_path / "file.txt").exists()

    def test_missing_file(self, tmp_path):
        """Non-existent files are tracked as already_missing."""
        result = cleanup_files(tmp_path, ["nope.txt"], {})
        assert "nope.txt" in result.already_missing

    def test_empty_file_list(self, tmp_path):
        """Empty file list returns empty result."""
        result = cleanup_files(tmp_path, [], {})
        assert result.total_removed == 0
        assert result.restored == []


class TestRemoveEmptyDirs:
    def test_removes_empty_managed_dir(self, tmp_path):
        """Empty managed directories are removed."""
        (tmp_path / "memory").mkdir()
        result = CleanResult()
        _remove_empty_dirs(tmp_path, result)
        assert not (tmp_path / "memory").exists()
        assert "memory" in result.dirs_removed

    def test_keeps_nonempty_managed_dir(self, tmp_path):
        """Managed directories with files are kept."""
        (tmp_path / "memory").mkdir()
        (tmp_path / "memory" / "keep.md").write_text("keep")
        result = CleanResult()
        _remove_empty_dirs(tmp_path, result)
        assert (tmp_path / "memory").exists()


# ── Output directory propagation ──────────────────────────────────


class TestOutputDirPropagation:
    def test_compute_config_uses_state_output_dir(self, tmp_path):
        """_compute_config reads output_dir from state."""
        from cc_rig.ui.textual_wizard import WizardApp

        app = WizardApp(initial_state={"output_dir": str(tmp_path)})
        state = {
            "template": "fastapi",
            "workflow": "standard",
            "name": "test-proj",
            "output_dir": str(tmp_path),
        }
        state = app._compute_config(state)
        assert state["config"].output_dir == str(tmp_path)

    def test_compute_config_default_output_dir(self):
        """_compute_config falls back to '.' when output_dir absent."""
        from cc_rig.ui.textual_wizard import WizardApp

        app = WizardApp()
        state = {
            "template": "fastapi",
            "workflow": "standard",
            "name": "test-proj",
        }
        state = app._compute_config(state)
        assert state["config"].output_dir == "."

    def test_guided_flow_textual_uses_state_output_dir(self, tmp_path):
        """_guided_flow_textual passes state's output_dir to run_generation."""
        from cc_rig.config.defaults import compute_defaults
        from cc_rig.wizard.flow import _guided_flow_textual

        custom_dir = tmp_path / "custom-output"
        custom_dir.mkdir()

        config = compute_defaults(
            "fastapi",
            "standard",
            project_name="test-proj",
            output_dir=str(custom_dir),
        )
        tui_state = {
            "config": config,
            "output_dir": custom_dir,
            "launcher_mode": "fresh",
        }

        io = make_io(inputs=[])
        with (
            patch("cc_rig.ui.textual_wizard.WizardApp") as mock_app_cls,
            patch("cc_rig.wizard.flow.run_generation", return_value=0) as mock_gen,
        ):
            mock_app_cls.return_value.run.return_value = tui_state
            _guided_flow_textual("test-proj", Path("."), io)
            # run_generation should receive the custom dir, not the original "."
            actual_dir = mock_gen.call_args[0][1]
            assert actual_dir == custom_dir

    def test_quick_flow_textual_uses_state_output_dir(self, tmp_path):
        """_quick_flow_textual passes state's output_dir to run_generation."""
        from cc_rig.config.defaults import compute_defaults
        from cc_rig.wizard.flow import _quick_flow_textual

        custom_dir = tmp_path / "quick-output"
        custom_dir.mkdir()

        config = compute_defaults(
            "fastapi",
            "standard",
            project_name="test-proj",
            output_dir=str(custom_dir),
        )
        tui_state = {
            "config": config,
            "output_dir": custom_dir,
        }

        io = make_io(inputs=[])
        with (
            patch("cc_rig.ui.textual_wizard.QuickWizardApp") as mock_app_cls,
            patch("cc_rig.wizard.flow.run_generation", return_value=0) as mock_gen,
        ):
            mock_app_cls.return_value.run.return_value = tui_state
            _quick_flow_textual("test-proj", Path("."), io)
            actual_dir = mock_gen.call_args[0][1]
            assert actual_dir == custom_dir

    def test_guided_flow_textual_falls_back_to_original(self, tmp_path):
        """When state has no output_dir, original parameter is used."""
        from cc_rig.config.defaults import compute_defaults
        from cc_rig.wizard.flow import _guided_flow_textual

        config = compute_defaults(
            "fastapi",
            "standard",
            project_name="test-proj",
            output_dir=str(tmp_path),
        )
        tui_state = {
            "config": config,
            "launcher_mode": "fresh",
            # no output_dir in state
        }

        io = make_io(inputs=[])
        with (
            patch("cc_rig.ui.textual_wizard.WizardApp") as mock_app_cls,
            patch("cc_rig.wizard.flow.run_generation", return_value=0) as mock_gen,
        ):
            mock_app_cls.return_value.run.return_value = tui_state
            _guided_flow_textual("test-proj", tmp_path, io)
            actual_dir = mock_gen.call_args[0][1]
            assert actual_dir == tmp_path
