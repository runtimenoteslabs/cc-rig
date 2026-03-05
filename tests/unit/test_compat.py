"""Tests for --check-compat feature compatibility checking."""

from __future__ import annotations

from typing import Optional
from unittest.mock import patch

import pytest

from cc_rig.config.cc_version import (
    FEATURE_MIN_VERSIONS,
    check_feature_compat,
)
from cc_rig.config.project import PluginRecommendation, ProjectConfig


def _make_config(
    agents: Optional[list[str]] = None,
    plugins: Optional[list[PluginRecommendation]] = None,
) -> ProjectConfig:
    """Build a minimal ProjectConfig for compat testing."""
    from tests.conftest import make_valid_config

    config = make_valid_config()
    if agents is not None:
        config.agents = agents
    if plugins is not None:
        config.recommended_plugins = plugins
    else:
        config.recommended_plugins = []
    return config


class TestCheckFeatureCompat:
    """Tests for check_feature_compat()."""

    def test_no_warnings_when_version_none(self) -> None:
        config = _make_config()
        assert check_feature_compat(None, config) == []

    def test_no_warnings_when_version_meets_all(self) -> None:
        config = _make_config()
        # Use a very high version
        assert check_feature_compat((99, 0, 0), config) == []

    def test_plugin_warning_on_old_version(self) -> None:
        plugin = PluginRecommendation(
            name="test-plugin",
            category="utility",
        )
        config = _make_config(plugins=[plugin])
        old_version = (1, 0, 0)
        warnings = check_feature_compat(old_version, config)
        assert any("Plugins require" in w for w in warnings)

    def test_no_plugin_warning_when_no_plugins(self) -> None:
        config = _make_config(plugins=[])
        old_version = (1, 0, 0)
        warnings = check_feature_compat(old_version, config)
        assert not any("Plugins require" in w for w in warnings)

    def test_background_agent_warning(self) -> None:
        config = _make_config(agents=["parallel-worker"])
        old_version = (1, 0, 0)
        warnings = check_feature_compat(old_version, config)
        assert any("background mode" in w for w in warnings)

    def test_worktree_isolation_warning(self) -> None:
        config = _make_config(agents=["parallel-worker"])
        old_version = (1, 0, 0)
        warnings = check_feature_compat(old_version, config)
        # parallel-worker has both background and isolation;
        # we should get at least one warning about it
        assert any("parallel-worker" in w for w in warnings)

    def test_no_agent_warning_for_basic_agents(self) -> None:
        config = _make_config(agents=["code-reviewer"])
        old_version = (1, 0, 0)
        warnings = check_feature_compat(old_version, config)
        assert not any("background" in w.lower() for w in warnings)
        assert not any("worktree" in w.lower() for w in warnings)

    def test_multiple_warnings(self) -> None:
        plugin = PluginRecommendation(
            name="test-plugin",
            category="utility",
        )
        config = _make_config(
            agents=["parallel-worker"],
            plugins=[plugin],
        )
        old_version = (1, 0, 0)
        warnings = check_feature_compat(old_version, config)
        assert len(warnings) >= 2

    def test_settings_local_warning(self) -> None:
        config = _make_config()
        old_version = (1, 0, 0)
        warnings = check_feature_compat(old_version, config)
        assert any("settings.local.json" in w for w in warnings)

    def test_feature_min_versions_populated(self) -> None:
        """FEATURE_MIN_VERSIONS has expected keys."""
        assert "plugins" in FEATURE_MIN_VERSIONS
        assert "background_agents" in FEATURE_MIN_VERSIONS
        assert "worktree_isolation" in FEATURE_MIN_VERSIONS
        assert "settings_local" in FEATURE_MIN_VERSIONS


class TestDoctorCheckCompat:
    """Tests for --check-compat integration with doctor."""

    def test_doctor_check_compat_flag(self, tmp_path: "pytest.TempPathFactory") -> None:
        """Verify --check-compat CLI flag is parsed."""
        from cc_rig.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["doctor", "--check-compat"])
        assert args.check_compat is True

    def test_doctor_check_compat_runs_only_compat(self, tmp_path: "pytest.TempPathFactory") -> None:
        """check_compat=True skips regular checks, runs only compat."""
        import json
        from pathlib import Path

        from cc_rig.doctor import run_doctor

        # Create a minimal .cc-rig.json
        project_dir = tmp_path if isinstance(tmp_path, Path) else Path(str(tmp_path))
        config_data = {
            "project_name": "test",
            "template_preset": "fastapi",
            "workflow_preset": "standard",
            "workflow": "standard",
            "language": "python",
            "framework": "fastapi",
            "project_type": "web",
            "agents": [],
            "commands": [],
            "hooks": [],
            "features": {},
            "permission_mode": "default",
        }
        (project_dir / ".cc-rig.json").write_text(json.dumps(config_data))

        # Run with check_compat=True — should not error on missing manifest etc.
        with patch("cc_rig.config.cc_version.detect_cc_version") as mock_detect:
            mock_detect.return_value = type(
                "R",
                (),
                {
                    "installed": True,
                    "version": (99, 0, 0),
                    "version_str": "99.0.0",
                    "warnings": [],
                },
            )()
            result = run_doctor(project_dir, check_compat=True)
            assert result.passed
