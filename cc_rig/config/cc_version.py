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


# ── Feature compatibility ──────────────────────────────────────────

# Feature → minimum CC version required.
# Conservative estimates; easy to update as CC changelog evolves.
FEATURE_MIN_VERSIONS: dict[str, tuple[int, ...]] = {
    "plugins": (1, 0, 13),
    "precompact_hook": (1, 0, 2),
    "subagent_stop_hook": (1, 0, 6),
    "settings_local": (1, 0, 2),
    "background_agents": (1, 0, 6),
    "worktree_isolation": (1, 0, 6),
}


def _fmt_version(v: tuple[int, ...]) -> str:
    return ".".join(str(x) for x in v)


def check_feature_compat(
    version: tuple[int, ...] | None,
    config: "ProjectConfig",  # noqa: F821
) -> list[str]:
    """Check config features against detected CC version. Returns warnings."""
    if version is None:
        return []

    warnings: list[str] = []

    # Check plugins
    if config.recommended_plugins and version < FEATURE_MIN_VERSIONS["plugins"]:
        warnings.append(
            f"Plugins require Claude Code {_fmt_version(FEATURE_MIN_VERSIONS['plugins'])}+"
        )

    # Check settings.local.json
    if version < FEATURE_MIN_VERSIONS["settings_local"]:
        warnings.append(
            f"settings.local.json requires Claude Code "
            f"{_fmt_version(FEATURE_MIN_VERSIONS['settings_local'])}+"
        )

    # Check agent features (background, worktree isolation)
    if config.agents:
        from cc_rig.generators.agents import _AGENT_DEFS

        for agent_name in config.agents:
            defn = _AGENT_DEFS.get(agent_name)
            if defn is None:
                continue
            if defn.background and version < FEATURE_MIN_VERSIONS["background_agents"]:
                warnings.append(
                    f"Agent '{agent_name}' uses background mode, "
                    f"requires Claude Code "
                    f"{_fmt_version(FEATURE_MIN_VERSIONS['background_agents'])}+"
                )
                break  # One warning is enough
            if defn.isolation and version < FEATURE_MIN_VERSIONS["worktree_isolation"]:
                warnings.append(
                    f"Agent '{agent_name}' uses worktree isolation, "
                    f"requires Claude Code "
                    f"{_fmt_version(FEATURE_MIN_VERSIONS['worktree_isolation'])}+"
                )
                break

    return warnings
