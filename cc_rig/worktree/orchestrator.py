"""Batch worktree spawning and status reporting."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from cc_rig.worktree import manager as _mgr
from cc_rig.worktree.state import (
    WorktreeEntry,
    load_state,
    refresh_all,
    refresh_entry_status,
    save_state,
    slugify,
)


def _find_claude_cli() -> Optional[str]:
    """Find the claude CLI executable."""
    return shutil.which("claude")


def _launch_claude(
    task: str,
    worktree_path: Path,
    output_file: Path,
) -> subprocess.Popen:
    """Launch a claude process in the worktree directory.

    Returns the Popen object.
    """
    return subprocess.Popen(
        [
            "claude",
            "-p", task,
            "--output-format", "json",
            "--dangerously-skip-permissions",
        ],
        cwd=worktree_path,
        stdout=output_file.open("w"),
        stderr=subprocess.STDOUT,
    )


def spawn_worktrees(
    project_dir: Path,
    tasks: List[str],
) -> Tuple[List[WorktreeEntry], List[Tuple[str, str]]]:
    """Create worktrees and launch Claude for each task.

    Returns (created_entries, failures) where failures is [(task, reason)].
    """
    if not _mgr.check_git_repo(project_dir):
        return [], [(t, "Not a git repository") for t in tasks]

    claude_path = _find_claude_cli()
    if not claude_path:
        return [], [(t, "claude CLI not found") for t in tasks]

    state = load_state(project_dir)
    created: List[WorktreeEntry] = []
    failures: List[Tuple[str, str]] = []

    for task in tasks:
        name = slugify(task)
        branch = f"wt/{name}"

        # Check for duplicate
        existing = state.get(name)
        if existing and existing.status == "running":
            failures.append((task, f"Worktree '{name}' is already running"))
            continue

        # Create the git worktree
        ok, msg = _mgr.create_worktree(project_dir, name, branch)
        if not ok:
            failures.append((task, msg))
            continue

        worktree_path = Path(msg)
        output_file = worktree_path / ".claude-output.json"

        # Launch claude
        try:
            proc = _launch_claude(task, worktree_path, output_file)
        except OSError as exc:
            failures.append((task, f"Failed to launch claude: {exc}"))
            continue

        entry = WorktreeEntry(
            name=name,
            branch=branch,
            path=str(worktree_path),
            task=task,
            status="running",
            pid=proc.pid,
        )
        state.add(entry)
        created.append(entry)

    save_state(project_dir, state)
    return created, failures


def list_worktrees(project_dir: Path) -> List[WorktreeEntry]:
    """List all tracked worktrees with refreshed status."""
    state = load_state(project_dir)
    refresh_all(state)
    save_state(project_dir, state)
    return state.worktrees


def get_worktree_status(
    project_dir: Path,
    name: str,
) -> Optional[WorktreeEntry]:
    """Get detailed status for a single worktree."""
    state = load_state(project_dir)
    entry = state.get(name)
    if entry is None:
        return None

    refresh_entry_status(entry)
    save_state(project_dir, state)
    return entry


def worktree_pr(
    project_dir: Path,
    name: str,
) -> Tuple[bool, str]:
    """Push the worktree branch and create a PR.

    Returns (success, url_or_error).
    """
    state = load_state(project_dir)
    entry = state.get(name)
    if entry is None:
        return False, f"No worktree found: {name}"

    if entry.status == "running":
        return False, (
            f"Worktree '{name}' is still running — wait for it to finish"
        )

    # Push the branch
    ok, msg = _mgr.push_branch(project_dir, entry.branch)
    if not ok:
        return False, msg

    # Create the PR
    body = (
        f"## Task\n\n{entry.task}\n\n"
        f"---\n"
        f"Created by `cc-rig worktree spawn`"
    )
    ok, result = _mgr.create_pr(
        project_dir, entry.branch, entry.task, body,
    )
    if not ok:
        return False, result

    entry.status = "pr-created"
    save_state(project_dir, state)
    return True, result


def cleanup_worktree(
    project_dir: Path,
    name: str,
    force: bool = False,
) -> Tuple[bool, str]:
    """Remove a single worktree and its branch.

    Returns (success, message).
    """
    state = load_state(project_dir)
    entry = state.get(name)
    if entry is None:
        return False, f"No worktree found: {name}"

    if entry.status == "running" and not force:
        return False, (
            f"Worktree '{name}' is still running — use --force or wait"
        )

    ok, msg = _mgr.remove_worktree(
        project_dir, name, entry.branch, force=force,
    )
    if not ok:
        return False, msg

    state.remove(name)
    save_state(project_dir, state)
    return True, msg


def cleanup_all(
    project_dir: Path,
    merged_only: bool = False,
    force: bool = False,
) -> List[Tuple[str, bool, str]]:
    """Clean up all (or merged-only) worktrees.

    Returns list of (name, success, message).
    """
    state = load_state(project_dir)
    refresh_all(state)
    results: List[Tuple[str, bool, str]] = []

    for entry in list(state.worktrees):
        if merged_only and entry.status != "merged":
            continue
        if entry.status == "running" and not force:
            results.append((entry.name, False, "Still running — skipped"))
            continue

        ok, msg = _mgr.remove_worktree(
            project_dir, entry.name, entry.branch, force=force,
        )
        if ok:
            state.remove(entry.name)
        results.append((entry.name, ok, msg))

    save_state(project_dir, state)
    return results
