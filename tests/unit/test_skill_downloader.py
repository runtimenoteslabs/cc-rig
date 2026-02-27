"""Tests for cc_rig/skills/downloader.py.

Covers:
- download_skills() with skill_md_only mode
- download_skills() with full_tree mode
- Download failure handling — skill recorded in report.failed
- SkillInstallReport properties (failed_names, all_files)
- Timeout passed to urllib
- _fetch_text URL construction
- Full tree fallback to skill_md_only when directory listing fails
- Mixed success/failure (some skills succeed, some fail)
- Empty specs list returns empty report
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from cc_rig.generators.fileops import FileTracker
from cc_rig.skills.downloader import (
    SkillInstallReport,
    _fetch_text,
    _list_directory,
    download_skills,
)
from cc_rig.skills.registry import SkillSpec

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

_SKILL_MD_CONTENT = "# My Skill\n\nThis is a skill."
_EXTRA_FILE_CONTENT = "# Extra\n\nExtra content."


def _make_spec(
    name: str = "test-skill",
    repo: str = "owner/repo",
    repo_path: str = "skills/test-skill",
    download_mode: str = "skill_md_only",
) -> SkillSpec:
    return SkillSpec(
        name=name,
        repo=repo,
        repo_path=repo_path,
        sdlc_phase="testing",
        description="A test skill",
        download_mode=download_mode,
    )


def _make_url_response(content: str) -> MagicMock:
    """Return a context-manager mock that yields a response with encoded content."""
    resp = MagicMock()
    resp.read.return_value = content.encode("utf-8")
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=resp)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _make_api_response(entries: list[dict]) -> MagicMock:
    """Return a context-manager mock for a JSON directory listing response."""
    return _make_url_response(json.dumps(entries))


# ---------------------------------------------------------------------------
# SkillInstallReport — Unit tests for the dataclass
# ---------------------------------------------------------------------------


class TestSkillInstallReport:
    def test_initial_state_is_empty(self):
        report = SkillInstallReport()
        assert report.installed == []
        assert report.failed == []

    def test_failed_names_returns_set_of_names(self):
        report = SkillInstallReport()
        report.failed.append(("skill-a", "connection error"))
        report.failed.append(("skill-b", "timeout"))
        assert report.failed_names == {"skill-a", "skill-b"}

    def test_failed_names_empty_when_no_failures(self):
        report = SkillInstallReport()
        assert report.failed_names == set()

    def test_failed_names_deduplicates(self):
        """If the same skill fails multiple times, name appears once in failed_names."""
        report = SkillInstallReport()
        report.failed.append(("skill-a", "error one"))
        report.failed.append(("skill-a", "error two"))
        assert report.failed_names == {"skill-a"}

    def test_all_files_empty_initially(self):
        report = SkillInstallReport()
        # Initialise internal list the same way download_skills does
        object.__setattr__(report, "_files", [])
        assert report.all_files == []

    def test_add_file_appends_to_all_files(self):
        report = SkillInstallReport()
        object.__setattr__(report, "_files", [])
        report._add_file(".claude/skills/my-skill/SKILL.md")
        report._add_file(".claude/skills/my-skill/extra.md")
        assert report.all_files == [
            ".claude/skills/my-skill/SKILL.md",
            ".claude/skills/my-skill/extra.md",
        ]

    def test_add_file_creates_internal_list_on_first_call(self):
        """_add_file must work even if _files was never set."""
        report = SkillInstallReport()
        # Do NOT call object.__setattr__ — let _add_file handle it
        report._add_file(".claude/skills/x/SKILL.md")
        assert report.all_files == [".claude/skills/x/SKILL.md"]

    def test_all_files_returns_copy_like_list(self):
        """Mutating the returned list does not affect the report."""
        report = SkillInstallReport()
        object.__setattr__(report, "_files", [])
        report._add_file("file.md")
        files = report.all_files
        files.append("injected.md")
        assert len(report.all_files) == 1


# ---------------------------------------------------------------------------
# download_skills — Empty input
# ---------------------------------------------------------------------------


class TestDownloadSkillsEmpty:
    def test_empty_specs_returns_empty_report(self, tmp_path):
        report = download_skills([], tmp_path)
        assert report.installed == []
        assert report.failed == []
        assert report.all_files == []


# ---------------------------------------------------------------------------
# download_skills — skill_md_only mode (happy path)
# ---------------------------------------------------------------------------


class TestDownloadSkillsMdOnly:
    def test_installs_skill_and_adds_to_installed(self, tmp_path):
        spec = _make_spec(download_mode="skill_md_only")

        with patch("urllib.request.urlopen", return_value=_make_url_response(_SKILL_MD_CONTENT)):
            report = download_skills([spec], tmp_path)

        assert "test-skill" in report.installed
        assert report.failed == []

    def test_writes_skill_md_to_correct_path(self, tmp_path):
        spec = _make_spec(name="my-skill", download_mode="skill_md_only")

        with patch("urllib.request.urlopen", return_value=_make_url_response(_SKILL_MD_CONTENT)):
            download_skills([spec], tmp_path)

        expected = tmp_path / ".claude" / "skills" / "my-skill" / "SKILL.md"
        assert expected.exists()
        assert expected.read_text() == _SKILL_MD_CONTENT

    def test_file_recorded_in_all_files(self, tmp_path):
        spec = _make_spec(name="my-skill", download_mode="skill_md_only")

        with patch("urllib.request.urlopen", return_value=_make_url_response(_SKILL_MD_CONTENT)):
            report = download_skills([spec], tmp_path)

        assert ".claude/skills/my-skill/SKILL.md" in report.all_files

    def test_creates_parent_directories(self, tmp_path):
        spec = _make_spec(name="deep-skill", download_mode="skill_md_only")

        with patch("urllib.request.urlopen", return_value=_make_url_response(_SKILL_MD_CONTENT)):
            download_skills([spec], tmp_path)

        parent = tmp_path / ".claude" / "skills" / "deep-skill"
        assert parent.is_dir()

    def test_url_uses_raw_githubusercontent(self, tmp_path):
        spec = _make_spec(
            name="my-skill",
            repo="owner/repo",
            repo_path="skills/my-skill",
            download_mode="skill_md_only",
        )

        captured_requests: list[urllib.request.Request] = []

        def capturing_urlopen(req, timeout=None):
            captured_requests.append(req)
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            download_skills([spec], tmp_path)

        assert len(captured_requests) == 1
        url = captured_requests[0].full_url
        assert url == "https://raw.githubusercontent.com/owner/repo/main/skills/my-skill/SKILL.md"

    def test_timeout_passed_to_urlopen(self, tmp_path):
        spec = _make_spec(download_mode="skill_md_only")

        captured_timeouts: list[int] = []

        def capturing_urlopen(req, timeout=None):
            captured_timeouts.append(timeout)
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            download_skills([spec], tmp_path, timeout=42)

        assert captured_timeouts == [42]

    def test_default_timeout_is_ten(self, tmp_path):
        spec = _make_spec(download_mode="skill_md_only")

        captured_timeouts: list[int] = []

        def capturing_urlopen(req, timeout=None):
            captured_timeouts.append(timeout)
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            download_skills([spec], tmp_path)

        assert captured_timeouts == [10]

    def test_user_agent_header_set(self, tmp_path):
        spec = _make_spec(download_mode="skill_md_only")

        captured_requests: list[urllib.request.Request] = []

        def capturing_urlopen(req, timeout=None):
            captured_requests.append(req)
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            download_skills([spec], tmp_path)

        assert captured_requests[0].get_header("User-agent") == "cc-rig"

    def test_multiple_skills_all_installed(self, tmp_path):
        specs = [
            _make_spec(name="skill-a", download_mode="skill_md_only"),
            _make_spec(name="skill-b", download_mode="skill_md_only"),
            _make_spec(name="skill-c", download_mode="skill_md_only"),
        ]

        with patch("urllib.request.urlopen", return_value=_make_url_response(_SKILL_MD_CONTENT)):
            report = download_skills(specs, tmp_path)

        assert set(report.installed) == {"skill-a", "skill-b", "skill-c"}
        assert report.failed == []
        assert len(report.all_files) == 3


# ---------------------------------------------------------------------------
# download_skills — skill_md_only mode with FileTracker
# ---------------------------------------------------------------------------


class TestDownloadSkillsMdOnlyWithTracker:
    def test_uses_tracker_write_text_not_direct_io(self, tmp_path):
        spec = _make_spec(name="tracked-skill", download_mode="skill_md_only")
        tracker = MagicMock(spec=FileTracker)

        with patch("urllib.request.urlopen", return_value=_make_url_response(_SKILL_MD_CONTENT)):
            download_skills([spec], tmp_path, tracker=tracker)

        tracker.write_text.assert_called_once_with(
            ".claude/skills/tracked-skill/SKILL.md", _SKILL_MD_CONTENT
        )

    def test_tracker_does_not_write_file_directly(self, tmp_path):
        spec = _make_spec(name="tracked-skill", download_mode="skill_md_only")
        tracker = MagicMock(spec=FileTracker)

        with patch("urllib.request.urlopen", return_value=_make_url_response(_SKILL_MD_CONTENT)):
            download_skills([spec], tmp_path, tracker=tracker)

        # File should NOT be written to disk directly when tracker is provided
        direct_path = tmp_path / ".claude" / "skills" / "tracked-skill" / "SKILL.md"
        assert not direct_path.exists()

    def test_skill_still_appears_in_installed(self, tmp_path):
        spec = _make_spec(name="tracked-skill", download_mode="skill_md_only")
        tracker = MagicMock(spec=FileTracker)

        with patch("urllib.request.urlopen", return_value=_make_url_response(_SKILL_MD_CONTENT)):
            report = download_skills([spec], tmp_path, tracker=tracker)

        assert "tracked-skill" in report.installed

    def test_file_path_appears_in_all_files_with_tracker(self, tmp_path):
        spec = _make_spec(name="tracked-skill", download_mode="skill_md_only")
        tracker = MagicMock(spec=FileTracker)

        with patch("urllib.request.urlopen", return_value=_make_url_response(_SKILL_MD_CONTENT)):
            report = download_skills([spec], tmp_path, tracker=tracker)

        assert ".claude/skills/tracked-skill/SKILL.md" in report.all_files


# ---------------------------------------------------------------------------
# download_skills — full_tree mode (happy path)
# ---------------------------------------------------------------------------


class TestDownloadSkillsFullTree:
    def _api_entries(
        self,
        filenames: list[str],
        skill_path: str = "skills/test-skill",
    ) -> list[dict]:
        return [{"type": "file", "name": fn, "path": f"{skill_path}/{fn}"} for fn in filenames]

    def test_installs_skill_and_adds_to_installed(self, tmp_path):
        spec = _make_spec(download_mode="full_tree")
        entries = self._api_entries(["SKILL.md"])

        responses = [
            _make_api_response(entries),  # directory listing
            _make_url_response(_SKILL_MD_CONTENT),  # SKILL.md download
        ]

        with patch("urllib.request.urlopen", side_effect=responses):
            report = download_skills([spec], tmp_path)

        assert "test-skill" in report.installed
        assert report.failed == []

    def test_writes_skill_md_to_correct_path(self, tmp_path):
        spec = _make_spec(name="tree-skill", download_mode="full_tree")
        entries = self._api_entries(["SKILL.md"], skill_path="skills/tree-skill")

        responses = [
            _make_api_response(entries),
            _make_url_response(_SKILL_MD_CONTENT),
        ]

        with patch("urllib.request.urlopen", side_effect=responses):
            download_skills([spec], tmp_path)

        expected = tmp_path / ".claude" / "skills" / "tree-skill" / "SKILL.md"
        assert expected.exists()
        assert expected.read_text() == _SKILL_MD_CONTENT

    def test_writes_multiple_companion_files(self, tmp_path):
        spec = _make_spec(name="rich-skill", download_mode="full_tree")
        entries = self._api_entries(
            ["SKILL.md", "helpers.md", "examples.md"],
            skill_path="skills/rich-skill",
        )

        responses = [
            _make_api_response(entries),
            _make_url_response(_SKILL_MD_CONTENT),  # SKILL.md
            _make_url_response(_EXTRA_FILE_CONTENT),  # helpers.md
            _make_url_response(_EXTRA_FILE_CONTENT),  # examples.md
        ]

        with patch("urllib.request.urlopen", side_effect=responses):
            report = download_skills([spec], tmp_path)

        skill_dir = tmp_path / ".claude" / "skills" / "rich-skill"
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "helpers.md").exists()
        assert (skill_dir / "examples.md").exists()
        assert len(report.all_files) == 3

    def test_all_files_includes_companion_files(self, tmp_path):
        spec = _make_spec(name="rich-skill", download_mode="full_tree")
        entries = self._api_entries(
            ["SKILL.md", "helpers.md"],
            skill_path="skills/rich-skill",
        )

        responses = [
            _make_api_response(entries),
            _make_url_response(_SKILL_MD_CONTENT),
            _make_url_response(_EXTRA_FILE_CONTENT),
        ]

        with patch("urllib.request.urlopen", side_effect=responses):
            report = download_skills([spec], tmp_path)

        assert ".claude/skills/rich-skill/SKILL.md" in report.all_files
        assert ".claude/skills/rich-skill/helpers.md" in report.all_files

    def test_skips_directory_entries_in_api_response(self, tmp_path):
        spec = _make_spec(name="mixed-skill", download_mode="full_tree")
        entries = [
            {"type": "file", "name": "SKILL.md", "path": "skills/mixed-skill/SKILL.md"},
            {"type": "dir", "name": "subdir", "path": "skills/mixed-skill/subdir"},
        ]

        responses = [
            _make_api_response(entries),
            _make_url_response(_SKILL_MD_CONTENT),  # only SKILL.md downloaded
        ]

        with patch("urllib.request.urlopen", side_effect=responses):
            report = download_skills([spec], tmp_path)

        # Only one file should be installed (the subdir entry is skipped)
        assert len(report.all_files) == 1
        assert ".claude/skills/mixed-skill/SKILL.md" in report.all_files

    def test_api_url_uses_github_contents_api(self, tmp_path):
        spec = _make_spec(
            name="api-skill",
            repo="owner/repo",
            repo_path="skills/api-skill",
            download_mode="full_tree",
        )
        entries = [{"type": "file", "name": "SKILL.md", "path": "skills/api-skill/SKILL.md"}]

        captured_requests: list[urllib.request.Request] = []

        def capturing_urlopen(req, timeout=None):
            captured_requests.append(req)
            if "api.github.com" in req.full_url:
                return _make_api_response(entries)
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            download_skills([spec], tmp_path)

        api_requests = [r for r in captured_requests if "api.github.com" in r.full_url]
        assert len(api_requests) == 1
        assert api_requests[0].full_url == (
            "https://api.github.com/repos/owner/repo/contents/skills/api-skill"
        )

    def test_raw_url_uses_raw_githubusercontent_for_files(self, tmp_path):
        spec = _make_spec(
            name="raw-skill",
            repo="owner/repo",
            repo_path="skills/raw-skill",
            download_mode="full_tree",
        )
        entries = [{"type": "file", "name": "SKILL.md", "path": "skills/raw-skill/SKILL.md"}]

        captured_requests: list[urllib.request.Request] = []

        def capturing_urlopen(req, timeout=None):
            captured_requests.append(req)
            if "api.github.com" in req.full_url:
                return _make_api_response(entries)
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            download_skills([spec], tmp_path)

        raw_requests = [r for r in captured_requests if "raw.githubusercontent.com" in r.full_url]
        assert len(raw_requests) == 1
        assert raw_requests[0].full_url == (
            "https://raw.githubusercontent.com/owner/repo/main/skills/raw-skill/SKILL.md"
        )

    def test_timeout_passed_for_api_call(self, tmp_path):
        spec = _make_spec(download_mode="full_tree")
        entries = [{"type": "file", "name": "SKILL.md", "path": "skills/test-skill/SKILL.md"}]

        captured_timeouts: list[int] = []

        def capturing_urlopen(req, timeout=None):
            captured_timeouts.append(timeout)
            if "api.github.com" in req.full_url:
                return _make_api_response(entries)
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            download_skills([spec], tmp_path, timeout=30)

        assert all(t == 30 for t in captured_timeouts)

    def test_uses_tracker_for_all_files(self, tmp_path):
        spec = _make_spec(name="tracked-tree", download_mode="full_tree")
        entries = [
            {"type": "file", "name": "SKILL.md", "path": "skills/tracked-tree/SKILL.md"},
            {"type": "file", "name": "extra.md", "path": "skills/tracked-tree/extra.md"},
        ]
        tracker = MagicMock(spec=FileTracker)

        def capturing_urlopen(req, timeout=None):
            if "api.github.com" in req.full_url:
                return _make_api_response(entries)
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            download_skills([spec], tmp_path, tracker=tracker)

        assert tracker.write_text.call_count == 2
        calls = {c[0][0] for c in tracker.write_text.call_args_list}
        assert ".claude/skills/tracked-tree/SKILL.md" in calls
        assert ".claude/skills/tracked-tree/extra.md" in calls


# ---------------------------------------------------------------------------
# download_skills — full_tree fallback to skill_md_only
# ---------------------------------------------------------------------------


class TestFullTreeFallback:
    def test_falls_back_when_api_listing_fails_with_http_error(self, tmp_path):
        spec = _make_spec(download_mode="full_tree")

        http_error = urllib.error.HTTPError(
            url="https://api.github.com/repos/owner/repo/contents/skills/test-skill",
            code=404,
            msg="Not Found",
            hdrs=MagicMock(),
            fp=None,
        )

        call_count = 0

        def failing_then_succeeding(req, timeout=None):
            nonlocal call_count
            call_count += 1
            if "api.github.com" in req.full_url:
                raise http_error
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=failing_then_succeeding):
            report = download_skills([spec], tmp_path)

        assert "test-skill" in report.installed
        assert report.failed == []

    def test_falls_back_when_api_listing_fails_with_url_error(self, tmp_path):
        spec = _make_spec(download_mode="full_tree")
        url_error = urllib.error.URLError("network unreachable")

        def failing_then_succeeding(req, timeout=None):
            if "api.github.com" in req.full_url:
                raise url_error
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=failing_then_succeeding):
            report = download_skills([spec], tmp_path)

        assert "test-skill" in report.installed
        assert report.failed == []

    def test_fallback_writes_skill_md_to_correct_path(self, tmp_path):
        spec = _make_spec(name="fallback-skill", download_mode="full_tree")
        url_error = urllib.error.URLError("timeout")

        def failing_then_succeeding(req, timeout=None):
            if "api.github.com" in req.full_url:
                raise url_error
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=failing_then_succeeding):
            download_skills([spec], tmp_path)

        expected = tmp_path / ".claude" / "skills" / "fallback-skill" / "SKILL.md"
        assert expected.exists()
        assert expected.read_text() == _SKILL_MD_CONTENT

    def test_fallback_records_only_skill_md_in_all_files(self, tmp_path):
        spec = _make_spec(name="fallback-skill", download_mode="full_tree")
        url_error = urllib.error.URLError("timeout")

        def failing_then_succeeding(req, timeout=None):
            if "api.github.com" in req.full_url:
                raise url_error
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=failing_then_succeeding):
            report = download_skills([spec], tmp_path)

        assert report.all_files == [".claude/skills/fallback-skill/SKILL.md"]

    def test_full_tree_raises_when_skill_md_also_fails(self, tmp_path):
        """If API listing fails AND SKILL.md download fails, skill goes to failed."""
        spec = _make_spec(name="broken-skill", download_mode="full_tree")
        network_error = urllib.error.URLError("no network")

        with patch("urllib.request.urlopen", side_effect=network_error):
            report = download_skills([spec], tmp_path)

        assert "broken-skill" in report.failed_names
        assert report.installed == []


# ---------------------------------------------------------------------------
# download_skills — failure handling
# ---------------------------------------------------------------------------


class TestDownloadFailures:
    def test_failure_recorded_in_failed_not_installed(self, tmp_path):
        spec = _make_spec(name="bad-skill", download_mode="skill_md_only")
        error = urllib.error.HTTPError(
            url="https://raw.githubusercontent.com/owner/repo/main/skills/test-skill/SKILL.md",
            code=503,
            msg="Service Unavailable",
            hdrs=MagicMock(),
            fp=None,
        )

        with patch("urllib.request.urlopen", side_effect=error):
            report = download_skills([spec], tmp_path)

        assert "bad-skill" not in report.installed
        assert "bad-skill" in report.failed_names

    def test_failed_entry_contains_error_message(self, tmp_path):
        spec = _make_spec(name="bad-skill", download_mode="skill_md_only")
        error = urllib.error.URLError("connection refused")

        with patch("urllib.request.urlopen", side_effect=error):
            report = download_skills([spec], tmp_path)

        assert len(report.failed) == 1
        name, msg = report.failed[0]
        assert name == "bad-skill"
        assert "connection refused" in msg

    def test_timeout_error_recorded_in_failed(self, tmp_path):
        spec = _make_spec(name="slow-skill", download_mode="skill_md_only")
        error = TimeoutError("timed out")

        with patch("urllib.request.urlopen", side_effect=error):
            report = download_skills([spec], tmp_path)

        assert "slow-skill" in report.failed_names

    def test_generic_exception_recorded_in_failed(self, tmp_path):
        spec = _make_spec(name="exploding-skill", download_mode="skill_md_only")

        with patch("urllib.request.urlopen", side_effect=RuntimeError("unexpected")):
            report = download_skills([spec], tmp_path)

        assert "exploding-skill" in report.failed_names

    def test_no_file_written_on_failure(self, tmp_path):
        spec = _make_spec(name="fail-skill", download_mode="skill_md_only")

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("fail")):
            download_skills([spec], tmp_path)

        skill_dir = tmp_path / ".claude" / "skills" / "fail-skill"
        assert not skill_dir.exists()

    def test_full_tree_individual_file_failure_skipped_for_non_skill_md(self, tmp_path):
        """Non-SKILL.md file failures in full_tree mode are silently skipped."""
        spec = _make_spec(name="partial-skill", download_mode="full_tree")
        entries = [
            {"type": "file", "name": "SKILL.md", "path": "skills/partial-skill/SKILL.md"},
            {"type": "file", "name": "optional.md", "path": "skills/partial-skill/optional.md"},
        ]

        def selective_failure(req, timeout=None):
            if "api.github.com" in req.full_url:
                return _make_api_response(entries)
            if "optional.md" in req.full_url:
                raise urllib.error.URLError("404 Not Found")
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=selective_failure):
            report = download_skills([spec], tmp_path)

        # Skill succeeds overall even though optional.md failed
        assert "partial-skill" in report.installed
        assert "partial-skill" not in report.failed_names

    def test_full_tree_skill_md_failure_propagates(self, tmp_path):
        """SKILL.md failure in full_tree file loop should propagate to failed."""
        spec = _make_spec(name="no-skill-md", download_mode="full_tree")
        entries = [
            {"type": "file", "name": "SKILL.md", "path": "skills/no-skill-md/SKILL.md"},
        ]

        def always_fail_raw(req, timeout=None):
            if "api.github.com" in req.full_url:
                return _make_api_response(entries)
            raise urllib.error.HTTPError(
                url=req.full_url, code=404, msg="Not Found", hdrs=MagicMock(), fp=None
            )

        with patch("urllib.request.urlopen", side_effect=always_fail_raw):
            report = download_skills([spec], tmp_path)

        assert "no-skill-md" in report.failed_names
        assert "no-skill-md" not in report.installed


# ---------------------------------------------------------------------------
# download_skills — mixed success/failure
# ---------------------------------------------------------------------------


class TestMixedSuccessFailure:
    """Each spec gets a unique repo_path so URL-based matching is unambiguous."""

    @staticmethod
    def _make_named_spec(name: str, download_mode: str = "skill_md_only") -> SkillSpec:
        """Build a spec whose repo_path embeds the skill name so selective mocking works."""
        return _make_spec(
            name=name,
            repo="owner/repo",
            repo_path=f"skills/{name}",
            download_mode=download_mode,
        )

    def test_good_skills_installed_despite_failures(self, tmp_path):
        specs = [
            self._make_named_spec("good-skill"),
            self._make_named_spec("bad-skill"),
            self._make_named_spec("also-good"),
        ]

        def selective_failure(req, timeout=None):
            if "bad-skill" in req.full_url:
                raise urllib.error.URLError("network error")
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=selective_failure):
            report = download_skills(specs, tmp_path)

        assert "good-skill" in report.installed
        assert "also-good" in report.installed
        assert "bad-skill" not in report.installed
        assert "bad-skill" in report.failed_names

    def test_all_files_only_contains_successful_files(self, tmp_path):
        specs = [
            self._make_named_spec("ok-skill"),
            self._make_named_spec("err-skill"),
        ]

        def selective_failure(req, timeout=None):
            if "err-skill" in req.full_url:
                raise urllib.error.URLError("fail")
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=selective_failure):
            report = download_skills(specs, tmp_path)

        assert ".claude/skills/ok-skill/SKILL.md" in report.all_files
        assert not any("err-skill" in f for f in report.all_files)

    def test_failed_and_installed_counts_are_correct(self, tmp_path):
        specs = [self._make_named_spec(f"skill-{i}") for i in range(5)]
        failing_names = {"skill-1", "skill-3"}

        def selective_failure(req, timeout=None):
            for name in failing_names:
                if name in req.full_url:
                    raise urllib.error.URLError("fail")
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=selective_failure):
            report = download_skills(specs, tmp_path)

        assert len(report.installed) == 3
        assert len(report.failed) == 2
        assert report.failed_names == failing_names

    def test_later_failure_does_not_undo_earlier_success(self, tmp_path):
        specs = [
            self._make_named_spec("first-skill"),
            self._make_named_spec("second-skill"),
        ]

        def fail_second(req, timeout=None):
            if "second-skill" in req.full_url:
                raise urllib.error.URLError("second fails")
            return _make_url_response(_SKILL_MD_CONTENT)

        with patch("urllib.request.urlopen", side_effect=fail_second):
            report = download_skills(specs, tmp_path)

        first_file = tmp_path / ".claude" / "skills" / "first-skill" / "SKILL.md"
        assert first_file.exists()
        assert "first-skill" in report.installed


# ---------------------------------------------------------------------------
# _fetch_text — URL construction and behaviour
# ---------------------------------------------------------------------------


class TestFetchText:
    def test_returns_decoded_text(self):
        content = "hello, world"
        with patch("urllib.request.urlopen", return_value=_make_url_response(content)):
            result = _fetch_text("https://example.com/file.txt", timeout=5)
        assert result == content

    def test_passes_url_to_request(self):
        captured: list[urllib.request.Request] = []

        def capturing_urlopen(req, timeout=None):
            captured.append(req)
            return _make_url_response("ok")

        target_url = "https://raw.githubusercontent.com/owner/repo/main/skills/x/SKILL.md"
        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            _fetch_text(target_url, timeout=5)

        assert captured[0].full_url == target_url

    def test_passes_timeout_to_urlopen(self):
        captured_timeouts: list[int] = []

        def capturing_urlopen(req, timeout=None):
            captured_timeouts.append(timeout)
            return _make_url_response("ok")

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            _fetch_text("https://example.com/x", timeout=99)

        assert captured_timeouts == [99]

    def test_decodes_utf8_bytes(self):
        content = "Résumé with accents: \u00e9\u00e0\u00fc"
        with patch("urllib.request.urlopen", return_value=_make_url_response(content)):
            result = _fetch_text("https://example.com/x", timeout=5)
        assert result == content

    def test_propagates_http_error(self):
        error = urllib.error.HTTPError(
            url="https://example.com/x",
            code=404,
            msg="Not Found",
            hdrs=MagicMock(),
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(urllib.error.HTTPError):
                _fetch_text("https://example.com/x", timeout=5)

    def test_propagates_url_error(self):
        error = urllib.error.URLError("no route to host")
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(urllib.error.URLError):
                _fetch_text("https://example.com/x", timeout=5)


# ---------------------------------------------------------------------------
# _list_directory — URL construction and behaviour
# ---------------------------------------------------------------------------


class TestListDirectory:
    def test_returns_parsed_json_list(self):
        entries = [
            {"type": "file", "name": "SKILL.md"},
            {"type": "file", "name": "extra.md"},
        ]
        with patch("urllib.request.urlopen", return_value=_make_api_response(entries)):
            result = _list_directory("owner/repo", "skills/my-skill", timeout=10)

        assert result == entries

    def test_constructs_correct_api_url(self):
        entries = [{"type": "file", "name": "SKILL.md"}]
        captured: list[urllib.request.Request] = []

        def capturing_urlopen(req, timeout=None):
            captured.append(req)
            return _make_api_response(entries)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            _list_directory("myorg/myrepo", "skills/my-skill", timeout=5)

        assert captured[0].full_url == (
            "https://api.github.com/repos/myorg/myrepo/contents/skills/my-skill"
        )

    def test_accept_header_set_for_github_api(self):
        entries = [{"type": "file", "name": "SKILL.md"}]
        captured: list[urllib.request.Request] = []

        def capturing_urlopen(req, timeout=None):
            captured.append(req)
            return _make_api_response(entries)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            _list_directory("owner/repo", "skills/s", timeout=5)

        assert captured[0].get_header("Accept") == "application/vnd.github.v3+json"

    def test_user_agent_header_set(self):
        entries = [{"type": "file", "name": "SKILL.md"}]
        captured: list[urllib.request.Request] = []

        def capturing_urlopen(req, timeout=None):
            captured.append(req)
            return _make_api_response(entries)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            _list_directory("owner/repo", "skills/s", timeout=5)

        assert captured[0].get_header("User-agent") == "cc-rig"

    def test_passes_timeout_to_urlopen(self):
        entries = [{"type": "file", "name": "SKILL.md"}]
        captured_timeouts: list[int] = []

        def capturing_urlopen(req, timeout=None):
            captured_timeouts.append(timeout)
            return _make_api_response(entries)

        with patch("urllib.request.urlopen", side_effect=capturing_urlopen):
            _list_directory("owner/repo", "skills/s", timeout=77)

        assert captured_timeouts == [77]

    def test_propagates_http_error(self):
        error = urllib.error.HTTPError(
            url="https://api.github.com/repos/owner/repo/contents/skills/s",
            code=404,
            msg="Not Found",
            hdrs=MagicMock(),
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(urllib.error.HTTPError):
                _list_directory("owner/repo", "skills/s", timeout=5)
