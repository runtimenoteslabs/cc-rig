"""Git worktree operations: create, remove, list, create PR."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


def _run_git(args: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def check_git_repo(project_dir: Path) -> bool:
    """Check if the directory is inside a git repository."""
    result = _run_git(["rev-parse", "--git-dir"], cwd=project_dir)
    return result.returncode == 0


def create_worktree(
    project_dir: Path,
    name: str,
    branch: str,
) -> Tuple[bool, str]:
    """Create a git worktree with a new branch.

    Returns (success, message).
    """
    worktree_path = project_dir / ".claude" / "worktrees" / name

    if worktree_path.exists():
        return False, f"Worktree path already exists: {worktree_path}"

    # Create parent directory
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    result = _run_git(
        ["worktree", "add", str(worktree_path), "-b", branch],
        cwd=project_dir,
    )

    if result.returncode != 0:
        return False, f"git worktree add failed: {result.stderr.strip()}"

    return True, str(worktree_path)


def remove_worktree(
    project_dir: Path,
    name: str,
    branch: str,
    force: bool = False,
) -> Tuple[bool, str]:
    """Remove a git worktree and optionally its branch.

    Returns (success, message).
    """
    worktree_path = project_dir / ".claude" / "worktrees" / name

    # Remove the worktree
    if worktree_path.exists():
        result = _run_git(
            ["worktree", "remove", str(worktree_path), "--force"]
            if force
            else ["worktree", "remove", str(worktree_path)],
            cwd=project_dir,
        )
        if result.returncode != 0:
            return False, f"git worktree remove failed: {result.stderr.strip()}"

    # Delete the branch
    flag = "-D" if force else "-d"
    result = _run_git(["branch", flag, branch], cwd=project_dir)
    if result.returncode != 0:
        # Branch deletion failure is non-fatal
        return True, f"Worktree removed, but branch deletion failed: {result.stderr.strip()}"

    return True, f"Removed worktree and branch: {name}"


def list_worktree_branches(project_dir: Path) -> List[str]:
    """List all git worktree paths currently registered."""
    result = _run_git(["worktree", "list", "--porcelain"], cwd=project_dir)
    if result.returncode != 0:
        return []
    paths = []
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            paths.append(line[len("worktree "):])
    return paths


def get_worktree_commits(
    project_dir: Path,
    branch: str,
    max_count: int = 10,
) -> List[str]:
    """Get oneline log of commits on a branch since it diverged from HEAD.

    Returns list of "hash subject" strings.
    """
    # Find the merge base between the worktree branch and HEAD
    merge_base = _run_git(
        ["merge-base", "HEAD", branch],
        cwd=project_dir,
    )
    if merge_base.returncode != 0:
        # Fallback: just show last N commits on the branch
        result = _run_git(
            ["log", "--oneline", f"-{max_count}", branch],
            cwd=project_dir,
        )
        return result.stdout.strip().splitlines() if result.returncode == 0 else []

    base = merge_base.stdout.strip()
    result = _run_git(
        ["log", "--oneline", f"-{max_count}", f"{base}..{branch}"],
        cwd=project_dir,
    )
    return result.stdout.strip().splitlines() if result.returncode == 0 else []


def push_branch(project_dir: Path, branch: str) -> Tuple[bool, str]:
    """Push a branch to the remote. Returns (success, message)."""
    result = _run_git(
        ["push", "-u", "origin", branch],
        cwd=project_dir,
    )
    if result.returncode != 0:
        return False, f"git push failed: {result.stderr.strip()}"
    return True, "Pushed to remote"


def create_pr(
    project_dir: Path,
    branch: str,
    title: str,
    body: str,
) -> Tuple[bool, str]:
    """Create a GitHub PR using `gh`. Returns (success, url_or_error)."""
    if not shutil.which("gh"):
        return False, "gh CLI not found. Install it from https://cli.github.com/"

    result = subprocess.run(
        [
            "gh", "pr", "create",
            "--head", branch,
            "--title", title,
            "--body", body,
        ],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, f"gh pr create failed: {result.stderr.strip()}"
    return True, result.stdout.strip()
