"""Tests for plugin registry — catalog, mappings, and resolver."""

from __future__ import annotations

from cc_rig.config.schema import VALID_LANGUAGES
from cc_rig.plugins.registry import (
    LANGUAGE_PLUGINS,
    PLUGIN_CATALOG,
    TEMPLATE_PLUGINS,
    VALID_PLUGIN_CATEGORIES,
    WORKFLOW_PLUGINS,
    resolve_plugins,
)
from cc_rig.presets.manager import BUILTIN_TEMPLATES, BUILTIN_WORKFLOWS

# ── Catalog completeness ─────────────────────────────────────────────


class TestPluginCatalog:
    """Verify PLUGIN_CATALOG structure and completeness."""

    def test_catalog_is_nonempty(self):
        assert len(PLUGIN_CATALOG) > 0

    def test_catalog_has_expected_count(self):
        """Guard: update count when adding/removing plugins."""
        assert len(PLUGIN_CATALOG) == 80

    def test_all_plugins_have_name(self):
        for name, spec in PLUGIN_CATALOG.items():
            assert spec.name == name, f"Plugin {name!r} has mismatched name {spec.name!r}"

    def test_all_plugins_have_marketplace(self):
        for name, spec in PLUGIN_CATALOG.items():
            assert spec.marketplace, f"Plugin {name!r} missing marketplace"

    def test_all_plugins_have_category(self):
        for name, spec in PLUGIN_CATALOG.items():
            assert spec.category, f"Plugin {name!r} missing category"

    def test_all_plugins_have_description(self):
        for name, spec in PLUGIN_CATALOG.items():
            assert spec.description, f"Plugin {name!r} missing description"

    def test_all_categories_are_valid(self):
        for name, spec in PLUGIN_CATALOG.items():
            assert spec.category in VALID_PLUGIN_CATEGORIES, (
                f"Plugin {name!r} has invalid category {spec.category!r}"
            )

    def test_lsp_plugins_have_requires_binary(self):
        lsp_plugins = [s for s in PLUGIN_CATALOG.values() if s.category == "lsp"]
        for spec in lsp_plugins:
            assert spec.requires_binary, f"LSP plugin {spec.name!r} missing requires_binary"

    def test_non_lsp_plugins_mostly_no_binary(self):
        non_lsp = [s for s in PLUGIN_CATALOG.values() if s.category != "lsp"]
        for spec in non_lsp:
            assert spec.requires_binary == "", (
                f"Non-LSP plugin {spec.name!r} should not have requires_binary"
            )

    def test_github_plugin_replaces_github_mcp(self):
        assert PLUGIN_CATALOG["github"].replaces_mcp == "github"

    def test_ralph_loop_is_autonomy_category(self):
        assert PLUGIN_CATALOG["ralph-loop"].category == "autonomy"

    def test_ralph_loop_not_in_template_plugins(self):
        """ralph-loop should never appear in TEMPLATE_PLUGINS values."""
        for template, plugins in TEMPLATE_PLUGINS.items():
            assert "ralph-loop" not in plugins, (
                f"ralph-loop found in TEMPLATE_PLUGINS[{template!r}]"
            )

    def test_ralph_loop_not_in_workflow_plugins(self):
        """ralph-loop should never appear in WORKFLOW_PLUGINS values."""
        for workflow, plugins in WORKFLOW_PLUGINS.items():
            assert "ralph-loop" not in plugins, (
                f"ralph-loop found in WORKFLOW_PLUGINS[{workflow!r}]"
            )

    def test_ralph_loop_has_no_mcp_replacement(self):
        """ralph-loop plugin should not claim to replace any MCP."""
        ralph = [s for s in PLUGIN_CATALOG.values() if s.name == "ralph-loop"]
        assert len(ralph) == 1
        assert ralph[0].replaces_mcp == ""


# ── Language plugins mapping ─────────────────────────────────────────


class TestLanguagePlugins:
    """Verify LANGUAGE_PLUGINS keys match VALID_LANGUAGES."""

    def test_all_language_keys_are_valid(self):
        for lang in LANGUAGE_PLUGINS:
            assert lang in VALID_LANGUAGES, f"Unknown language: {lang!r}"

    def test_all_plugin_values_exist_in_catalog(self):
        for lang, plugin in LANGUAGE_PLUGINS.items():
            assert plugin in PLUGIN_CATALOG, (
                f"Language {lang!r} references unknown plugin {plugin!r}"
            )

    def test_python_has_pyright(self):
        assert LANGUAGE_PLUGINS["python"] == "pyright-lsp"

    def test_typescript_has_ts_lsp(self):
        assert LANGUAGE_PLUGINS["typescript"] == "typescript-lsp"

    def test_go_has_gopls(self):
        assert LANGUAGE_PLUGINS["go"] == "gopls-lsp"

    def test_rust_has_rust_analyzer(self):
        assert LANGUAGE_PLUGINS["rust"] == "rust-analyzer-lsp"

    def test_ruby_has_ruby_lsp(self):
        assert LANGUAGE_PLUGINS["ruby"] == "ruby-lsp"

    def test_elixir_has_elixir_ls(self):
        assert LANGUAGE_PLUGINS["elixir"] == "elixir-ls"

    def test_generic_has_no_lsp(self):
        assert "generic" not in LANGUAGE_PLUGINS


# ── Template plugins mapping ────────────────────────────────────────


class TestTemplatePlugins:
    """Verify TEMPLATE_PLUGINS keys match BUILTIN_TEMPLATES."""

    def test_all_template_keys_exist(self):
        for tmpl in BUILTIN_TEMPLATES:
            assert tmpl in TEMPLATE_PLUGINS, f"Missing TEMPLATE_PLUGINS entry for {tmpl!r}"

    def test_all_templates_have_github(self):
        for tmpl in BUILTIN_TEMPLATES:
            assert "github" in TEMPLATE_PLUGINS[tmpl], f"Template {tmpl!r} missing github plugin"

    def test_nextjs_has_vercel(self):
        assert "vercel" in TEMPLATE_PLUGINS["nextjs"]

    def test_all_plugin_refs_exist_in_catalog(self):
        for tmpl, plugins in TEMPLATE_PLUGINS.items():
            for name in plugins:
                assert name in PLUGIN_CATALOG, (
                    f"Template {tmpl!r} references unknown plugin {name!r}"
                )


# ── Workflow plugins mapping ────────────────────────────────────────


class TestWorkflowPlugins:
    """Verify WORKFLOW_PLUGINS keys match BUILTIN_WORKFLOWS."""

    def test_all_workflow_keys_exist(self):
        for wf in BUILTIN_WORKFLOWS:
            assert wf in WORKFLOW_PLUGINS, f"Missing WORKFLOW_PLUGINS entry for {wf!r}"

    def test_speedrun_has_commit_commands(self):
        assert "commit-commands" in WORKFLOW_PLUGINS["speedrun"]

    def test_standard_has_code_review(self):
        assert "code-review" in WORKFLOW_PLUGINS["standard"]

    def test_spec_driven_has_feature_dev(self):
        assert "feature-dev" in WORKFLOW_PLUGINS["spec-driven"]

    def test_verify_heavy_has_security_guidance(self):
        assert "security-guidance" in WORKFLOW_PLUGINS["verify-heavy"]

    def test_all_plugin_refs_exist_in_catalog(self):
        for wf, plugins in WORKFLOW_PLUGINS.items():
            for name in plugins:
                assert name in PLUGIN_CATALOG, f"Workflow {wf!r} references unknown plugin {name!r}"

    def test_workflow_plugins_scale_with_complexity(self):
        """More complex workflows should have more plugins."""
        speedrun_count = len(WORKFLOW_PLUGINS["speedrun"])
        standard_count = len(WORKFLOW_PLUGINS["standard"])
        spec_count = len(WORKFLOW_PLUGINS["spec-driven"])
        assert speedrun_count <= standard_count <= spec_count


# ── Resolver ────────────────────────────────────────────────────────


class TestResolvePlugins:
    """Verify resolve_plugins() combines dimensions correctly."""

    def test_python_fastapi_standard(self):
        plugins, mcps_remove = resolve_plugins("fastapi", "standard", "python")
        names = {p.name for p in plugins}
        assert "pyright-lsp" in names  # language LSP
        assert "github" in names  # template integration
        assert "commit-commands" in names  # speedrun workflow
        assert "code-review" in names  # standard workflow
        assert "github" in mcps_remove  # replaces github MCP

    def test_typescript_nextjs_verify_heavy(self):
        plugins, _ = resolve_plugins("nextjs", "verify-heavy", "typescript")
        names = {p.name for p in plugins}
        assert "typescript-lsp" in names
        assert "github" in names
        assert "vercel" in names  # nextjs-specific
        assert "security-guidance" in names  # verify-heavy

    def test_ruby_rails_standard(self):
        plugins, _ = resolve_plugins("rails", "standard", "ruby")
        names = {p.name for p in plugins}
        assert "github" in names
        assert "ruby-lsp" in names  # V2.1: Ruby now has LSP

    def test_generic_speedrun(self):
        plugins, _ = resolve_plugins("generic", "speedrun", "generic")
        names = {p.name for p in plugins}
        assert "github" in names
        assert "commit-commands" in names
        # No LSP for generic
        assert not any(p.category == "lsp" for p in plugins)

    def test_ralph_loop_not_included(self):
        """resolve_plugins should never include ralph-loop (harness-managed)."""
        for tmpl in BUILTIN_TEMPLATES:
            for wf in BUILTIN_WORKFLOWS:
                plugins, _ = resolve_plugins(tmpl, wf, "python")
                names = {p.name for p in plugins}
                assert "ralph-loop" not in names

    def test_dedup_no_duplicates(self):
        plugins, _ = resolve_plugins("fastapi", "verify-heavy", "python")
        names = [p.name for p in plugins]
        assert len(names) == len(set(names)), f"Duplicate plugins: {names}"

    def test_mcp_replacement_github(self):
        _, mcps_remove = resolve_plugins("fastapi", "standard", "python", ["github", "postgres"])
        assert "github" in mcps_remove
        assert "postgres" not in mcps_remove

    def test_no_mcp_replacement_when_no_mcps(self):
        _, mcps_remove = resolve_plugins("generic", "standard", "generic", [])
        # github replacement is still reported even with empty mcps
        assert "github" in mcps_remove


# ── V2.1 Plugin Expansion Tests ──────────────────────────────────────


class TestV21PluginExpansion:
    """V2.1: New LSP, integration, workflow, and style plugins."""

    def test_new_lsp_plugins_exist(self):
        new_lsp = ["ruby-lsp", "clangd-lsp", "kotlin-lsp", "lua-lsp", "swift-lsp"]
        for name in new_lsp:
            assert name in PLUGIN_CATALOG, f"Missing LSP plugin {name!r}"
            assert PLUGIN_CATALOG[name].category == "lsp"

    def test_new_lsp_plugins_have_binary(self):
        new_lsp = ["ruby-lsp", "clangd-lsp", "kotlin-lsp", "lua-lsp", "swift-lsp"]
        for name in new_lsp:
            assert PLUGIN_CATALOG[name].requires_binary, f"{name} missing requires_binary"

    def test_new_integration_plugins_exist(self):
        new_integ = [
            "asana",
            "context7",
            "discord",
            "greptile",
            "laravel-boost",
            "playwright",
            "serena",
            "telegram",
        ]
        for name in new_integ:
            assert name in PLUGIN_CATALOG, f"Missing integration plugin {name!r}"
            assert PLUGIN_CATALOG[name].category == "integration"

    def test_new_workflow_plugins_exist(self):
        new_wf = [
            "code-simplifier",
            "claude-md-management",
            "skill-creator",
            "frontend-design",
            "agent-sdk-dev",
            "mcp-server-dev",
            "plugin-dev",
            "claude-code-setup",
        ]
        for name in new_wf:
            assert name in PLUGIN_CATALOG, f"Missing workflow plugin {name!r}"
            assert PLUGIN_CATALOG[name].category == "workflow"

    def test_style_plugins_exist(self):
        style = ["explanatory-output-style", "learning-output-style"]
        for name in style:
            assert name in PLUGIN_CATALOG, f"Missing style plugin {name!r}"
            assert PLUGIN_CATALOG[name].category == "style"

    def test_csharp_lsp_binary_fixed(self):
        assert PLUGIN_CATALOG["csharp-lsp"].requires_binary == "csharp-ls"

    def test_laravel_has_laravel_boost(self):
        assert "laravel-boost" in TEMPLATE_PLUGINS["laravel"]

    def test_nextjs_has_frontend_design(self):
        assert "frontend-design" in TEMPLATE_PLUGINS["nextjs"]

    def test_nextjs_has_playwright(self):
        assert "playwright" in TEMPLATE_PLUGINS["nextjs"]

    def test_express_has_playwright(self):
        assert "playwright" in TEMPLATE_PLUGINS["express"]

    def test_spec_driven_has_code_simplifier(self):
        assert "code-simplifier" in WORKFLOW_PLUGINS["spec-driven"]

    def test_superpowers_has_code_simplifier(self):
        assert "code-simplifier" in WORKFLOW_PLUGINS["superpowers"]

    def test_verify_heavy_has_code_simplifier(self):
        assert "code-simplifier" in WORKFLOW_PLUGINS["verify-heavy"]

    def test_speedrun_no_code_simplifier(self):
        assert "code-simplifier" not in WORKFLOW_PLUGINS["speedrun"]

    def test_ruby_rails_gets_ruby_lsp(self):
        plugins, _ = resolve_plugins("rails", "standard", "ruby")
        names = {p.name for p in plugins}
        assert "ruby-lsp" in names

    def test_elixir_phoenix_has_lsp(self):
        plugins, _ = resolve_plugins("phoenix", "standard", "elixir")
        names = {p.name for p in plugins}
        assert "elixir-ls" in names


# ── V2.5 Plugin Expansion Tests ──────────────────────────────────────


class TestV25PluginExpansion:
    """V2.5: LSP, integration, workflow, style, and utility expansion."""

    def test_new_lsp_plugins_exist(self):
        new_lsp = ["elixir-ls", "scala-metals-lsp", "dart-lsp"]
        for name in new_lsp:
            assert name in PLUGIN_CATALOG, f"Missing LSP plugin {name!r}"
            assert PLUGIN_CATALOG[name].category == "lsp"

    def test_new_lsp_plugins_have_binary(self):
        new_lsp = ["elixir-ls", "scala-metals-lsp", "dart-lsp"]
        for name in new_lsp:
            assert PLUGIN_CATALOG[name].requires_binary, f"{name} missing requires_binary"

    def test_new_integration_plugins_exist(self):
        new_integ = [
            "figma",
            "stripe",
            "aws",
            "gcp",
            "azure",
            "datadog",
            "pagerduty",
            "grafana",
            "redis",
            "mongodb",
            "twilio",
            "sendgrid",
            "cloudflare",
            "docker",
            "terraform",
            "heroku",
            "railway",
            "shopify",
        ]
        for name in new_integ:
            assert name in PLUGIN_CATALOG, f"Missing integration plugin {name!r}"
            assert PLUGIN_CATALOG[name].category == "integration"

    def test_new_workflow_plugins_exist(self):
        new_wf = [
            "test-runner",
            "doc-generator",
            "perf-profiler",
            "migration-helper",
            "dependency-updater",
            "changelog-generator",
            "api-design",
        ]
        for name in new_wf:
            assert name in PLUGIN_CATALOG, f"Missing workflow plugin {name!r}"
            assert PLUGIN_CATALOG[name].category == "workflow"

    def test_new_style_plugins_exist(self):
        new_style = [
            "concise-output-style",
            "mentor-output-style",
            "team-lead-output-style",
        ]
        for name in new_style:
            assert name in PLUGIN_CATALOG, f"Missing style plugin {name!r}"
            assert PLUGIN_CATALOG[name].category == "style"

    def test_new_utility_plugins_exist(self):
        new_util = ["config-doctor", "context-optimizer"]
        for name in new_util:
            assert name in PLUGIN_CATALOG, f"Missing utility plugin {name!r}"
            assert PLUGIN_CATALOG[name].category == "utility"

    def test_elixir_language_mapping(self):
        assert LANGUAGE_PLUGINS["elixir"] == "elixir-ls"

    def test_nextjs_has_stripe(self):
        assert "stripe" in TEMPLATE_PLUGINS["nextjs"]

    def test_spring_has_aws(self):
        assert "aws" in TEMPLATE_PLUGINS["spring"]

    def test_django_has_redis(self):
        assert "redis" in TEMPLATE_PLUGINS["django"]

    def test_fastapi_has_docker(self):
        assert "docker" in TEMPLATE_PLUGINS["fastapi"]

    def test_rails_has_redis(self):
        assert "redis" in TEMPLATE_PLUGINS["rails"]

    def test_spec_driven_has_test_runner(self):
        assert "test-runner" in WORKFLOW_PLUGINS["spec-driven"]

    def test_superpowers_has_doc_generator(self):
        assert "doc-generator" in WORKFLOW_PLUGINS["superpowers"]

    def test_verify_heavy_has_test_runner_and_doc_generator(self):
        assert "test-runner" in WORKFLOW_PLUGINS["verify-heavy"]
        assert "doc-generator" in WORKFLOW_PLUGINS["verify-heavy"]

    def test_speedrun_no_test_runner(self):
        assert "test-runner" not in WORKFLOW_PLUGINS["speedrun"]

    def test_phoenix_resolve_includes_elixir_ls(self):
        plugins, _ = resolve_plugins("phoenix", "standard", "elixir")
        names = {p.name for p in plugins}
        assert "elixir-ls" in names
