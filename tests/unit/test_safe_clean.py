"""Tests for safe clean: restore pre-existing files, skip, backward compat."""

import json

from cc_rig.clean import CleanResult, load_manifest, run_clean
from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.fileops import _BACKUP_DIR
from cc_rig.generators.orchestrator import generate_all
from tests.conftest import generate_project as _generate_project


def _generate_with_features(tmp_path, workflow="standard"):
    """Generate a project with the given workflow (controls features)."""
    return _generate_project(tmp_path, workflow=workflow)


def _generate_with_gtd(tmp_path):
    """Generate a project with GTD features explicitly enabled."""
    config = compute_defaults("fastapi", "standard", project_name="test-proj")
    config.features.gtd = True
    config.features.worktrees = True
    config.commands = list(config.commands) + [
        "gtd-capture",
        "gtd-process",
        "daily-plan",
        "worktree",
    ]
    manifest = generate_all(config, tmp_path)
    return config, manifest


class TestSafeCleanRestorePreExisting:
    def test_pre_existing_file_restored(self, tmp_path):
        """If a file existed before generation, clean restores it from backup."""
        # Create a pre-existing CLAUDE.md
        (tmp_path / "CLAUDE.md").write_text("my original claude.md")

        # Generate project (overwrites CLAUDE.md)
        _generate_project(tmp_path)
        assert (tmp_path / "CLAUDE.md").exists()
        # Content should be overwritten by generator
        assert (tmp_path / "CLAUDE.md").read_text() != "my original claude.md"

        # Backup should exist (with .bak extension to avoid Claude Code discovery)
        backup = tmp_path / _BACKUP_DIR / "CLAUDE.md.bak"
        assert backup.exists()
        assert backup.read_text() == "my original claude.md"

        # Clean should restore, not delete
        result = run_clean(tmp_path, force=True)
        assert "CLAUDE.md" in result.restored
        assert "CLAUDE.md" not in result.removed
        assert (tmp_path / "CLAUDE.md").read_text() == "my original claude.md"

    def test_non_preexisting_files_deleted(self, tmp_path):
        """Files that didn't exist before are deleted normally."""
        _generate_project(tmp_path)
        result = run_clean(tmp_path, force=True)
        assert result.total_removed > 0
        # Settings file should be gone
        assert not (tmp_path / ".claude" / "settings.json").exists()

    def test_clean_result_fields(self, tmp_path):
        """CleanResult has the new restored and skipped_preexisting fields."""
        result = CleanResult()
        assert result.restored == []
        assert result.skipped_preexisting == []

    def test_backup_dir_cleaned(self, tmp_path):
        """Backup directory is removed after clean."""
        (tmp_path / "CLAUDE.md").write_text("original")
        _generate_project(tmp_path)
        assert (tmp_path / _BACKUP_DIR).exists()

        run_clean(tmp_path, force=True)
        assert not (tmp_path / _BACKUP_DIR).exists()


class TestSafeCleanBackwardCompat:
    def test_old_manifest_without_metadata(self, tmp_path):
        """Clean works with manifests that lack file_metadata (backward compat)."""
        _generate_project(tmp_path)

        # Strip file_metadata from manifest to simulate old format
        manifest_path = tmp_path / ".claude" / ".cc-rig-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest.pop("file_metadata", None)
        manifest_path.write_text(json.dumps(manifest))

        # Clean should still work — treats all files as non-pre-existing
        result = run_clean(tmp_path, force=True)
        assert result.total_removed > 0
        assert not (tmp_path / "CLAUDE.md").exists()

    def test_empty_metadata_treated_as_new(self, tmp_path):
        """Files with no metadata entry are treated as non-pre-existing."""
        _generate_project(tmp_path)
        result = run_clean(tmp_path, force=True)
        # All files should be removed (none were pre-existing)
        assert result.total_removed > 0
        assert len(result.restored) == 0
        assert len(result.skipped_preexisting) == 0


class TestSafeCleanPreExistingNoBackup:
    def test_skips_when_no_backup(self, tmp_path):
        """Pre-existing file without backup is skipped (not deleted)."""
        (tmp_path / "CLAUDE.md").write_text("original")
        _generate_project(tmp_path)

        # Manually delete the backup to simulate missing backup
        backup = tmp_path / _BACKUP_DIR / "CLAUDE.md.bak"
        if backup.exists():
            backup.unlink()

        result = run_clean(tmp_path, force=True)
        # Should skip, not delete
        assert "CLAUDE.md" in result.skipped_preexisting
        assert "CLAUDE.md" not in result.removed
        # File should still exist with the generated content (not deleted)
        assert (tmp_path / "CLAUDE.md").exists()


class TestManifestHasFileMetadata:
    def test_manifest_contains_file_metadata(self, tmp_path):
        """Generated manifests contain the file_metadata key."""
        _generate_project(tmp_path)
        manifest = load_manifest(tmp_path)
        assert "file_metadata" in manifest
        assert isinstance(manifest["file_metadata"], dict)
        # CLAUDE.md should be tracked
        assert "CLAUDE.md" in manifest["file_metadata"]
        assert manifest["file_metadata"]["CLAUDE.md"]["pre_existed"] is False

    def test_manifest_memory_files_have_preserve_flag(self, tmp_path):
        """Memory files should have preserve_on_clean and content_hash in metadata."""
        _generate_with_features(tmp_path, workflow="standard")
        manifest = load_manifest(tmp_path)
        meta = manifest["file_metadata"]
        for filename in [
            "memory/decisions.md",
            "memory/patterns.md",
            "memory/gotchas.md",
            "memory/people.md",
            "memory/session-log.md",
            "memory/MEMORY-README.md",
        ]:
            assert filename in meta, f"{filename} missing from file_metadata"
            assert meta[filename]["preserve_on_clean"] is True
            assert "content_hash" in meta[filename]
            assert len(meta[filename]["content_hash"]) == 64  # sha256 hex


class TestPreserveOnClean:
    def test_modified_memory_file_preserved(self, tmp_path):
        """Edited memory files survive clean."""
        _generate_with_features(tmp_path, workflow="standard")
        decisions = tmp_path / "memory" / "decisions.md"
        assert decisions.exists()
        decisions.write_text("# Decisions\n\nReal decision here.\n")

        result = run_clean(tmp_path, force=True)
        assert "memory/decisions.md" in result.skipped_user_modified
        assert decisions.exists()
        assert "Real decision" in decisions.read_text()

    def test_unmodified_memory_file_deleted(self, tmp_path):
        """Unedited memory files are deleted normally."""
        _generate_with_features(tmp_path, workflow="standard")
        decisions = tmp_path / "memory" / "decisions.md"
        assert decisions.exists()

        result = run_clean(tmp_path, force=True)
        assert "memory/decisions.md" not in result.skipped_user_modified
        assert "memory/decisions.md" in result.removed

    def test_modified_gtd_file_preserved(self, tmp_path):
        """Edited GTD task files survive clean."""
        _generate_with_gtd(tmp_path)
        inbox = tmp_path / "tasks" / "inbox.md"
        assert inbox.exists()
        inbox.write_text("# Inbox\n\n- [ ] My real task\n")

        result = run_clean(tmp_path, force=True)
        assert "tasks/inbox.md" in result.skipped_user_modified
        assert inbox.exists()

    def test_modified_spec_file_preserved(self, tmp_path):
        """Edited spec template survives clean."""
        _generate_with_features(tmp_path, workflow="spec-driven")
        spec = tmp_path / "specs" / "TEMPLATE.md"
        assert spec.exists()
        spec.write_text("# Spec: Auth Feature\n\nReal spec content.\n")

        result = run_clean(tmp_path, force=True)
        assert "specs/TEMPLATE.md" in result.skipped_user_modified
        assert spec.exists()

    def test_clean_result_has_skipped_user_modified(self, tmp_path):
        """CleanResult initializes skipped_user_modified as empty list."""
        result = CleanResult()
        assert result.skipped_user_modified == []
