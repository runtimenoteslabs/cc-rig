"""Tests for clean command: manifest-based file removal."""

import pytest

from cc_rig.clean import CleanResult, load_manifest, run_clean
from cc_rig.cli import main
from tests.conftest import generate_project as _generate_project


class TestLoadManifest:
    def test_load_valid(self, tmp_path):
        _generate_project(tmp_path)
        manifest = load_manifest(tmp_path)
        assert manifest is not None
        assert "files" in manifest
        assert len(manifest["files"]) > 0

    def test_load_missing(self, tmp_path):
        assert load_manifest(tmp_path) is None

    def test_load_invalid_json(self, tmp_path):
        manifest_dir = tmp_path / ".claude"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / ".cc-rig-manifest.json").write_text("{bad")
        assert load_manifest(tmp_path) is None


class TestCleanBasic:
    def test_clean_removes_all_files(self, tmp_path):
        _generate_project(tmp_path)
        manifest = load_manifest(tmp_path)
        file_count = len(manifest["files"])

        result = run_clean(tmp_path, force=True)
        assert isinstance(result, CleanResult)
        # Should remove all manifest files + .cc-rig.json
        assert result.total_removed >= file_count

    def test_clean_removes_cc_rig_json(self, tmp_path):
        _generate_project(tmp_path)
        assert (tmp_path / ".cc-rig.json").exists()
        run_clean(tmp_path, force=True)
        assert not (tmp_path / ".cc-rig.json").exists()

    def test_clean_claude_md_removed(self, tmp_path):
        _generate_project(tmp_path)
        assert (tmp_path / "CLAUDE.md").exists()
        run_clean(tmp_path, force=True)
        assert not (tmp_path / "CLAUDE.md").exists()


class TestCleanDirectories:
    def test_empty_dirs_removed(self, tmp_path):
        _generate_project(tmp_path)
        run_clean(tmp_path, force=True)
        result_dirs = [
            tmp_path / ".claude",
            tmp_path / "agent_docs",
        ]
        for d in result_dirs:
            if d.name in ("memory",):
                continue
            # Directory should be gone if all its files were removed
            assert not d.exists() or any(d.iterdir()), f"{d} should be empty/removed"


class TestCleanAlreadyMissing:
    def test_handles_missing_files(self, tmp_path):
        _generate_project(tmp_path)
        # Remove a file before clean
        (tmp_path / "CLAUDE.md").unlink()
        result = run_clean(tmp_path, force=True)
        assert "CLAUDE.md" in result.already_missing

    def test_clean_all_already_gone(self, tmp_path):
        _generate_project(tmp_path)
        manifest = load_manifest(tmp_path)
        # Remove all files except the manifest itself
        manifest_rel = ".claude/.cc-rig-manifest.json"
        for rel in manifest["files"]:
            if rel == manifest_rel:
                continue
            p = tmp_path / rel
            if p.exists():
                p.unlink()
        result = run_clean(tmp_path, force=True)
        assert len(result.already_missing) > 0


class TestCleanConfirmation:
    def test_no_manifest_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="manifest"):
            run_clean(tmp_path, force=True)

    def test_confirm_yes_proceeds(self, tmp_path):
        _generate_project(tmp_path)
        result = run_clean(
            tmp_path,
            confirm_fn=lambda _: True,
        )
        assert result.total_removed > 0

    def test_confirm_no_cancels(self, tmp_path):
        _generate_project(tmp_path)
        result = run_clean(
            tmp_path,
            confirm_fn=lambda _: False,
        )
        assert result.total_removed == 0
        # Files should still exist
        assert (tmp_path / "CLAUDE.md").exists()

    def test_no_confirm_fn_raises(self, tmp_path):
        _generate_project(tmp_path)
        with pytest.raises(RuntimeError, match="[Cc]onfirmation"):
            run_clean(tmp_path)

    def test_force_skips_confirmation(self, tmp_path):
        _generate_project(tmp_path)
        result = run_clean(tmp_path, force=True)
        assert result.total_removed > 0


class TestCleanOnlyGeneratedFiles:
    def test_user_files_preserved(self, tmp_path):
        _generate_project(tmp_path)
        # Create a user file that is NOT in the manifest
        user_file = tmp_path / "my-notes.txt"
        user_file.write_text("important stuff")
        run_clean(tmp_path, force=True)
        assert user_file.exists()
        assert user_file.read_text() == "important stuff"

    def test_user_file_in_claude_dir_preserved(self, tmp_path):
        _generate_project(tmp_path)
        # Add a user file inside .claude/ that's not in manifest
        user_file = tmp_path / ".claude" / "my-custom-agent.md"
        user_file.write_text("custom")
        run_clean(tmp_path, force=True)
        assert user_file.exists()


class TestCleanCLI:
    def test_clean_force_runs(self, capsys, tmp_path):
        _generate_project(tmp_path)
        rc = main(["clean", "--force", "-d", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "removed" in captured.out.lower() or "clean" in captured.out.lower()

    def test_clean_no_manifest(self, capsys, tmp_path):
        rc = main(["clean", "--force", "-d", str(tmp_path)])
        assert rc == 1

    def test_clean_multiple_templates(self, tmp_path):
        """Clean works for projects generated with different templates."""
        for template in ("fastapi", "django", "nextjs"):
            proj_dir = tmp_path / template
            proj_dir.mkdir()
            _generate_project(proj_dir, template=template)
            result = run_clean(proj_dir, force=True)
            assert result.total_removed > 0
            assert not (proj_dir / "CLAUDE.md").exists()
