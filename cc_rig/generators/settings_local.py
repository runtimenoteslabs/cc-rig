"""Generate .claude/settings.local.json with personal permission stubs."""

from __future__ import annotations

import json
from pathlib import Path

from cc_rig.generators.fileops import FileTracker


def generate_settings_local(
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate .claude/settings.local.json for per-developer overrides.

    This file lets individual developers customise permissions and
    environment variables without touching the team-shared settings.json.
    Uses preserve_on_clean=True so cc-rig clean does not delete user
    customisations.

    Returns list of relative file paths written.
    """
    data = {
        "permissions": {
            "allow": [],
            "deny": [],
        },
        "env": {},
    }
    content = json.dumps(data, indent=2) + "\n"

    rel = ".claude/settings.local.json"
    if tracker is not None:
        tracker.write_text(rel, content, preserve_on_clean=True)
    else:
        out = output_dir / ".claude"
        out.mkdir(parents=True, exist_ok=True)
        (output_dir / rel).write_text(content)

    return [rel]
