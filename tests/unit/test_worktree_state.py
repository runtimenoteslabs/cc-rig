"""Tests for cc_rig.worktree.state — dataclass, serialization, PID utils."""

from __future__ import annotations

import json

import pytest

from cc_rig.worktree.state import (
    WorktreeEntry,
    WorktreeState,
    is_pid_alive,
    load_state,
    refresh_all,
    refresh_entry_status,
    save_state,
    slugify,
    state_file_path,
)


class TestWorktreeEntry:
    def test_defaults(self):
        entry = WorktreeEntry(
            name="fix-bug",
            branch="wt/fix-bug",
            path=".claude/worktrees/fix-bug",
            task="Fix the bug",
        )
        assert entry.status == "running"
        assert entry.pid is None
        assert entry.exit_code is None
        assert entry.created_at  # non-empty

    def test_to_dict_roundtrip(self):
        entry = WorktreeEntry(
            name="add-feature",
            branch="wt/add-feature",
            path="/tmp/wt/add-feature",
            task="Add rate limiting",
            status="done",
            pid=12345,
            exit_code=0,
            created_at="2026-03-06T10:30:00+00:00",
        )
        d = entry.to_dict()
        restored = WorktreeEntry.from_dict(d)
        assert restored.name == entry.name
        assert restored.branch == entry.branch
        assert restored.status == "done"
        assert restored.pid == 12345
        assert restored.exit_code == 0

    def test_from_dict_ignores_extra_keys(self):
        data = {
            "name": "test",
            "branch": "wt/test",
            "path": "/tmp/test",
            "task": "test task",
            "unknown_field": "ignored",
        }
        entry = WorktreeEntry.from_dict(data)
        assert entry.name == "test"

    def test_from_dict_minimal(self):
        data = {
            "name": "x",
            "branch": "wt/x",
            "path": "/tmp/x",
            "task": "do x",
        }
        entry = WorktreeEntry.from_dict(data)
        assert entry.status == "running"


class TestWorktreeState:
    def test_empty_state(self):
        state = WorktreeState()
        assert state.worktrees == []
        assert state.get("anything") is None

    def test_add_and_get(self):
        state = WorktreeState()
        entry = WorktreeEntry(
            name="foo", branch="wt/foo", path="/tmp/foo", task="do foo"
        )
        state.add(entry)
        assert state.get("foo") is entry
        assert len(state.worktrees) == 1

    def test_add_replaces_same_name(self):
        state = WorktreeState()
        e1 = WorktreeEntry(
            name="foo", branch="wt/foo", path="/tmp/foo", task="v1"
        )
        e2 = WorktreeEntry(
            name="foo", branch="wt/foo", path="/tmp/foo", task="v2"
        )
        state.add(e1)
        state.add(e2)
        assert len(state.worktrees) == 1
        assert state.get("foo").task == "v2"

    def test_remove(self):
        state = WorktreeState()
        state.add(
            WorktreeEntry(name="a", branch="wt/a", path="/a", task="a")
        )
        state.add(
            WorktreeEntry(name="b", branch="wt/b", path="/b", task="b")
        )
        assert state.remove("a") is True
        assert state.get("a") is None
        assert len(state.worktrees) == 1

    def test_remove_nonexistent(self):
        state = WorktreeState()
        assert state.remove("nope") is False

    def test_to_dict_from_dict_roundtrip(self):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="x", branch="wt/x", path="/x", task="task x", status="done"
            )
        )
        state.add(
            WorktreeEntry(
                name="y", branch="wt/y", path="/y", task="task y", status="running"
            )
        )
        d = state.to_dict()
        restored = WorktreeState.from_dict(d)
        assert len(restored.worktrees) == 2
        assert restored.get("x").status == "done"
        assert restored.get("y").status == "running"


class TestStateFileIO:
    def test_state_file_path(self, tmp_path):
        path = state_file_path(tmp_path)
        assert path == tmp_path / ".claude" / "worktrees.json"

    def test_load_missing_file(self, tmp_path):
        state = load_state(tmp_path)
        assert state.worktrees == []

    def test_load_invalid_json(self, tmp_path):
        sf = tmp_path / ".claude" / "worktrees.json"
        sf.parent.mkdir(parents=True)
        sf.write_text("not json!")
        state = load_state(tmp_path)
        assert state.worktrees == []

    def test_save_and_load_roundtrip(self, tmp_path):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="test", branch="wt/test", path="/test", task="do test"
            )
        )
        save_state(tmp_path, state)
        loaded = load_state(tmp_path)
        assert len(loaded.worktrees) == 1
        assert loaded.get("test").task == "do test"

    def test_save_creates_directory(self, tmp_path):
        state = WorktreeState()
        save_state(tmp_path, state)
        assert (tmp_path / ".claude" / "worktrees.json").exists()

    def test_saved_file_is_valid_json(self, tmp_path):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="x", branch="wt/x", path="/x", task="t"
            )
        )
        path = save_state(tmp_path, state)
        data = json.loads(path.read_text())
        assert "worktrees" in data
        assert len(data["worktrees"]) == 1


class TestPIDUtils:
    def test_is_pid_alive_current_process(self):
        import os
        assert is_pid_alive(os.getpid()) is True

    def test_is_pid_alive_nonexistent(self):
        # PID 99999999 almost certainly doesn't exist
        assert is_pid_alive(99999999) is False


class TestRefreshStatus:
    def test_running_with_dead_pid(self):
        entry = WorktreeEntry(
            name="x", branch="wt/x", path="/x", task="t",
            status="running", pid=99999999,
        )
        refresh_entry_status(entry)
        assert entry.status in ("done", "failed", "orphaned")

    def test_running_with_no_pid(self):
        entry = WorktreeEntry(
            name="x", branch="wt/x", path="/x", task="t",
            status="running", pid=None,
        )
        refresh_entry_status(entry)
        assert entry.status == "orphaned"

    def test_terminal_status_not_changed(self):
        for status in ("done", "failed", "merged", "pr-created"):
            entry = WorktreeEntry(
                name="x", branch="wt/x", path="/x", task="t",
                status=status, pid=99999999,
            )
            refresh_entry_status(entry)
            assert entry.status == status

    def test_running_with_alive_pid(self):
        import os
        entry = WorktreeEntry(
            name="x", branch="wt/x", path="/x", task="t",
            status="running", pid=os.getpid(),
        )
        refresh_entry_status(entry)
        assert entry.status == "running"

    def test_refresh_all(self):
        state = WorktreeState()
        state.add(
            WorktreeEntry(
                name="a", branch="wt/a", path="/a", task="a",
                status="running", pid=99999999,
            )
        )
        state.add(
            WorktreeEntry(
                name="b", branch="wt/b", path="/b", task="b",
                status="done", pid=1,
            )
        )
        refresh_all(state)
        assert state.get("a").status in ("done", "failed", "orphaned")
        assert state.get("b").status == "done"  # unchanged


class TestSlugify:
    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("Fix auth bug", "fix-auth-bug"),
            ("  Add rate-limiting! ", "add-rate-limiting"),
            ("Hello World", "hello-world"),
            ("a/b/c", "a-b-c"),
            ("UPPER case", "upper-case"),
            ("   ", "worktree"),
            ("", "worktree"),
            ("simple", "simple"),
            ("a--b", "a-b"),
            ("feat: add login", "feat-add-login"),
        ],
    )
    def test_slugify(self, input_text, expected):
        assert slugify(input_text) == expected
