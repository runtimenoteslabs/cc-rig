"""Tests for CLI init subcommand: zero-config, arg parsing, preset list."""

import json
from unittest.mock import patch

import pytest

from cc_rig.cli import build_parser, main
from cc_rig.skills.downloader import SkillInstallReport


@pytest.fixture(autouse=True)
def _mock_skill_downloads():
    """Mock skill downloads to avoid network calls in CLI tests."""
    report = SkillInstallReport()
    object.__setattr__(report, "_files", [])
    with patch("cc_rig.generators.skills.download_skills", return_value=report):
        yield


class TestZeroConfig:
    def test_generates_files(self, tmp_path):
        output = tmp_path / "out"
        rc = main(
            [
                "init",
                "--template",
                "fastapi",
                "--workflow",
                "standard",
                "--name",
                "test-project",
                "-o",
                str(output),
            ]
        )
        assert rc == 0
        assert (output / "CLAUDE.md").exists()
        assert (output / ".claude" / "settings.json").exists()
        assert (output / ".cc-rig.json").exists()

    def test_config_has_correct_template(self, tmp_path):
        output = tmp_path / "out"
        main(
            [
                "init",
                "--template",
                "django",
                "--workflow",
                "speedrun",
                "--name",
                "my-django",
                "-o",
                str(output),
            ]
        )
        data = json.loads((output / ".cc-rig.json").read_text())
        assert data["framework"] == "django"
        assert data["workflow"] == "speedrun"

    def test_all_templates_work(self, tmp_path):
        from cc_rig.presets.manager import BUILTIN_TEMPLATES

        for template in BUILTIN_TEMPLATES:
            output = tmp_path / template
            rc = main(
                [
                    "init",
                    "--template",
                    template,
                    "--workflow",
                    "standard",
                    "-o",
                    str(output),
                ]
            )
            assert rc == 0, f"Failed for template: {template}"
            assert (output / "CLAUDE.md").exists()

    def test_all_workflows_work(self, tmp_path):
        from cc_rig.presets.manager import BUILTIN_WORKFLOWS

        for workflow in BUILTIN_WORKFLOWS:
            output = tmp_path / workflow
            rc = main(
                [
                    "init",
                    "--template",
                    "fastapi",
                    "--workflow",
                    workflow,
                    "-o",
                    str(output),
                ]
            )
            assert rc == 0, f"Failed for workflow: {workflow}"

    def test_invalid_template_returns_error(self, tmp_path):
        output = tmp_path / "out"
        rc = main(
            [
                "init",
                "--template",
                "nonexistent",
                "--workflow",
                "standard",
                "-o",
                str(output),
            ]
        )
        assert rc == 1

    def test_invalid_workflow_returns_error(self, tmp_path):
        output = tmp_path / "out"
        rc = main(
            [
                "init",
                "--template",
                "fastapi",
                "--workflow",
                "nonexistent",
                "-o",
                str(output),
            ]
        )
        assert rc == 1


class TestConfigLoad:
    def test_load_config_file(self, tmp_path):
        # First generate a config
        output1 = tmp_path / "first"
        main(
            [
                "init",
                "--template",
                "fastapi",
                "--workflow",
                "standard",
                "--name",
                "original",
                "-o",
                str(output1),
            ]
        )
        config_path = output1 / ".cc-rig.json"

        # Now load that config into a new output
        output2 = tmp_path / "second"
        rc = main(
            [
                "init",
                "--config",
                str(config_path),
                "--name",
                "reloaded",
                "-o",
                str(output2),
            ]
        )
        assert rc == 0
        assert (output2 / "CLAUDE.md").exists()
        data = json.loads((output2 / ".cc-rig.json").read_text())
        assert data["framework"] == "fastapi"

    def test_missing_config_returns_error(self, tmp_path):
        rc = main(
            [
                "init",
                "--config",
                str(tmp_path / "nope.json"),
                "-o",
                str(tmp_path / "out"),
            ]
        )
        assert rc == 1


class TestArgParsing:
    def test_init_flags_parsed(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "init",
                "--template",
                "nextjs",
                "--workflow",
                "speedrun",
                "--name",
                "myapp",
                "-o",
                "/tmp/test",
            ]
        )
        assert args.template == "nextjs"
        assert args.workflow == "speedrun"
        assert args.name == "myapp"
        assert args.output == "/tmp/test"

    def test_init_quick_flag(self):
        parser = build_parser()
        args = parser.parse_args(["init", "--quick"])
        assert args.quick is True

    def test_init_expert_flag(self):
        parser = build_parser()
        args = parser.parse_args(["init", "--expert"])
        assert args.expert is True

    def test_init_migrate_flag(self):
        parser = build_parser()
        args = parser.parse_args(["init", "--migrate"])
        assert args.migrate is True


class TestPresetList:
    def test_preset_list_runs(self, capsys):
        rc = main(["preset", "list"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "fastapi" in captured.out
        assert "standard" in captured.out

    def test_preset_default_is_list(self, capsys):
        rc = main(["preset"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Templates:" in captured.out
        assert "Workflows:" in captured.out


class TestNoCommand:
    def test_no_command_shows_help(self, capsys):
        rc = main([])
        assert rc == 0


class TestDoctorAndClean:
    def test_doctor_runs_successfully(self, tmp_path, capsys):
        """Doctor returns 0 with warnings on a generated project directory."""
        # Generate a project first so doctor has something to check
        main(
            [
                "init",
                "--template",
                "fastapi",
                "--workflow",
                "speedrun",
                "--name",
                "test",
                "-o",
                str(tmp_path),
            ]
        )
        rc = main(["doctor", "--dir", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "warning" in captured.out.lower() or "passed" in captured.out.lower()

    def test_clean_requires_manifest(self, tmp_path, capsys):
        """Clean returns 1 when no .cc-rig.json manifest exists."""
        rc = main(["clean", "--dir", str(tmp_path)])
        assert rc == 1

    def test_clean_force_skips_confirm(self, tmp_path):
        """Clean with --force removes files without stdin prompt."""
        # Generate files first
        main(
            [
                "init",
                "--template",
                "fastapi",
                "--workflow",
                "speedrun",
                "--name",
                "test",
                "-o",
                str(tmp_path),
            ]
        )
        assert (tmp_path / ".cc-rig.json").exists()
        rc = main(["clean", "--force", "--dir", str(tmp_path)])
        assert rc == 0
        assert not (tmp_path / ".cc-rig.json").exists()
