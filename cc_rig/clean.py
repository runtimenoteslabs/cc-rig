"""Manifest-based clean/uninstall for cc-rig projects.

Removes only the files that cc-rig generated, using the manifest
as the source of truth. Cleans up empty directories afterward.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


class CleanResult:
    """Tracks what was removed during clean."""

    def __init__(self) -> None:
        self.removed: list[str] = []
        self.already_missing: list[str] = []
        self.dirs_removed: list[str] = []

    @property
    def total_removed(self) -> int:
        return len(self.removed)


def load_manifest(project_dir: Path) -> dict[str, Any] | None:
    """Load the cc-rig manifest from a project directory.

    Returns None if the manifest doesn't exist or is invalid.
    """
    manifest_path = project_dir / ".claude" / ".cc-rig-manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def run_clean(
    project_dir: Path,
    force: bool = False,
    confirm_fn: Callable[[str], bool] | None = None,
) -> CleanResult:
    """Remove all files tracked by the manifest.

    Args:
        project_dir: Root of the project.
        force: If True, skip confirmation prompt.
        confirm_fn: Callable(prompt) -> bool for confirmation.
            If None and not force, raises RuntimeError.

    Returns:
        CleanResult with removed/missing file lists.
    """
    result = CleanResult()

    manifest = load_manifest(project_dir)
    if manifest is None:
        raise FileNotFoundError(
            "No manifest found at .claude/.cc-rig-manifest.json. "
            "Cannot determine which files to remove."
        )

    files = manifest.get("files", [])
    if not files:
        return result

    if not force:
        if confirm_fn is None:
            raise RuntimeError("Confirmation required but no confirm_fn provided.")
        if not confirm_fn(f"Remove {len(files)} generated files?"):
            return result

    # Remove files
    resolved_root = project_dir.resolve()
    for rel_path in files:
        full_path = (project_dir / rel_path).resolve()
        # Guard against path traversal (e.g. "../../etc/passwd" in manifest)
        if not str(full_path).startswith(str(resolved_root) + "/") and full_path != resolved_root:
            continue
        if full_path.exists():
            full_path.unlink()
            result.removed.append(rel_path)
        else:
            result.already_missing.append(rel_path)

    # Also remove .cc-rig.json (project config)
    cc_rig_json = project_dir / ".cc-rig.json"
    if cc_rig_json.exists():
        cc_rig_json.unlink()
        result.removed.append(".cc-rig.json")

    # Clean up empty directories (bottom-up)
    _remove_empty_dirs(project_dir, result)

    return result


def _remove_empty_dirs(project_dir: Path, result: CleanResult) -> None:
    """Remove empty directories left behind after file deletion.

    Only removes directories within the cc-rig managed tree
    (.claude/, memory/, agent_docs/).
    """
    managed_dirs = [
        project_dir / ".claude" / "hooks",
        project_dir / ".claude" / "agents",
        project_dir / ".claude" / "commands",
        project_dir / ".claude" / "skills",
        project_dir / ".claude",
        project_dir / "memory",
        project_dir / "agent_docs",
    ]

    for d in managed_dirs:
        if not d.exists():
            continue
        # Remove subdirectories first (skills has nested dirs)
        for sub in sorted(d.rglob("*"), reverse=True):
            if sub.is_dir() and not any(sub.iterdir()):
                sub.rmdir()
                result.dirs_removed.append(str(sub.relative_to(project_dir)))
        # Remove the directory itself if empty
        if d.exists() and not any(d.iterdir()):
            d.rmdir()
            result.dirs_removed.append(str(d.relative_to(project_dir)))
