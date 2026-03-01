"""Framework template content for cc-rig.

Each framework module exports a CONTENT dict with keys:
    rules, architecture, conventions, testing, deployment
"""

from __future__ import annotations

from importlib import import_module
from typing import TypedDict


class FrameworkContent(TypedDict, total=False):
    """Schema for framework template CONTENT dicts."""

    rules: str
    architecture: str
    conventions: str
    testing: str
    deployment: str


_FRAMEWORK_MODULE_OVERRIDES: dict[str, str] = {
    "clap": "rust_cli",
    "axum": "rust_web",
    "spring-boot": "spring_boot",
    "go-std": "go_std",
}


def get_framework_content(framework: str) -> FrameworkContent:
    """Return the CONTENT dict for the given framework.

    Falls back to the generic module for unrecognized frameworks.
    """
    module_name = _FRAMEWORK_MODULE_OVERRIDES.get(framework, framework)
    try:
        module = import_module(f"cc_rig.templates.frameworks.{module_name}")
    except ImportError:
        module = import_module("cc_rig.templates.frameworks.generic")
    return module.CONTENT
