"""Official Claude Code plugin catalog, mappings, and resolver.

Mirrors the cc_rig/skills/registry.py pattern for community skills.
Plugins are Anthropic marketplace extensions — LSP, integration, workflow, autonomy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PluginSpec:
    """Metadata for an official Claude Code plugin."""

    name: str  # e.g. "pyright-lsp"
    marketplace: str  # "claude-plugins-official"
    category: str  # "lsp", "integration", "workflow", "autonomy", "utility"
    description: str  # one-line for wizard/review
    requires_binary: str = ""  # e.g. "pyright" (LSP only), "" if self-contained
    replaces_mcp: str = ""  # MCP name this replaces, "" if none


# ── Plugin catalog (~25 official plugins) ─────────────────────────────

PLUGIN_CATALOG: dict[str, PluginSpec] = {
    # LSP plugins
    "pyright-lsp": PluginSpec(
        name="pyright-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="Python type checking and diagnostics via Pyright",
        requires_binary="pyright",
    ),
    "typescript-lsp": PluginSpec(
        name="typescript-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="TypeScript diagnostics and go-to-definition",
        requires_binary="typescript-language-server",
    ),
    "gopls-lsp": PluginSpec(
        name="gopls-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="Go language server with diagnostics and refactoring",
        requires_binary="gopls",
    ),
    "rust-analyzer-lsp": PluginSpec(
        name="rust-analyzer-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="Rust diagnostics, completion, and code actions",
        requires_binary="rust-analyzer",
    ),
    "jdtls-lsp": PluginSpec(
        name="jdtls-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="Java language server with Eclipse JDT",
        requires_binary="jdtls",
    ),
    "csharp-lsp": PluginSpec(
        name="csharp-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="C# diagnostics via OmniSharp",
        requires_binary="OmniSharp",
    ),
    "php-lsp": PluginSpec(
        name="php-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="PHP language server with Intelephense",
        requires_binary="intelephense",
    ),
    # Integration plugins
    "github": PluginSpec(
        name="github",
        marketplace="claude-plugins-official",
        category="integration",
        description="GitHub integration (PRs, issues, actions)",
        replaces_mcp="github",
    ),
    "vercel": PluginSpec(
        name="vercel",
        marketplace="claude-plugins-official",
        category="integration",
        description="Vercel deployment and project management",
    ),
    "supabase": PluginSpec(
        name="supabase",
        marketplace="claude-plugins-official",
        category="integration",
        description="Supabase database and auth management",
    ),
    "sentry": PluginSpec(
        name="sentry",
        marketplace="claude-plugins-official",
        category="integration",
        description="Sentry error tracking and performance monitoring",
    ),
    "slack": PluginSpec(
        name="slack",
        marketplace="claude-plugins-official",
        category="integration",
        description="Slack messaging and workspace integration",
    ),
    "linear": PluginSpec(
        name="linear",
        marketplace="claude-plugins-official",
        category="integration",
        description="Linear issue tracking and project management",
    ),
    "notion": PluginSpec(
        name="notion",
        marketplace="claude-plugins-official",
        category="integration",
        description="Notion workspace and documentation integration",
    ),
    "firebase": PluginSpec(
        name="firebase",
        marketplace="claude-plugins-official",
        category="integration",
        description="Firebase backend services and hosting",
    ),
    "gitlab": PluginSpec(
        name="gitlab",
        marketplace="claude-plugins-official",
        category="integration",
        description="GitLab repository and CI/CD integration",
    ),
    "atlassian": PluginSpec(
        name="atlassian",
        marketplace="claude-plugins-official",
        category="integration",
        description="Jira and Confluence integration",
    ),
    # Workflow plugins
    "commit-commands": PluginSpec(
        name="commit-commands",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Smart commit message generation and staging",
    ),
    "code-review": PluginSpec(
        name="code-review",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Automated code review with inline comments",
    ),
    "pr-review-toolkit": PluginSpec(
        name="pr-review-toolkit",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Pull request review with approval workflows",
    ),
    "feature-dev": PluginSpec(
        name="feature-dev",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Feature development lifecycle management",
    ),
    "security-guidance": PluginSpec(
        name="security-guidance",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Security best practices and vulnerability detection",
    ),
    # Autonomy plugin
    "ralph-loop": PluginSpec(
        name="ralph-loop",
        marketplace="claude-plugins-official",
        category="autonomy",
        description="Official Anthropic autonomous iteration loop",
    ),
    # Utility plugin
    "hookify": PluginSpec(
        name="hookify",
        marketplace="claude-plugins-official",
        category="utility",
        description="Visual hook builder and manager",
    ),
}


# ── Language → LSP plugin mapping ─────────────────────────────────────

LANGUAGE_PLUGINS: dict[str, str] = {
    "python": "pyright-lsp",
    "typescript": "typescript-lsp",
    "go": "gopls-lsp",
    "rust": "rust-analyzer-lsp",
    "java": "jdtls-lsp",
    "csharp": "csharp-lsp",
    "php": "php-lsp",
    # ruby, elixir, generic: no official LSP plugin yet
}


# ── Template → integration plugins ───────────────────────────────────

TEMPLATE_PLUGINS: dict[str, list[str]] = {
    "generic": ["github"],
    "fastapi": ["github"],
    "django": ["github"],
    "flask": ["github"],
    "nextjs": ["github", "vercel"],
    "gin": ["github"],
    "echo": ["github"],
    "rust-cli": ["github"],
    "rust-web": ["github"],
    "rails": ["github"],
    "spring": ["github"],
    "dotnet": ["github"],
    "laravel": ["github"],
    "express": ["github"],
    "phoenix": ["github"],
    "go-std": ["github"],
}


# ── Workflow → workflow plugins (cumulative) ─────────────────────────

WORKFLOW_PLUGINS: dict[str, list[str]] = {
    "speedrun": ["commit-commands"],
    "standard": ["commit-commands", "code-review"],
    "gstack": ["commit-commands", "code-review", "pr-review-toolkit"],
    "aihero": ["commit-commands", "code-review", "feature-dev", "pr-review-toolkit"],
    "spec-driven": ["commit-commands", "code-review", "feature-dev", "pr-review-toolkit"],
    "superpowers": [
        "commit-commands",
        "code-review",
        "pr-review-toolkit",
        "security-guidance",
    ],
    "gtd": ["commit-commands", "code-review"],
    # Backward compat aliases
    "gtd-lite": ["commit-commands", "code-review"],
    "verify-heavy": [
        "commit-commands",
        "code-review",
        "pr-review-toolkit",
        "security-guidance",
    ],
}


# ── Valid plugin categories ───────────────────────────────────────────

VALID_PLUGIN_CATEGORIES = {"lsp", "integration", "workflow", "autonomy", "utility"}


# ── Resolver ─────────────────────────────────────────────────────────


def resolve_plugins(
    template: str,
    workflow: str,
    language: str,
    default_mcps: Optional[list[str]] = None,
) -> tuple[list[PluginSpec], list[str]]:
    """Resolve plugins for a template × workflow × language combination.

    Combines language LSP + template integrations + workflow plugins.
    Does NOT include ralph-loop (that comes from harness config).

    Args:
        template: Template preset name (e.g. "fastapi").
        workflow: Workflow preset name (e.g. "standard").
        language: Language name (e.g. "python").
        default_mcps: Current MCP list for replacement detection.

    Returns:
        Tuple of (resolved plugins, MCP names to remove).
    """
    seen: dict[str, PluginSpec] = {}
    mcps_to_remove: list[str] = []

    # 1. Language LSP plugin (always included if available)
    lsp_name = LANGUAGE_PLUGINS.get(language)
    if lsp_name and lsp_name in PLUGIN_CATALOG:
        seen[lsp_name] = PLUGIN_CATALOG[lsp_name]

    # 2. Template integration plugins
    for plugin_name in TEMPLATE_PLUGINS.get(template, []):
        if plugin_name in PLUGIN_CATALOG:
            spec = PLUGIN_CATALOG[plugin_name]
            seen[plugin_name] = spec
            # Track MCP replacements
            if spec.replaces_mcp:
                mcps_to_remove.append(spec.replaces_mcp)

    # 3. Workflow plugins
    for plugin_name in WORKFLOW_PLUGINS.get(workflow, []):
        if plugin_name in PLUGIN_CATALOG:
            seen[plugin_name] = PLUGIN_CATALOG[plugin_name]

    return list(seen.values()), mcps_to_remove
