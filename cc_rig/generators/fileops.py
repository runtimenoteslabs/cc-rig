"""Safe file operations with pre-existence tracking and backup.

FileTracker wraps file writes to detect pre-existing files and
create backups before overwriting. The metadata it collects is
stored in the manifest so ``cc-rig clean`` can restore originals
instead of deleting user files.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

# Name of the backup directory created alongside the project root.
_BACKUP_DIR = ".cc-rig-backup"


class FileTracker:
    """Track file writes, detect pre-existing files, create backups.

    Usage::

        tracker = FileTracker(output_dir)
        tracker.write_text("CLAUDE.md", content)
        metadata = tracker.metadata()
    """

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir.resolve()
        self._meta: dict[str, dict[str, Any]] = {}
        self._written: set[str] = set()  # files written in this session

    def write_text(self, rel_path: str, content: str, *, preserve_on_clean: bool = False) -> None:
        """Write *content* to *rel_path* under the output directory.

        If the file already exists, backs it up to ``_BACKUP_DIR``
        before overwriting.

        When *preserve_on_clean* is True, the manifest records a
        content hash so ``cc-rig clean`` can skip files the user has
        edited since generation.
        """
        full = self._output_dir / rel_path
        # Guard against path traversal via crafted rel_path values
        if not str(full.resolve()).startswith(str(self._output_dir) + "/"):
            raise ValueError(f"Path traversal detected: {rel_path}")
        # Only treat as pre-existing if it existed before this generation run
        pre_existed = full.exists() and rel_path not in self._written
        backed_up = False

        if pre_existed:
            backup = self._backup_path(rel_path)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(full), str(backup))
            backed_up = True

        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)

        meta: dict[str, Any] = {
            "pre_existed": pre_existed,
            "backed_up": backed_up,
        }
        if preserve_on_clean:
            meta["preserve_on_clean"] = True
            meta["content_hash"] = hashlib.sha256(content.encode()).hexdigest()

        self._meta[rel_path] = meta
        self._written.add(rel_path)

    def chmod(self, rel_path: str, mode: int) -> None:
        """Set file permissions (e.g. 0o755 for hook scripts)."""
        (self._output_dir / rel_path).chmod(mode)

    def metadata(self) -> dict[str, dict[str, Any]]:
        """Return a deep copy of the collected file metadata."""
        return {k: dict(v) for k, v in self._meta.items()}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _backup_path(self, rel_path: str) -> Path:
        return self._output_dir / _BACKUP_DIR / (rel_path + ".bak")
