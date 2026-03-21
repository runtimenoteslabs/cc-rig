"""Tests for cc_rig.worktree.manager — git worktree operations (mocked)."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from cc_rig.worktree.manager import (
    check_git_repo,
    create_pr,
    create_worktree,
    get_worktree_commits,
    list_worktree_branches,
    push_branch,
    remove_worktree,
)


@pytest.fixture
def mock_run():
    """Patch subprocess.run for git commands."""
    with patch("cc_rig.worktree.manager.subprocess.run") as m:
        yield m


class TestCheckGitRepo:
    def test_true_when_git_dir(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout=".git", stderr="")
        assert check_git_repo(tmp_path) is True
        mock_run.assert_called_once()

    def test_false_when_not_git(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess(
            [], 128, stdout="", stderr="not a git repo"
        )
        assert check_git_repo(tmp_path) is False


class TestCreateWorktree:
    def test_success(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        ok, msg = create_worktree(tmp_path, "fix-bug", "wt/fix-bug")
        assert ok is True
        assert "fix-bug" in msg

    def test_path_already_exists(self, tmp_path):
        wt_path = tmp_path / ".claude" / "worktrees" / "fix-bug"
        wt_path.mkdir(parents=True)
        ok, msg = create_worktree(tmp_path, "fix-bug", "wt/fix-bug")
        assert ok is False
        assert "already exists" in msg

    def test_git_failure(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess(
            [], 1, stdout="", stderr="branch already exists"
        )
        ok, msg = create_worktree(tmp_path, "new", "wt/new")
        assert ok is False
        assert "branch already exists" in msg


class TestRemoveWorktree:
    def test_success(self, mock_run, tmp_path):
        # First call: worktree remove, second: branch delete
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        wt_path = tmp_path / ".claude" / "worktrees" / "fix-bug"
        wt_path.mkdir(parents=True)

        ok, msg = remove_worktree(tmp_path, "fix-bug", "wt/fix-bug")
        assert ok is True

    def test_force_remove(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        wt_path = tmp_path / ".claude" / "worktrees" / "fix-bug"
        wt_path.mkdir(parents=True)

        ok, msg = remove_worktree(tmp_path, "fix-bug", "wt/fix-bug", force=True)
        assert ok is True
        # Check --force was passed to git worktree remove
        first_call = mock_run.call_args_list[0]
        assert "--force" in first_call[0][0]

    def test_git_worktree_remove_failure(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="is locked")
        wt_path = tmp_path / ".claude" / "worktrees" / "fix-bug"
        wt_path.mkdir(parents=True)

        ok, msg = remove_worktree(tmp_path, "fix-bug", "wt/fix-bug")
        assert ok is False
        assert "is locked" in msg

    def test_branch_delete_failure_nonfatal(self, mock_run, tmp_path):
        # worktree remove succeeds, branch delete fails
        def side_effect(args, **kwargs):
            if "worktree" in args:
                return subprocess.CompletedProcess([], 0, stdout="", stderr="")
            return subprocess.CompletedProcess([], 1, stdout="", stderr="not merged")

        mock_run.side_effect = side_effect
        wt_path = tmp_path / ".claude" / "worktrees" / "fix-bug"
        wt_path.mkdir(parents=True)

        ok, msg = remove_worktree(tmp_path, "fix-bug", "wt/fix-bug")
        assert ok is True
        assert "branch deletion failed" in msg

    def test_remove_nonexistent_path(self, mock_run, tmp_path):
        """When path doesn't exist, skip worktree remove and go to branch delete."""
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        ok, msg = remove_worktree(tmp_path, "gone", "wt/gone")
        assert ok is True
        # Only branch delete should be called (no worktree remove since path doesn't exist)
        assert mock_run.call_count == 1


class TestListWorktreeBranches:
    def test_parses_porcelain_output(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess(
            [],
            0,
            stdout="worktree /home/user/project\nHEAD abc123\nbranch refs/heads/main\n\n"
            "worktree /home/user/project/.claude/worktrees/fix-bug\nHEAD def456\n"
            "branch refs/heads/wt/fix-bug\n",
            stderr="",
        )
        paths = list_worktree_branches(tmp_path)
        assert len(paths) == 2
        assert "/home/user/project" in paths[0]

    def test_empty_on_failure(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="error")
        assert list_worktree_branches(tmp_path) == []


class TestGetWorktreeCommits:
    def test_commits_since_divergence(self, mock_run, tmp_path):
        def side_effect(args, **kwargs):
            if "merge-base" in args:
                return subprocess.CompletedProcess([], 0, stdout="abc123\n", stderr="")
            return subprocess.CompletedProcess(
                [], 0, stdout="def456 Add feature\nghi789 Fix test\n", stderr=""
            )

        mock_run.side_effect = side_effect
        commits = get_worktree_commits(tmp_path, "wt/fix-bug")
        assert len(commits) == 2
        assert "Add feature" in commits[0]

    def test_fallback_on_merge_base_failure(self, mock_run, tmp_path):
        def side_effect(args, **kwargs):
            if "merge-base" in args:
                return subprocess.CompletedProcess([], 1, stdout="", stderr="error")
            return subprocess.CompletedProcess([], 0, stdout="abc Fix\n", stderr="")

        mock_run.side_effect = side_effect
        commits = get_worktree_commits(tmp_path, "wt/x")
        assert len(commits) == 1


class TestPushBranch:
    def test_success(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        ok, msg = push_branch(tmp_path, "wt/fix-bug")
        assert ok is True

    def test_failure(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess(
            [], 1, stdout="", stderr="permission denied"
        )
        ok, msg = push_branch(tmp_path, "wt/fix-bug")
        assert ok is False
        assert "permission denied" in msg


class TestCreatePR:
    def test_gh_not_found(self, tmp_path):
        with patch("cc_rig.worktree.manager.shutil.which", return_value=None):
            ok, msg = create_pr(tmp_path, "wt/x", "title", "body")
            assert ok is False
            assert "gh CLI not found" in msg

    def test_success(self, tmp_path):
        with patch("cc_rig.worktree.manager.shutil.which", return_value="/usr/bin/gh"):
            with patch("cc_rig.worktree.manager.subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    [], 0, stdout="https://github.com/user/repo/pull/1", stderr=""
                )
                ok, url = create_pr(tmp_path, "wt/x", "Fix bug", "details")
                assert ok is True
                assert "pull/1" in url

    def test_failure(self, tmp_path):
        with patch("cc_rig.worktree.manager.shutil.which", return_value="/usr/bin/gh"):
            with patch("cc_rig.worktree.manager.subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    [], 1, stdout="", stderr="auth required"
                )
                ok, msg = create_pr(tmp_path, "wt/x", "Fix", "body")
                assert ok is False
                assert "auth required" in msg
