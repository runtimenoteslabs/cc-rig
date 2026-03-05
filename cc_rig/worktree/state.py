"""Worktree state file management and PID utilities."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

STATE_FILENAME = "worktrees.json"


@dataclass
class WorktreeEntry:
    """One tracked worktree with its metadata."""

    name: str
    branch: str
    path: str
    task: str
    status: str = "running"  # running, done, failed, merged, pr-created, orphaned
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> WorktreeEntry:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class WorktreeState:
    """Container for all tracked worktrees, backed by a JSON file."""

    worktrees: List[WorktreeEntry] = field(default_factory=list)

    def get(self, name: str) -> Optional[WorktreeEntry]:
        """Look up a worktree by name."""
        for wt in self.worktrees:
            if wt.name == name:
                return wt
        return None

    def add(self, entry: WorktreeEntry) -> None:
        """Add a new worktree entry (replaces existing with same name)."""
        self.worktrees = [w for w in self.worktrees if w.name != entry.name]
        self.worktrees.append(entry)

    def remove(self, name: str) -> bool:
        """Remove a worktree entry by name. Returns True if found."""
        before = len(self.worktrees)
        self.worktrees = [w for w in self.worktrees if w.name != name]
        return len(self.worktrees) < before

    def to_dict(self) -> dict:
        return {"worktrees": [w.to_dict() for w in self.worktrees]}

    @classmethod
    def from_dict(cls, data: dict) -> WorktreeState:
        entries = [WorktreeEntry.from_dict(w) for w in data.get("worktrees", [])]
        return cls(worktrees=entries)


def state_file_path(project_dir: Path) -> Path:
    """Return the path to the worktrees state file."""
    return project_dir / ".claude" / STATE_FILENAME


def load_state(project_dir: Path) -> WorktreeState:
    """Load state from disk. Returns empty state if file missing or invalid."""
    path = state_file_path(project_dir)
    if not path.exists():
        return WorktreeState()
    try:
        data = json.loads(path.read_text())
        return WorktreeState.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return WorktreeState()


def save_state(project_dir: Path, state: WorktreeState) -> Path:
    """Write state to disk. Creates .claude/ directory if needed."""
    path = state_file_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2) + "\n")
    return path


def is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def get_exit_code(pid: int) -> Optional[int]:
    """Try to reap a finished child process and get its exit code.

    Returns None if the process is still running or not a child.
    """
    try:
        result_pid, status = os.waitpid(pid, os.WNOHANG)
        if result_pid == 0:
            return None  # still running
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status)
        if os.WIFSIGNALED(status):
            return 128 + os.WTERMSIG(status)
        return 1  # unknown termination
    except ChildProcessError:
        # Not our child — can't reap. Check if alive.
        if is_pid_alive(pid):
            return None
        return None  # gone but can't determine exit code


def refresh_entry_status(entry: WorktreeEntry) -> None:
    """Update a worktree entry's status based on PID liveness.

    Mutates the entry in place.
    """
    if entry.status not in ("running",):
        return  # terminal states are not refreshed

    if entry.pid is None:
        entry.status = "orphaned"
        return

    if is_pid_alive(entry.pid):
        return  # still running, no change

    # Process is gone
    exit_code = get_exit_code(entry.pid)
    if exit_code is not None:
        entry.exit_code = exit_code
        entry.status = "done" if exit_code == 0 else "failed"
    else:
        # Can't determine exit code — PID is gone
        entry.status = "orphaned"


def refresh_all(state: WorktreeState) -> None:
    """Refresh status of all running worktrees."""
    for entry in state.worktrees:
        refresh_entry_status(entry)


def slugify(text: str) -> str:
    """Convert a task description to a worktree-safe slug.

    >>> slugify("Fix auth bug")
    'fix-auth-bug'
    >>> slugify("  Add rate-limiting! ")
    'add-rate-limiting'
    """
    import re

    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "worktree"
