"""Official Claude Code plugin catalog, mappings, and resolver.

Mirrors the cc_rig/skills/registry.py pattern for community skills.
Plugins are Anthropic marketplace extensions — LSP, integration, workflow,
autonomy, utility, style.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PluginSpec:
    """Metadata for an official Claude Code plugin."""

    name: str  # e.g. "pyright-lsp"
    marketplace: str  # "claude-plugins-official"
    category: str  # "lsp", "integration", "workflow", "autonomy", "utility", "style"
    description: str  # one-line for wizard/review
    requires_binary: str = ""  # e.g. "pyright" (LSP only), "" if self-contained
    replaces_mcp: str = ""  # MCP name this replaces, "" if none


# ── Plugin catalog (80 official plugins) ──────────────────────────────

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
        description="C# diagnostics and code actions",
        requires_binary="csharp-ls",
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
    # ── V2.1: New LSP plugins (fill language gaps) ────────────────────
    "ruby-lsp": PluginSpec(
        name="ruby-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="Ruby language server with diagnostics and formatting",
        requires_binary="ruby-lsp",
    ),
    "clangd-lsp": PluginSpec(
        name="clangd-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="C/C++ diagnostics and code completion via clangd",
        requires_binary="clangd",
    ),
    "kotlin-lsp": PluginSpec(
        name="kotlin-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="Kotlin language server with diagnostics",
        requires_binary="kotlin-language-server",
    ),
    "lua-lsp": PluginSpec(
        name="lua-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="Lua language server with diagnostics",
        requires_binary="lua-language-server",
    ),
    "swift-lsp": PluginSpec(
        name="swift-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="Swift language server via SourceKit-LSP",
        requires_binary="sourcekit-lsp",
    ),
    # ── V2.1: New integration plugins (external) ─────────────────────
    "asana": PluginSpec(
        name="asana",
        marketplace="claude-plugins-official",
        category="integration",
        description="Asana project and task management",
    ),
    "context7": PluginSpec(
        name="context7",
        marketplace="claude-plugins-official",
        category="integration",
        description="Documentation context provider for libraries and frameworks",
    ),
    "discord": PluginSpec(
        name="discord",
        marketplace="claude-plugins-official",
        category="integration",
        description="Discord messaging and channel integration",
    ),
    "greptile": PluginSpec(
        name="greptile",
        marketplace="claude-plugins-official",
        category="integration",
        description="AI-powered codebase search and understanding",
    ),
    "laravel-boost": PluginSpec(
        name="laravel-boost",
        marketplace="claude-plugins-official",
        category="integration",
        description="Laravel-specific development tools and patterns",
    ),
    "playwright": PluginSpec(
        name="playwright",
        marketplace="claude-plugins-official",
        category="integration",
        description="Browser automation and end-to-end testing",
    ),
    "serena": PluginSpec(
        name="serena",
        marketplace="claude-plugins-official",
        category="integration",
        description="AI assistant integration and orchestration",
    ),
    "telegram": PluginSpec(
        name="telegram",
        marketplace="claude-plugins-official",
        category="integration",
        description="Telegram messaging and bot integration",
    ),
    # ── V2.1: New workflow plugins ────────────────────────────────────
    "code-simplifier": PluginSpec(
        name="code-simplifier",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Code clarity and maintainability improvements",
    ),
    "claude-md-management": PluginSpec(
        name="claude-md-management",
        marketplace="claude-plugins-official",
        category="workflow",
        description="CLAUDE.md file maintenance and optimization",
    ),
    "skill-creator": PluginSpec(
        name="skill-creator",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Create and optimize custom skills",
    ),
    "frontend-design": PluginSpec(
        name="frontend-design",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Frontend design guidance and component patterns",
    ),
    "agent-sdk-dev": PluginSpec(
        name="agent-sdk-dev",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Claude Agent SDK development toolkit",
    ),
    "mcp-server-dev": PluginSpec(
        name="mcp-server-dev",
        marketplace="claude-plugins-official",
        category="workflow",
        description="MCP server design and development",
    ),
    "plugin-dev": PluginSpec(
        name="plugin-dev",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Plugin development and testing toolkit",
    ),
    "claude-code-setup": PluginSpec(
        name="claude-code-setup",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Codebase analysis and automation recommendations",
    ),
    # ── V2.1: Style plugins (new category) ───────────────────────────
    "explanatory-output-style": PluginSpec(
        name="explanatory-output-style",
        marketplace="claude-plugins-official",
        category="style",
        description="Educational insights about implementation choices",
    ),
    "learning-output-style": PluginSpec(
        name="learning-output-style",
        marketplace="claude-plugins-official",
        category="style",
        description="Interactive learning mode with guided explanations",
    ),
    # ── V2.5: LSP expansion ─────────────────────────────────────────────
    "elixir-ls": PluginSpec(
        name="elixir-ls",
        marketplace="claude-plugins-official",
        category="lsp",
        description="Elixir language server with diagnostics and formatting",
        requires_binary="elixir-ls",
    ),
    "scala-metals-lsp": PluginSpec(
        name="scala-metals-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="Scala language server via Metals",
        requires_binary="metals",
    ),
    "dart-lsp": PluginSpec(
        name="dart-lsp",
        marketplace="claude-plugins-official",
        category="lsp",
        description="Dart language server with diagnostics and completion",
        requires_binary="dart",
    ),
    # ── V2.5: Integration expansion ─────────────────────────────────────
    "figma": PluginSpec(
        name="figma",
        marketplace="claude-plugins-official",
        category="integration",
        description="Figma design file inspection and component extraction",
    ),
    "stripe": PluginSpec(
        name="stripe",
        marketplace="claude-plugins-official",
        category="integration",
        description="Stripe payment processing and webhook management",
    ),
    "aws": PluginSpec(
        name="aws",
        marketplace="claude-plugins-official",
        category="integration",
        description="AWS service integration (S3, Lambda, CloudFormation)",
    ),
    "gcp": PluginSpec(
        name="gcp",
        marketplace="claude-plugins-official",
        category="integration",
        description="Google Cloud Platform service integration",
    ),
    "azure": PluginSpec(
        name="azure",
        marketplace="claude-plugins-official",
        category="integration",
        description="Azure cloud service integration",
    ),
    "datadog": PluginSpec(
        name="datadog",
        marketplace="claude-plugins-official",
        category="integration",
        description="Datadog monitoring and observability integration",
    ),
    "pagerduty": PluginSpec(
        name="pagerduty",
        marketplace="claude-plugins-official",
        category="integration",
        description="PagerDuty incident management integration",
    ),
    "grafana": PluginSpec(
        name="grafana",
        marketplace="claude-plugins-official",
        category="integration",
        description="Grafana dashboard and alerting integration",
    ),
    "redis": PluginSpec(
        name="redis",
        marketplace="claude-plugins-official",
        category="integration",
        description="Redis cache management and monitoring",
    ),
    "mongodb": PluginSpec(
        name="mongodb",
        marketplace="claude-plugins-official",
        category="integration",
        description="MongoDB database operations and schema management",
    ),
    "twilio": PluginSpec(
        name="twilio",
        marketplace="claude-plugins-official",
        category="integration",
        description="Twilio communications API integration",
    ),
    "sendgrid": PluginSpec(
        name="sendgrid",
        marketplace="claude-plugins-official",
        category="integration",
        description="SendGrid email delivery integration",
    ),
    "cloudflare": PluginSpec(
        name="cloudflare",
        marketplace="claude-plugins-official",
        category="integration",
        description="Cloudflare CDN and Workers integration",
    ),
    "docker": PluginSpec(
        name="docker",
        marketplace="claude-plugins-official",
        category="integration",
        description="Docker container management and Compose integration",
    ),
    "terraform": PluginSpec(
        name="terraform",
        marketplace="claude-plugins-official",
        category="integration",
        description="Terraform infrastructure-as-code integration",
    ),
    "heroku": PluginSpec(
        name="heroku",
        marketplace="claude-plugins-official",
        category="integration",
        description="Heroku app deployment and management",
    ),
    "railway": PluginSpec(
        name="railway",
        marketplace="claude-plugins-official",
        category="integration",
        description="Railway deployment and infrastructure management",
    ),
    "shopify": PluginSpec(
        name="shopify",
        marketplace="claude-plugins-official",
        category="integration",
        description="Shopify storefront and admin API integration",
    ),
    # ── V2.5: Workflow expansion ─────────────────────────────────────────
    "test-runner": PluginSpec(
        name="test-runner",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Automated test execution and coverage reporting",
    ),
    "doc-generator": PluginSpec(
        name="doc-generator",
        marketplace="claude-plugins-official",
        category="workflow",
        description="API documentation generation from code",
    ),
    "perf-profiler": PluginSpec(
        name="perf-profiler",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Performance profiling and optimization suggestions",
    ),
    "migration-helper": PluginSpec(
        name="migration-helper",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Database migration generation and validation",
    ),
    "dependency-updater": PluginSpec(
        name="dependency-updater",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Dependency version management and security updates",
    ),
    "changelog-generator": PluginSpec(
        name="changelog-generator",
        marketplace="claude-plugins-official",
        category="workflow",
        description="Automated changelog generation from commits",
    ),
    "api-design": PluginSpec(
        name="api-design",
        marketplace="claude-plugins-official",
        category="workflow",
        description="API design review and OpenAPI spec validation",
    ),
    # ── V2.5: Style expansion ───────────────────────────────────────────
    "concise-output-style": PluginSpec(
        name="concise-output-style",
        marketplace="claude-plugins-official",
        category="style",
        description="Minimal output with code-focused responses",
    ),
    "mentor-output-style": PluginSpec(
        name="mentor-output-style",
        marketplace="claude-plugins-official",
        category="style",
        description="Teaching-oriented explanations with best practices",
    ),
    "team-lead-output-style": PluginSpec(
        name="team-lead-output-style",
        marketplace="claude-plugins-official",
        category="style",
        description="Team-oriented responses with delegation guidance",
    ),
    # ── V2.5: Utility expansion ─────────────────────────────────────────
    "config-doctor": PluginSpec(
        name="config-doctor",
        marketplace="claude-plugins-official",
        category="utility",
        description="Configuration validation and health checks",
    ),
    "context-optimizer": PluginSpec(
        name="context-optimizer",
        marketplace="claude-plugins-official",
        category="utility",
        description="Context window optimization and token management",
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
    "ruby": "ruby-lsp",
    "elixir": "elixir-ls",
    # generic: no official LSP plugin
}


# ── Template → integration plugins ───────────────────────────────────

TEMPLATE_PLUGINS: dict[str, list[str]] = {
    "generic": ["github"],
    "fastapi": ["github", "docker"],
    "django": ["github", "redis"],
    "flask": ["github"],
    "nextjs": ["github", "vercel", "frontend-design", "playwright", "stripe"],
    "gin": ["github"],
    "echo": ["github"],
    "rust-cli": ["github"],
    "rust-web": ["github"],
    "rails": ["github", "redis"],
    "spring": ["github", "aws"],
    "dotnet": ["github"],
    "laravel": ["github", "laravel-boost"],
    "express": ["github", "playwright"],
    "phoenix": ["github"],
    "go-std": ["github"],
}


# ── Workflow → workflow plugins (cumulative) ─────────────────────────

WORKFLOW_PLUGINS: dict[str, list[str]] = {
    # Tiers
    "quick": ["commit-commands"],
    "standard": ["commit-commands", "code-review"],
    "rigorous": [
        "commit-commands",
        "code-review",
        "pr-review-toolkit",
        "security-guidance",
        "code-simplifier",
        "test-runner",
        "doc-generator",
    ],
    # Legacy workflow names
    "speedrun": ["commit-commands"],
    "gstack": ["commit-commands", "code-review", "pr-review-toolkit"],
    "aihero": ["commit-commands", "code-review", "feature-dev", "pr-review-toolkit"],
    "spec-driven": [
        "commit-commands",
        "code-review",
        "feature-dev",
        "pr-review-toolkit",
        "code-simplifier",
        "test-runner",
        "doc-generator",
    ],
    "superpowers": [
        "commit-commands",
        "code-review",
        "pr-review-toolkit",
        "security-guidance",
        "code-simplifier",
        "test-runner",
        "doc-generator",
    ],
    "gtd": ["commit-commands", "code-review"],
    "gtd-lite": ["commit-commands", "code-review"],
    "verify-heavy": [
        "commit-commands",
        "code-review",
        "pr-review-toolkit",
        "security-guidance",
        "code-simplifier",
        "test-runner",
        "doc-generator",
    ],
}


# ── Valid plugin categories ───────────────────────────────────────────

VALID_PLUGIN_CATEGORIES = {"lsp", "integration", "workflow", "autonomy", "utility", "style"}


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
