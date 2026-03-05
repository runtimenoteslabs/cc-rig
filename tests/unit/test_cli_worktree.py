"""Tests for CLI worktree subcommand arg parsing and dispatch."""

from __future__ import annotations

from unittest.mock import patch

from cc_rig.cli import build_parser, main


class TestWorktreeArgParsing:
    def test_spawn_single_task(self):
        parser = build_parser()
        args = parser.parse_args(["worktree", "spawn", "Fix auth bug"])
        assert args.command == "worktree"
        assert args.worktree_command == "spawn"
        assert args.tasks == ["Fix auth bug"]

    def test_spawn_multiple_tasks(self):
        parser = build_parser()
        args = parser.parse_args([
            "worktree", "spawn", "Fix auth bug", "Add rate limiting"
        ])
        assert args.tasks == ["Fix auth bug", "Add rate limiting"]

    def test_spawn_with_dir(self):
        parser = build_parser()
        args = parser.parse_args(["worktree", "spawn", "-d", "/tmp/proj", "Fix it"])
        assert args.dir == "/tmp/proj"
        assert args.tasks == ["Fix it"]

    def test_list(self):
        parser = build_parser()
        args = parser.parse_args(["worktree", "list"])
        assert args.worktree_command == "list"

    def test_status(self):
        parser = build_parser()
        args = parser.parse_args(["worktree", "status", "fix-bug"])
        assert args.worktree_command == "status"
        assert args.name == "fix-bug"

    def test_pr(self):
        parser = build_parser()
        args = parser.parse_args(["worktree", "pr", "fix-bug"])
        assert args.worktree_command == "pr"
        assert args.name == "fix-bug"

    def test_cleanup_single(self):
        parser = build_parser()
        args = parser.parse_args(["worktree", "cleanup", "fix-bug"])
        assert args.worktree_command == "cleanup"
        assert args.name == "fix-bug"
        assert args.all is False

    def test_cleanup_all(self):
        parser = build_parser()
        args = parser.parse_args(["worktree", "cleanup", "--all"])
        assert args.all is True

    def test_cleanup_merged(self):
        parser = build_parser()
        args = parser.parse_args(["worktree", "cleanup", "--merged"])
        assert args.merged is True

    def test_cleanup_force(self):
        parser = build_parser()
        args = parser.parse_args(["worktree", "cleanup", "--force", "x"])
        assert args.force is True


class TestWorktreeDispatch:
    def test_no_subcommand_shows_usage(self, capsys):
        rc = main(["worktree"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "spawn" in out or "Usage" in out

    def test_spawn_dispatch(self, tmp_path):
        with patch("cc_rig.worktree.orchestrator.spawn_worktrees") as mock_spawn:
            from cc_rig.worktree.state import WorktreeEntry
            entry = WorktreeEntry(
                name="fix-bug", branch="wt/fix-bug",
                path=str(tmp_path), task="Fix bug", pid=123,
            )
            mock_spawn.return_value = ([entry], [])
            rc = main([
                "worktree", "spawn", "-d", str(tmp_path), "Fix bug"
            ])
            assert rc == 0
            mock_spawn.assert_called_once()

    def test_list_dispatch(self, tmp_path):
        with patch("cc_rig.worktree.orchestrator.list_worktrees", return_value=[]):
            rc = main(["worktree", "list", "-d", str(tmp_path)])
            assert rc == 0

    def test_status_dispatch(self, tmp_path):
        with patch("cc_rig.worktree.orchestrator.get_worktree_status", return_value=None):
            rc = main(["worktree", "status", "-d", str(tmp_path), "nope"])
            assert rc == 1

    def test_pr_dispatch(self, tmp_path):
        with patch("cc_rig.worktree.orchestrator.worktree_pr",
                   return_value=(True, "https://github.com/x/pull/1")):
            rc = main(["worktree", "pr", "-d", str(tmp_path), "fix-bug"])
            assert rc == 0

    def test_cleanup_dispatch(self, tmp_path):
        with patch("cc_rig.worktree.orchestrator.cleanup_worktree",
                   return_value=(True, "Removed")):
            rc = main(["worktree", "cleanup", "-d", str(tmp_path), "fix-bug"])
            assert rc == 0

    def test_cleanup_all_dispatch(self, tmp_path):
        with patch("cc_rig.worktree.orchestrator.cleanup_all", return_value=[]):
            rc = main(["worktree", "cleanup", "--all", "-d", str(tmp_path)])
            assert rc == 0

    def test_spawn_all_failures(self, tmp_path):
        with patch("cc_rig.worktree.orchestrator.spawn_worktrees") as mock_spawn:
            mock_spawn.return_value = ([], [("Fix bug", "not a git repo")])
            rc = main([
                "worktree", "spawn", "-d", str(tmp_path), "Fix bug"
            ])
            assert rc == 1

    def test_spawn_partial_success(self, tmp_path):
        """When some succeed and some fail, return 0."""
        with patch("cc_rig.worktree.orchestrator.spawn_worktrees") as mock_spawn:
            from cc_rig.worktree.state import WorktreeEntry
            entry = WorktreeEntry(
                name="ok", branch="wt/ok",
                path=str(tmp_path), task="Ok task", pid=1,
            )
            mock_spawn.return_value = ([entry], [("bad", "error")])
            rc = main([
                "worktree", "spawn", "-d", str(tmp_path), "Ok task", "bad"
            ])
            assert rc == 0
