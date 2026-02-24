"""Claude Code version detection and compatibility checking.

Detects installed Claude Code version and warns about missing or
outdated installations. Generates all files regardless — they work
when CC is installed later.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

# Minimum CC version for full feature support (worktrees, etc.)
MIN_CC_VERSION = (2, 1, 50)
MIN_CC_VERSION_STR = "2.1.50"


@dataclass
class CCVersionResult:
    """Result of Claude Code version detection."""

    installed: bool
    version: tuple[int, ...] | None  # (major, minor, patch)
    version_str: str  # e.g. "2.1.50" or "not found"
    warnings: list[str]

    @property
    def meets_minimum(self) -> bool:
        """Check if installed version meets minimum requirement."""
        if not self.installed or self.version is None:
            return False
        return self.version >= MIN_CC_VERSION


def detect_cc_version() -> CCVersionResult:
    """Detect installed Claude Code version by running `claude --version`.

    Returns a CCVersionResult with version info and any warnings.
    Never raises — returns a result with installed=False if detection fails.
    """
    try:
        proc = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = proc.stdout.strip() + proc.stderr.strip()
    except FileNotFoundError:
        return CCVersionResult(
            installed=False,
            version=None,
            version_str="not found",
            warnings=[
                "Claude Code not detected. Generated files will work once Claude Code is installed."
            ],
        )
    except (subprocess.TimeoutExpired, OSError):
        return CCVersionResult(
            installed=False,
            version=None,
            version_str="not found",
            warnings=["Could not detect Claude Code version."],
        )

    # Parse version from output (e.g. "claude 2.1.50" or "2.1.50")
    version = _parse_version(output)
    if version is None:
        return CCVersionResult(
            installed=True,
            version=None,
            version_str="unknown",
            warnings=[f"Could not parse Claude Code version from: {output!r}"],
        )

    version_str = ".".join(str(v) for v in version)
    warnings: list[str] = []

    if version < MIN_CC_VERSION:
        warnings.append(
            f"Claude Code {version_str} detected. "
            f"Some features work best with v{MIN_CC_VERSION_STR}+."
        )

    return CCVersionResult(
        installed=True,
        version=version,
        version_str=version_str,
        warnings=warnings,
    )


def _parse_version(output: str) -> tuple[int, ...] | None:
    """Extract semver tuple from claude --version output."""
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", output)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
