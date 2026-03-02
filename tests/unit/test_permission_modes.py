"""Tests for permission mode content — explicit comparison of default vs permissive."""

import json

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.settings import generate_settings


def _get_permissions(tmp_path, workflow):
    config = compute_defaults("fastapi", workflow, project_name="test")
    generate_settings(config, tmp_path)
    data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    return data["permissions"]


class TestPermissionModeComparison:
    """Side-by-side comparison of default vs permissive modes."""

    def test_permissive_is_superset_of_default(self, tmp_path):
        default_dir = tmp_path / "default"
        permissive_dir = tmp_path / "permissive"
        default_perms = _get_permissions(default_dir, "speedrun")
        permissive_perms = _get_permissions(permissive_dir, "standard")
        default_allow = set(default_perms["allow"])
        permissive_allow = set(permissive_perms["allow"])
        assert default_allow.issubset(permissive_allow), (
            f"Default allow {default_allow} is not a subset of permissive allow {permissive_allow}"
        )

    def test_permissive_has_bash(self, tmp_path):
        perms = _get_permissions(tmp_path, "standard")
        assert "Bash" in perms["allow"]

    def test_default_lacks_bash(self, tmp_path):
        perms = _get_permissions(tmp_path, "speedrun")
        assert "Bash" not in perms["allow"]

    def test_permissive_has_task(self, tmp_path):
        perms = _get_permissions(tmp_path, "standard")
        assert "Task" in perms["allow"]

    def test_default_lacks_task(self, tmp_path):
        perms = _get_permissions(tmp_path, "speedrun")
        assert "Task" not in perms["allow"]

    def test_permissive_has_web_tools(self, tmp_path):
        perms = _get_permissions(tmp_path, "standard")
        assert "WebSearch" in perms["allow"]
        assert "WebFetch" in perms["allow"]

    def test_default_lacks_web_tools(self, tmp_path):
        perms = _get_permissions(tmp_path, "speedrun")
        assert "WebSearch" not in perms["allow"]
        assert "WebFetch" not in perms["allow"]


class TestDefaultAllowList:
    """Validate the complete allow list for default mode."""

    def test_default_allow_contents(self, tmp_path):
        perms = _get_permissions(tmp_path, "speedrun")
        expected = {"Read", "Glob", "Grep", "Edit", "Write", "NotebookEdit"}
        assert set(perms["allow"]) == expected


class TestPermissiveAllowList:
    """Validate the complete allow list for permissive mode."""

    def test_permissive_allow_contents(self, tmp_path):
        perms = _get_permissions(tmp_path, "standard")
        expected = {
            "Read",
            "Glob",
            "Grep",
            "Edit",
            "Write",
            "NotebookEdit",
            "Bash",
            "WebSearch",
            "WebFetch",
            "Task",
        }
        assert set(perms["allow"]) == expected


class TestDenyList:
    """Validate deny list is consistent across modes."""

    def test_default_deny(self, tmp_path):
        perms = _get_permissions(tmp_path, "speedrun")
        assert "Bash(rm -rf /)" in perms["deny"]
        assert "Bash(rm -rf ~)" in perms["deny"]
        assert len(perms["deny"]) == 2

    def test_permissive_deny(self, tmp_path):
        perms = _get_permissions(tmp_path, "standard")
        assert "Bash(rm -rf /)" in perms["deny"]
        assert "Bash(rm -rf ~)" in perms["deny"]
        assert len(perms["deny"]) == 2

    def test_deny_identical_across_modes(self, tmp_path):
        default_dir = tmp_path / "default"
        permissive_dir = tmp_path / "permissive"
        default_perms = _get_permissions(default_dir, "speedrun")
        permissive_perms = _get_permissions(permissive_dir, "standard")
        assert default_perms["deny"] == permissive_perms["deny"]
