"""Tests for cc-rig config update command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from cc_rig.config.defaults import compute_defaults
from cc_rig.ui.prompts import IO


def _make_io(inputs: list[str] | None = None) -> IO:
    """Create a test IO with canned inputs."""
    from tests.conftest import make_io

    return make_io(inputs or [])


def _generate_config(tmp_path: Path, template: str = "fastapi", workflow: str = "standard") -> Path:
    """Generate a .cc-rig.json in tmp_path and return the path."""
    config = compute_defaults(
        template,
        workflow,
        project_name="test-project",
        output_dir=str(tmp_path),
    )
    config_path = tmp_path / ".cc-rig.json"
    config_path.write_text(config.to_json() + "\n")
    return config_path


class TestConfigUpdateCLI:
    """Tests for config update CLI integration."""

    def test_cli_config_update_subcommand_exists(self) -> None:
        from cc_rig.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["config", "update"])
        assert args.config_command == "update"

    def test_cli_config_update_with_dir(self) -> None:
        from cc_rig.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["config", "update", "-d", "/tmp/foo"])
        assert args.dir == "/tmp/foo"

    def test_cli_config_update_quick_flag(self) -> None:
        from cc_rig.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["config", "update", "--quick"])
        assert args.quick is True

    def test_cli_config_update_expert_flag(self) -> None:
        from cc_rig.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["config", "update", "--expert"])
        assert args.expert is True


class TestConfigUpdateFlow:
    """Tests for run_update_wizard()."""

    def test_update_no_config_returns_error(self, tmp_path: Path) -> None:
        from cc_rig.wizard.flow import run_update_wizard

        io = _make_io()
        result = run_update_wizard(tmp_path, io=io)
        assert result == 1

    def test_update_locked_config_blocked(self, tmp_path: Path) -> None:
        from cc_rig.wizard.flow import run_update_wizard

        _generate_config(tmp_path)
        config_path = tmp_path / ".cc-rig.json"
        data = json.loads(config_path.read_text())
        data["locked"] = True
        config_path.write_text(json.dumps(data))

        io = _make_io()
        result = run_update_wizard(tmp_path, io=io)
        assert result == 1

    def test_update_loads_existing_config(self, tmp_path: Path) -> None:
        """Verify run_update_wizard can read and parse .cc-rig.json."""
        from cc_rig.wizard.flow import run_update_wizard

        _generate_config(tmp_path, "fastapi", "standard")

        # Select same template (fastapi=2), same workflow (standard=2)
        # then "n" to decline regeneration if diff exists
        io = _make_io(["2", "2", "n"])
        result = run_update_wizard(tmp_path, io=io)
        assert result == 0

    def test_update_shows_diff_on_change(self, tmp_path: Path) -> None:
        """When template/workflow changes, diff should be shown."""
        from cc_rig.wizard.flow import run_update_wizard

        _generate_config(tmp_path, "fastapi", "standard")

        # Select django (4th in list), speedrun (1st in list), then "n" to cancel
        io = _make_io(["4", "1", "n"])

        with patch.object(io, "say", wraps=io.say) as mock_say:
            run_update_wizard(tmp_path, io=io)

        # Should have shown "Differences:" or "Changes from current config"
        all_output = " ".join(str(c) for c in mock_say.call_args_list)
        assert "Differences" in all_output or "Changes" in all_output

    def test_update_cancels_on_reject(self, tmp_path: Path) -> None:
        """User rejecting regeneration returns 0."""
        from cc_rig.wizard.flow import run_update_wizard

        _generate_config(tmp_path, "fastapi", "standard")

        # Select django, speedrun, then "n" to cancel
        io = _make_io(["4", "1", "n"])
        result = run_update_wizard(tmp_path, io=io)
        assert result == 0
