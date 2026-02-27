"""Tests for cc-rig skills CLI subcommand."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cc_rig.cli import build_parser, main
from cc_rig.skills.downloader import SkillInstallReport
from cc_rig.skills.registry import SKILL_CATALOG

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_project(tmp_path: Path) -> Path:
    """Generate a project in tmp_path so skills commands have context."""
    with patch("cc_rig.generators.skills.download_skills") as mock_dl:
        report = SkillInstallReport()
        object.__setattr__(report, "_files", [])
        mock_dl.return_value = report
        main(
            [
                "init",
                "--template",
                "fastapi",
                "--workflow",
                "standard",
                "--name",
                "test",
                "-o",
                str(tmp_path),
            ]
        )
    return tmp_path


def _install_fake_skill(project_dir: Path, name: str) -> Path:
    """Create a fake skill directory to simulate installation."""
    skill_dir = project_dir / ".claude" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(f"# {name}\nFake skill for testing.\n")
    return skill_md


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestSkillsParser:
    """Verify skills subcommand is registered."""

    def test_skills_command_exists(self):
        parser = build_parser()
        args = parser.parse_args(["skills", "catalog"])
        assert args.command == "skills"
        assert args.skills_command == "catalog"

    def test_skills_list_parsed(self):
        parser = build_parser()
        args = parser.parse_args(["skills", "list"])
        assert args.skills_command == "list"

    def test_skills_add_parsed(self):
        parser = build_parser()
        args = parser.parse_args(["skills", "add", "owasp-security"])
        assert args.skills_command == "add"
        assert args.name == "owasp-security"

    def test_skills_remove_parsed(self):
        parser = build_parser()
        args = parser.parse_args(["skills", "remove", "owasp-security"])
        assert args.skills_command == "remove"
        assert args.name == "owasp-security"

    def test_skills_install_parsed(self):
        parser = build_parser()
        args = parser.parse_args(["skills", "install"])
        assert args.skills_command == "install"

    def test_skills_dir_flag(self):
        parser = build_parser()
        args = parser.parse_args(["skills", "list", "-d", "/tmp/proj"])
        assert args.dir == "/tmp/proj"

    def test_skills_catalog_phase_filter(self):
        parser = build_parser()
        args = parser.parse_args(["skills", "catalog", "--phase", "testing"])
        assert args.phase == "testing"


# ---------------------------------------------------------------------------
# cc-rig skills catalog
# ---------------------------------------------------------------------------


class TestSkillsCatalog:
    """catalog shows all available skills from the registry."""

    def test_catalog_returns_zero(self, capsys):
        rc = main(["skills", "catalog"])
        assert rc == 0

    def test_catalog_shows_skill_count(self, capsys):
        main(["skills", "catalog"])
        output = capsys.readouterr().out
        assert f"{len(SKILL_CATALOG)} skills" in output

    def test_catalog_shows_phases(self, capsys):
        main(["skills", "catalog"])
        output = capsys.readouterr().out
        assert "CODING" in output
        assert "TESTING" in output
        assert "SECURITY" in output

    def test_catalog_shows_skill_names(self, capsys):
        main(["skills", "catalog"])
        output = capsys.readouterr().out
        assert "owasp-security" in output
        assert "test-driven-development" in output

    def test_catalog_phase_filter(self, capsys):
        main(["skills", "catalog", "--phase", "security"])
        output = capsys.readouterr().out
        assert "owasp-security" in output
        assert "TESTING" not in output


# ---------------------------------------------------------------------------
# cc-rig skills list
# ---------------------------------------------------------------------------


class TestSkillsList:
    """list shows installed skills."""

    def test_no_skills_dir(self, tmp_path, capsys):
        rc = main(["skills", "list", "-d", str(tmp_path)])
        assert rc == 0
        output = capsys.readouterr().out
        assert "No skills installed" in output

    def test_shows_installed_skills(self, tmp_path, capsys):
        _install_fake_skill(tmp_path, "owasp-security")
        _install_fake_skill(tmp_path, "modern-python")
        rc = main(["skills", "list", "-d", str(tmp_path)])
        assert rc == 0
        output = capsys.readouterr().out
        assert "owasp-security" in output
        assert "modern-python" in output
        assert "2" in output  # count

    def test_groups_by_phase(self, tmp_path, capsys):
        _install_fake_skill(tmp_path, "owasp-security")
        _install_fake_skill(tmp_path, "modern-python")
        main(["skills", "list", "-d", str(tmp_path)])
        output = capsys.readouterr().out
        assert "SECURITY" in output
        assert "CODING" in output

    def test_local_skills_shown(self, tmp_path, capsys):
        """Skills not in catalog get phase 'local'."""
        _install_fake_skill(tmp_path, "custom-team-skill")
        main(["skills", "list", "-d", str(tmp_path)])
        output = capsys.readouterr().out
        assert "custom-team-skill" in output
        assert "LOCAL" in output


# ---------------------------------------------------------------------------
# cc-rig skills add
# ---------------------------------------------------------------------------


class TestSkillsAdd:
    """add downloads a skill from the catalog."""

    def test_unknown_skill(self, tmp_path, capsys):
        rc = main(["skills", "add", "nonexistent-skill", "-d", str(tmp_path)])
        assert rc == 1
        output = capsys.readouterr().out
        assert "Unknown skill" in output

    def test_already_installed(self, tmp_path, capsys):
        _install_fake_skill(tmp_path, "owasp-security")
        rc = main(["skills", "add", "owasp-security", "-d", str(tmp_path)])
        assert rc == 0
        output = capsys.readouterr().out
        assert "already installed" in output

    def test_successful_download(self, tmp_path, capsys):
        report = SkillInstallReport()
        object.__setattr__(report, "_files", [".claude/skills/owasp-security/SKILL.md"])
        report.installed.append("owasp-security")

        with patch("cc_rig.skills.downloader.download_skills", return_value=report):
            rc = main(["skills", "add", "owasp-security", "-d", str(tmp_path)])

        assert rc == 0
        output = capsys.readouterr().out
        assert "Installed: owasp-security" in output

    def test_failed_download(self, tmp_path, capsys):
        report = SkillInstallReport()
        object.__setattr__(report, "_files", [])
        report.failed.append(("owasp-security", "connection timeout"))

        with patch("cc_rig.skills.downloader.download_skills", return_value=report):
            rc = main(["skills", "add", "owasp-security", "-d", str(tmp_path)])

        assert rc == 1
        output = capsys.readouterr().out
        assert "Failed" in output


# ---------------------------------------------------------------------------
# cc-rig skills remove
# ---------------------------------------------------------------------------


class TestSkillsRemove:
    """remove deletes an installed skill."""

    def test_remove_nonexistent(self, tmp_path, capsys):
        rc = main(["skills", "remove", "nonexistent", "-d", str(tmp_path)])
        assert rc == 1
        output = capsys.readouterr().out
        assert "not installed" in output

    def test_remove_installed(self, tmp_path, capsys):
        _install_fake_skill(tmp_path, "owasp-security")
        assert (tmp_path / ".claude" / "skills" / "owasp-security").exists()

        rc = main(["skills", "remove", "owasp-security", "-d", str(tmp_path)])
        assert rc == 0
        assert not (tmp_path / ".claude" / "skills" / "owasp-security").exists()
        output = capsys.readouterr().out
        assert "Removed: owasp-security" in output


# ---------------------------------------------------------------------------
# cc-rig skills install (retry)
# ---------------------------------------------------------------------------


class TestSkillsInstall:
    """install retries failed downloads."""

    def test_no_cc_rig_json(self, tmp_path, capsys):
        rc = main(["skills", "install", "-d", str(tmp_path)])
        assert rc == 1
        output = capsys.readouterr().out
        assert "No .cc-rig.json" in output

    def test_all_already_installed(self, tmp_path, capsys):
        project = _init_project(tmp_path)
        # Install all resolved skills as fakes
        from cc_rig.skills.registry import resolve_skills

        specs = resolve_skills("fastapi", "standard", ["github", "postgres"])
        for spec in specs:
            _install_fake_skill(project, spec.name)

        rc = main(["skills", "install", "-d", str(project)])
        assert rc == 0
        output = capsys.readouterr().out
        assert "already installed" in output

    def test_installs_missing_skills(self, tmp_path, capsys):
        project = _init_project(tmp_path)

        report = SkillInstallReport()
        object.__setattr__(report, "_files", [".claude/skills/owasp-security/SKILL.md"])
        report.installed.append("owasp-security")

        with patch("cc_rig.skills.downloader.download_skills", return_value=report):
            rc = main(["skills", "install", "-d", str(project)])

        assert rc == 0
        output = capsys.readouterr().out
        assert "owasp-security" in output


# ---------------------------------------------------------------------------
# Default subcommand
# ---------------------------------------------------------------------------


class TestSkillsDefault:
    """No subcommand defaults to list."""

    def test_no_subcommand_defaults_to_list(self, capsys):
        rc = main(["skills"])
        # Should default to list behavior (returns 0)
        assert rc == 0
