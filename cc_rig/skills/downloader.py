"""Download community skills from GitHub into .claude/skills/.

Uses only stdlib (urllib.request). No external dependencies.
On failure: skip and record in report. Offline fallback handled by caller.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from cc_rig.generators.fileops import FileTracker
from cc_rig.skills.registry import SkillSpec

# GitHub raw content URL pattern
_RAW_URL = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"

# GitHub Contents API URL pattern (for directory listing)
_API_URL = "https://api.github.com/repos/{repo}/contents/{path}"

# Default timeout per request
_TIMEOUT = 10


@dataclass
class SkillInstallReport:
    """Report of skill installation results."""

    installed: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)  # (name, error)

    @property
    def failed_names(self) -> set[str]:
        return {name for name, _ in self.failed}

    @property
    def all_files(self) -> list[str]:
        """Return all relative file paths that were written."""
        return list(self._files)

    def _add_file(self, rel_path: str) -> None:
        if not hasattr(self, "_files"):
            object.__setattr__(self, "_files", [])
        self._files.append(rel_path)


def download_skills(
    specs: list[SkillSpec],
    output_dir: Path,
    tracker: FileTracker | None = None,
    timeout: int = _TIMEOUT,
) -> SkillInstallReport:
    """Download community skills into .claude/skills/.

    Args:
        specs: List of skills to download.
        output_dir: Project root directory.
        tracker: FileTracker for manifest recording.
        timeout: Timeout per HTTP request in seconds.

    Returns:
        SkillInstallReport with installed/failed lists.

    Set CC_RIG_OFFLINE=1 to skip all downloads (useful for CI/demos).
    """
    report = SkillInstallReport()

    if os.environ.get("CC_RIG_OFFLINE"):
        object.__setattr__(report, "_files", [])
        for spec in specs:
            report.failed.append((spec.name, "offline mode"))
        return report
    # Initialize the internal files list
    object.__setattr__(report, "_files", [])

    for spec in specs:
        try:
            if spec.download_mode == "full_tree":
                files = _download_full_tree(spec, output_dir, tracker, timeout)
            else:
                files = _download_skill_md_only(spec, output_dir, tracker, timeout)
            report.installed.append(spec.name)
            for f in files:
                report._add_file(f)
        except Exception as exc:
            report.failed.append((spec.name, str(exc)))

    return report


def _download_skill_md_only(
    spec: SkillSpec,
    output_dir: Path,
    tracker: FileTracker | None,
    timeout: int,
) -> list[str]:
    """Download just SKILL.md via raw.githubusercontent.com."""
    url = _RAW_URL.format(repo=spec.repo, branch=spec.branch, path=f"{spec.repo_path}/SKILL.md")
    content = _fetch_text(url, timeout)

    rel = f".claude/skills/{spec.name}/SKILL.md"
    if tracker is not None:
        tracker.write_text(rel, content)
    else:
        path = output_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    return [rel]


def _download_full_tree(
    spec: SkillSpec,
    output_dir: Path,
    tracker: FileTracker | None,
    timeout: int,
) -> list[str]:
    """Download SKILL.md + companion files using GitHub Contents API."""
    files_written: list[str] = []

    # First try to list directory contents via API
    try:
        entries = _list_directory(spec.repo, spec.repo_path, timeout)
    except Exception:
        # Fallback: just download SKILL.md
        return _download_skill_md_only(spec, output_dir, tracker, timeout)

    # Download files recursively (handles subdirectories like scripts/, templates/)
    _download_tree_entries(
        entries=entries,
        spec=spec,
        repo_prefix=spec.repo_path,
        install_prefix=f".claude/skills/{spec.name}",
        output_dir=output_dir,
        tracker=tracker,
        timeout=timeout,
        files_written=files_written,
        depth=0,
    )

    return files_written


def _download_tree_entries(
    entries: list[dict],
    spec: SkillSpec,
    repo_prefix: str,
    install_prefix: str,
    output_dir: Path,
    tracker: FileTracker | None,
    timeout: int,
    files_written: list[str],
    depth: int,
) -> None:
    """Recursively download files from a directory listing.

    Args:
        entries: GitHub Contents API directory listing.
        spec: Skill spec (for repo/branch info).
        repo_prefix: Current repo path prefix (e.g. "skills/planning-with-files").
        install_prefix: Current install path prefix (e.g. ".claude/skills/planning-with-files").
        depth: Recursion depth (capped at 3 to prevent runaway).
    """
    for entry in entries:
        name = entry.get("name", "")
        # Guard against path traversal
        if "/" in name or "\\" in name or ".." in name:
            continue

        if entry["type"] == "file":
            url = _RAW_URL.format(
                repo=spec.repo,
                branch=spec.branch,
                path=f"{repo_prefix}/{name}",
            )
            try:
                content = _fetch_text(url, timeout)
                rel = f"{install_prefix}/{name}"
                if tracker is not None:
                    tracker.write_text(rel, content)
                else:
                    path = output_dir / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)
                files_written.append(rel)
            except Exception:
                # SKILL.md at root is required
                if name == "SKILL.md" and depth == 0:
                    raise

        elif entry["type"] == "dir" and depth < 3:
            # Recurse into subdirectories (capped at depth 3)
            try:
                sub_entries = _list_directory(spec.repo, f"{repo_prefix}/{name}", timeout)
                _download_tree_entries(
                    entries=sub_entries,
                    spec=spec,
                    repo_prefix=f"{repo_prefix}/{name}",
                    install_prefix=f"{install_prefix}/{name}",
                    output_dir=output_dir,
                    tracker=tracker,
                    timeout=timeout,
                    files_written=files_written,
                    depth=depth + 1,
                )
            except Exception:
                pass  # Skip failed subdirectory listings


def _fetch_text(url: str, timeout: int) -> str:
    """Fetch a URL and return its text content."""
    req = urllib.request.Request(url, headers={"User-Agent": "cc-rig"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def _list_directory(repo: str, path: str, timeout: int) -> list[dict]:
    """List directory contents via GitHub Contents API."""
    url = _API_URL.format(repo=repo, path=path)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "cc-rig",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))
