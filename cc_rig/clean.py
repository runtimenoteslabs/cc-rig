"""Manifest-based clean/uninstall for cc-rig projects.

Removes only the files that cc-rig generated, using the manifest
as the source of truth. Cleans up empty directories afterward.
Pre-existing files are restored from backup instead of deleted.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Callable

from cc_rig.generators.fileops import _BACKUP_DIR


class CleanResult:
    """Tracks what was removed during clean."""

    def __init__(self) -> None:
        self.removed: list[str] = []
        self.already_missing: list[str] = []
        self.dirs_removed: list[str] = []
        self.restored: list[str] = []
        self.skipped_preexisting: list[str] = []

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

    Pre-existing files (recorded in ``file_metadata``) are restored
    from ``.cc-rig-backup`` instead of being deleted.

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

    file_metadata: dict[str, dict[str, Any]] = manifest.get("file_metadata", {})
    backup_dir = project_dir / _BACKUP_DIR

    # Remove files
    resolved_root = project_dir.resolve()
    for rel_path in files:
        full_path = (project_dir / rel_path).resolve()
        # Guard against path traversal (e.g. "../../etc/passwd" in manifest)
        if not str(full_path).startswith(str(resolved_root) + "/") and full_path != resolved_root:
            continue

        meta = file_metadata.get(rel_path, {})
        pre_existed = meta.get("pre_existed", False)
        backed_up = meta.get("backed_up", False)

        if pre_existed:
            # Restore from backup if available, otherwise skip
            if backed_up:
                backup_path = backup_dir / rel_path
                if backup_path.exists():
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(backup_path), str(full_path))
                    result.restored.append(rel_path)
                    continue
            # Pre-existed but no backup — skip rather than delete
            result.skipped_preexisting.append(rel_path)
            continue

        if full_path.exists():
            full_path.unlink()
            result.removed.append(rel_path)
        else:
            result.already_missing.append(rel_path)

    # Also remove .cc-rig.json (project config) if it wasn't pre-existing
    cc_rig_json = project_dir / ".cc-rig.json"
    cc_rig_meta = file_metadata.get(".cc-rig.json", {})
    if cc_rig_json.exists() and not cc_rig_meta.get("pre_existed", False):
        cc_rig_json.unlink()
        result.removed.append(".cc-rig.json")

    # Clean up backup directory
    if backup_dir.exists():
        shutil.rmtree(str(backup_dir), ignore_errors=True)

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
