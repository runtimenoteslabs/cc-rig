"""Tests for cc_rig.worktree.orchestrator — batch spawn, status, cleanup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cc_rig.worktree.orchestrator import (
    cleanup_all,
    cleanup_worktree,
    get_worktree_status,
    list_worktrees,
    spawn_worktrees,
    worktree_pr,
)
from cc_rig.worktree.state import (
    WorktreeEntry,
    WorktreeState,
    load_state,
    save_state,
)

_O = "cc_rig.worktree.orchestrator"  # orchestrator-local names
_M = "cc_rig.worktree.manager"  # manager functions (via _mgr)


@pytest.fixture
def git_project(tmp_path):
    """Set up a minimal git repo."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    return tmp_path


class TestSpawnWorktrees:
    def test_not_a_git_repo(self, tmp_path):
        created, failures = spawn_worktrees(tmp_path, ["Fix bug"])
        assert created == []
        assert len(failures) == 1
        assert "Not a git repository" in failures[0][1]

    def test_claude_not_found(self, tmp_path):
        with (
            patch(f"{_M}.check_git_repo", return_value=True),
            patch(f"{_O}._find_claude_cli", return_value=None),
        ):
            created, failures = spawn_worktrees(tmp_path, ["Fix bug"])
            assert created == []
            assert "claude CLI not found" in failures[0][1]

    def test_spawn_success(self, git_project):
        mock_proc = MagicMock()
        mock_proc.pid = 12345

        with (
            patch(f"{_M}.check_git_repo", return_value=True),
            patch(f"{_O}._find_claude_cli", return_value="/usr/bin/claude"),
            patch(f"{_M}.create_worktree") as mock_create,
            patch(f"{_O}._launch_claude", return_value=mock_proc),
        ):
            wt_path = git_project / ".claude" / "worktrees" / "fix-bug"
            mock_create.return_value = (True, str(wt_path))

            created, failures = spawn_worktrees(
                git_project,
                ["Fix bug"],
            )
            assert len(created) == 1
            assert created[0].name == "fix-bug"
            assert created[0].pid == 12345
            assert failures == []

            # State should be saved
            state = load_state(git_project)
            assert state.get("fix-bug") is not None

    def test_spawn_multiple(self, git_project):
        mock_proc = MagicMock()
        mock_proc.pid = 100

        with (
            patch(f"{_M}.check_git_repo", return_value=True),
            patch(f"{_O}._find_claude_cli", return_value="/usr/bin/claude"),
            patch(f"{_M}.create_worktree") as mock_create,
            patch(f"{_O}._launch_claude", return_value=mock_proc),
        ):

            def create_side_effect(project_dir, name, branch):
                path = project_dir / ".claude" / "worktrees" / name
                return True, str(path)

            mock_create.side_effect = create_side_effect

            created, failures = spawn_worktrees(
                git_project,
                ["Fix bug", "Add feature"],
            )
            assert len(created) == 2
            assert failures == []

    def test_spawn_duplicate_running(self, git_project):
        # Pre-populate state with a running worktree
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="fix-bug",
                branch="wt/fix-bug",
                path="/x",
                task="old",
                status="running",
                pid=99999,
            )
        )
        save_state(git_project, state)

        with (
            patch(f"{_M}.check_git_repo", return_value=True),
            patch(f"{_O}._find_claude_cli", return_value="/usr/bin/claude"),
        ):
            created, failures = spawn_worktrees(
                git_project,
                ["Fix bug"],
            )
            assert created == []
            assert len(failures) == 1
            assert "already running" in failures[0][1]

    def test_spawn_git_failure(self, git_project):
        with (
            patch(f"{_M}.check_git_repo", return_value=True),
            patch(f"{_O}._find_claude_cli", return_value="/usr/bin/claude"),
            patch(f"{_M}.create_worktree", return_value=(False, "branch exists")),
        ):
            created, failures = spawn_worktrees(
                git_project,
                ["Fix bug"],
            )
            assert created == []
            assert "branch exists" in failures[0][1]


class TestListWorktrees:
    def test_empty_state(self, git_project):
        entries = list_worktrees(git_project)
        assert entries == []

    def test_returns_entries(self, git_project):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="a",
                branch="wt/a",
                path="/a",
                task="task a",
                status="done",
            )
        )
        save_state(git_project, state)

        entries = list_worktrees(git_project)
        assert len(entries) == 1
        assert entries[0].name == "a"


class TestGetWorktreeStatus:
    def test_found(self, git_project):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="x",
                branch="wt/x",
                path="/x",
                task="do x",
                status="done",
            )
        )
        save_state(git_project, state)

        entry = get_worktree_status(git_project, "x")
        assert entry is not None
        assert entry.task == "do x"

    def test_not_found(self, git_project):
        assert get_worktree_status(git_project, "nope") is None


class TestWorktreePR:
    def test_not_found(self, git_project):
        ok, msg = worktree_pr(git_project, "nope")
        assert ok is False
        assert "No worktree found" in msg

    def test_still_running(self, git_project):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="x",
                branch="wt/x",
                path="/x",
                task="t",
                status="running",
            )
        )
        save_state(git_project, state)

        ok, msg = worktree_pr(git_project, "x")
        assert ok is False
        assert "still running" in msg

    def test_success(self, git_project):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="x",
                branch="wt/x",
                path="/x",
                task="Fix login",
                status="done",
            )
        )
        save_state(git_project, state)

        with (
            patch(f"{_M}.push_branch", return_value=(True, "ok")),
            patch(f"{_M}.create_pr", return_value=(True, "https://github.com/u/r/pull/1")),
        ):
            ok, url = worktree_pr(git_project, "x")
            assert ok is True
            assert "pull/1" in url

            # Status should be updated
            state = load_state(git_project)
            assert state.get("x").status == "pr-created"

    def test_push_failure(self, git_project):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="x",
                branch="wt/x",
                path="/x",
                task="t",
                status="done",
            )
        )
        save_state(git_project, state)

        with patch(f"{_M}.push_branch", return_value=(False, "auth error")):
            ok, msg = worktree_pr(git_project, "x")
            assert ok is False
            assert "auth error" in msg


class TestCleanupWorktree:
    def test_not_found(self, git_project):
        ok, msg = cleanup_worktree(git_project, "nope")
        assert ok is False

    def test_still_running_no_force(self, git_project):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="x",
                branch="wt/x",
                path="/x",
                task="t",
                status="running",
            )
        )
        save_state(git_project, state)

        ok, msg = cleanup_worktree(git_project, "x")
        assert ok is False
        assert "still running" in msg

    def test_success(self, git_project):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="x",
                branch="wt/x",
                path="/x",
                task="t",
                status="done",
            )
        )
        save_state(git_project, state)

        with patch(f"{_M}.remove_worktree", return_value=(True, "Removed")):
            ok, msg = cleanup_worktree(git_project, "x")
            assert ok is True

            # Should be removed from state
            state = load_state(git_project)
            assert state.get("x") is None

    def test_force_running(self, git_project):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="x",
                branch="wt/x",
                path="/x",
                task="t",
                status="running",
            )
        )
        save_state(git_project, state)

        with patch(f"{_M}.remove_worktree", return_value=(True, "Force removed")):
            ok, msg = cleanup_worktree(git_project, "x", force=True)
            assert ok is True


class TestCleanupAll:
    def test_empty(self, git_project):
        results = cleanup_all(git_project)
        assert results == []

    def test_cleans_non_running(self, git_project):
        import os

        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="a",
                branch="wt/a",
                path="/a",
                task="a",
                status="done",
            )
        )
        # Use current PID so refresh_all sees it as still alive
        state.add(
            WorktreeEntry(
                name="b",
                branch="wt/b",
                path="/b",
                task="b",
                status="running",
                pid=os.getpid(),
            )
        )
        save_state(git_project, state)

        with patch(f"{_M}.remove_worktree", return_value=(True, "Removed")):
            results = cleanup_all(git_project)
            assert len(results) == 2
            # 'a' cleaned, 'b' skipped (still running)
            assert results[0][1] is True  # a succeeded
            assert results[1][1] is False  # b skipped (running)

    def test_merged_only(self, git_project):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="a",
                branch="wt/a",
                path="/a",
                task="a",
                status="merged",
            )
        )
        state.add(
            WorktreeEntry(
                name="b",
                branch="wt/b",
                path="/b",
                task="b",
                status="done",
            )
        )
        save_state(git_project, state)

        with patch(f"{_M}.remove_worktree", return_value=(True, "Removed")):
            results = cleanup_all(git_project, merged_only=True)
            assert len(results) == 1
            assert results[0][0] == "a"
