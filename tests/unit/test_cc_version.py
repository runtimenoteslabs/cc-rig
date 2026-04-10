"""Tests for Claude Code version detection."""

from unittest.mock import patch

from cc_rig.config.cc_version import (
    MIN_CC_VERSION,
    CCVersionResult,
    _parse_version,
    detect_cc_version,
)


class TestParseVersion:
    def test_simple_version(self):
        assert _parse_version("2.1.50") == (2, 1, 50)

    def test_claude_prefix(self):
        assert _parse_version("claude 2.1.50") == (2, 1, 50)

    def test_version_in_sentence(self):
        assert _parse_version("Claude Code v2.3.1 (stable)") == (2, 3, 1)

    def test_no_version(self):
        assert _parse_version("no version here") is None

    def test_empty_string(self):
        assert _parse_version("") is None

    def test_partial_version(self):
        # Only two numbers — not a valid semver
        assert _parse_version("2.1") is None


class TestCCVersionResult:
    def test_meets_minimum_when_installed(self):
        r = CCVersionResult(
            installed=True,
            version=(2, 1, 94),
            version_str="2.1.94",
            warnings=[],
        )
        assert r.meets_minimum is True

    def test_does_not_meet_minimum_when_old(self):
        r = CCVersionResult(
            installed=True,
            version=(2, 0, 0),
            version_str="2.0.0",
            warnings=["old"],
        )
        assert r.meets_minimum is False

    def test_does_not_meet_minimum_when_not_installed(self):
        r = CCVersionResult(
            installed=False,
            version=None,
            version_str="not found",
            warnings=["not found"],
        )
        assert r.meets_minimum is False

    def test_newer_version_meets_minimum(self):
        r = CCVersionResult(
            installed=True,
            version=(3, 0, 0),
            version_str="3.0.0",
            warnings=[],
        )
        assert r.meets_minimum is True


class TestDetectCCVersion:
    @patch("cc_rig.config.cc_version.subprocess.run")
    def test_claude_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        result = detect_cc_version()
        assert result.installed is False
        assert result.version is None
        assert len(result.warnings) == 1
        assert "not detected" in result.warnings[0]

    @patch("cc_rig.config.cc_version.subprocess.run")
    def test_claude_current_version(self, mock_run):
        mock_run.return_value.stdout = "claude 2.1.100\n"
        mock_run.return_value.stderr = ""
        result = detect_cc_version()
        assert result.installed is True
        assert result.version == (2, 1, 100)
        assert result.version_str == "2.1.100"
        assert result.warnings == []

    @patch("cc_rig.config.cc_version.subprocess.run")
    def test_claude_newer_version(self, mock_run):
        mock_run.return_value.stdout = "claude 3.0.0\n"
        mock_run.return_value.stderr = ""
        result = detect_cc_version()
        assert result.installed is True
        assert result.meets_minimum is True
        assert result.warnings == []

    @patch("cc_rig.config.cc_version.subprocess.run")
    def test_claude_old_version(self, mock_run):
        mock_run.return_value.stdout = "claude 2.0.5\n"
        mock_run.return_value.stderr = ""
        result = detect_cc_version()
        assert result.installed is True
        assert result.version == (2, 0, 5)
        assert len(result.warnings) == 1
        assert "2.1.94" in result.warnings[0]

    @patch("cc_rig.config.cc_version.subprocess.run")
    def test_unparseable_output(self, mock_run):
        mock_run.return_value.stdout = "something unexpected\n"
        mock_run.return_value.stderr = ""
        result = detect_cc_version()
        assert result.installed is True
        assert result.version is None
        assert result.version_str == "unknown"
        assert len(result.warnings) == 1

    @patch("cc_rig.config.cc_version.subprocess.run")
    def test_timeout(self, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("claude", 10)
        result = detect_cc_version()
        assert result.installed is False
        assert len(result.warnings) == 1

    @patch("cc_rig.config.cc_version.subprocess.run")
    def test_oserror(self, mock_run):
        mock_run.side_effect = OSError("permission denied")
        result = detect_cc_version()
        assert result.installed is False
        assert len(result.warnings) == 1

    def test_min_version_constant_is_valid_semver_tuple(self):
        assert len(MIN_CC_VERSION) == 3
        assert all(isinstance(v, int) and v >= 0 for v in MIN_CC_VERSION)

    def test_min_version_used_by_meets_minimum(self):
        """Verify meets_minimum actually uses MIN_CC_VERSION as threshold."""
        just_below = (MIN_CC_VERSION[0], MIN_CC_VERSION[1], MIN_CC_VERSION[2] - 1)
        below = CCVersionResult(installed=True, version=just_below, version_str="x", warnings=[])
        at_min = CCVersionResult(
            installed=True, version=MIN_CC_VERSION, version_str="x", warnings=[]
        )
        assert below.meets_minimum is False
        assert at_min.meets_minimum is True
