"""Tests for safe clean: restore pre-existing files, skip, backward compat."""

import json

from cc_rig.clean import CleanResult, load_manifest, run_clean
from cc_rig.generators.fileops import _BACKUP_DIR
from tests.conftest import generate_project as _generate_project


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

        # Backup should exist
        backup = tmp_path / _BACKUP_DIR / "CLAUDE.md"
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
        backup = tmp_path / _BACKUP_DIR / "CLAUDE.md"
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
