"""Plugins subsystem — official Claude Code plugin catalog and resolution."""

from cc_rig.plugins.registry import (
    LANGUAGE_PLUGINS,
    PLUGIN_CATALOG,
    TEMPLATE_PLUGINS,
    WORKFLOW_PLUGINS,
    PluginSpec,
    resolve_plugins,
)

__all__ = [
    "LANGUAGE_PLUGINS",
    "PLUGIN_CATALOG",
    "TEMPLATE_PLUGINS",
    "WORKFLOW_PLUGINS",
    "PluginSpec",
    "resolve_plugins",
]
