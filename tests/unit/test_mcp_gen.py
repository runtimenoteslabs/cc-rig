"""Tests for MCP server configuration generator."""

import json

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.mcp import _MCP_SERVERS, generate_mcp
from cc_rig.presets.manager import BUILTIN_TEMPLATES, BUILTIN_WORKFLOWS

# ── Expected MCP assignments per template ────────────────────────────

# Note: github MCP is replaced by the github plugin since v1.4.0.
# Templates that only had github MCP now have empty MCP lists.
TEMPLATE_MCPS = {
    "generic": [],
    "nextjs": ["playwright"],
    "fastapi": ["postgres"],
    "django": ["postgres"],
    "gin": ["postgres"],
    "echo": ["postgres"],
    "rust-cli": [],
    "rust-web": ["postgres"],
    "flask": ["postgres"],
    "rails": ["postgres"],
    "spring": ["postgres"],
    "dotnet": ["postgres"],
    "laravel": ["postgres"],
    "express": ["postgres"],
    "phoenix": ["postgres"],
    "go-std": ["postgres"],
}

# Templates with no MCPs after plugin replacement
_NO_MCP_TEMPLATES = {t for t, mcps in TEMPLATE_MCPS.items() if not mcps}

# Required fields per MCP server entry
REQUIRED_SERVER_FIELDS = {"command", "args", "env"}


def _generate_mcp(template, workflow, tmp_path):
    config = compute_defaults(template, workflow, project_name="test-project")
    files = generate_mcp(config, tmp_path)
    return config, files


def _read_mcp_json(tmp_path):
    return json.loads((tmp_path / ".mcp.json").read_text())


class TestMcpFileGeneration:
    """Verify .mcp.json is generated for all template × workflow combos."""

    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_mcp_file_created(self, template, tmp_path):
        _, files = _generate_mcp(template, "standard", tmp_path)
        if template in _NO_MCP_TEMPLATES:
            assert files == []
            assert not (tmp_path / ".mcp.json").exists()
        else:
            assert files == [".mcp.json"]
            assert (tmp_path / ".mcp.json").exists()

    @pytest.mark.parametrize(
        "template",
        [t for t in BUILTIN_TEMPLATES if t not in _NO_MCP_TEMPLATES],
    )
    def test_mcp_file_is_valid_json(self, template, tmp_path):
        _generate_mcp(template, "standard", tmp_path)
        data = _read_mcp_json(tmp_path)
        assert isinstance(data, dict)

    def test_empty_mcps_produces_no_file(self, tmp_path):
        from tests.conftest import make_valid_config

        config = make_valid_config(default_mcps=[])
        files = generate_mcp(config, tmp_path)
        assert files == []
        assert not (tmp_path / ".mcp.json").exists()


_TEMPLATES_WITH_MCPS = [t for t in BUILTIN_TEMPLATES if t not in _NO_MCP_TEMPLATES]


class TestMcpSchema:
    """Verify the MCP JSON structure matches Claude Code's expected schema."""

    @pytest.mark.parametrize("template", _TEMPLATES_WITH_MCPS)
    def test_has_mcpServers_key(self, template, tmp_path):
        _generate_mcp(template, "standard", tmp_path)
        data = _read_mcp_json(tmp_path)
        assert "mcpServers" in data
        assert isinstance(data["mcpServers"], dict)

    @pytest.mark.parametrize("template", _TEMPLATES_WITH_MCPS)
    def test_no_extra_top_level_keys(self, template, tmp_path):
        _generate_mcp(template, "standard", tmp_path)
        data = _read_mcp_json(tmp_path)
        assert set(data.keys()) == {"mcpServers"}

    @pytest.mark.parametrize("template", _TEMPLATES_WITH_MCPS)
    def test_server_entries_have_required_fields(self, template, tmp_path):
        _generate_mcp(template, "standard", tmp_path)
        data = _read_mcp_json(tmp_path)
        for name, server in data["mcpServers"].items():
            missing = REQUIRED_SERVER_FIELDS - set(server.keys())
            assert not missing, f"Server '{name}' missing fields: {missing}"

    @pytest.mark.parametrize("template", _TEMPLATES_WITH_MCPS)
    def test_command_is_string(self, template, tmp_path):
        _generate_mcp(template, "standard", tmp_path)
        data = _read_mcp_json(tmp_path)
        for name, server in data["mcpServers"].items():
            assert isinstance(server["command"], str), f"Server '{name}': command should be string"

    @pytest.mark.parametrize("template", _TEMPLATES_WITH_MCPS)
    def test_args_is_list_of_strings(self, template, tmp_path):
        _generate_mcp(template, "standard", tmp_path)
        data = _read_mcp_json(tmp_path)
        for name, server in data["mcpServers"].items():
            assert isinstance(server["args"], list), f"Server '{name}': args should be list"
            for arg in server["args"]:
                assert isinstance(arg, str), f"Server '{name}': arg '{arg}' should be string"

    @pytest.mark.parametrize("template", _TEMPLATES_WITH_MCPS)
    def test_env_is_dict_of_strings(self, template, tmp_path):
        _generate_mcp(template, "standard", tmp_path)
        data = _read_mcp_json(tmp_path)
        for name, server in data["mcpServers"].items():
            assert isinstance(server["env"], dict), f"Server '{name}': env should be dict"
            for key, val in server["env"].items():
                assert isinstance(key, str) and isinstance(val, str), (
                    f"Server '{name}': env entry '{key}' should be str:str"
                )


class TestMcpServerAssignment:
    """Verify correct MCP servers are assigned per template."""

    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_template_has_expected_mcps(self, template, tmp_path):
        config, _ = _generate_mcp(template, "standard", tmp_path)
        expected = TEMPLATE_MCPS[template]
        assert sorted(config.default_mcps) == sorted(expected), (
            f"{template}: expected MCPs {expected}, got {config.default_mcps}"
        )

    @pytest.mark.parametrize("template", _TEMPLATES_WITH_MCPS)
    def test_generated_servers_match_config(self, template, tmp_path):
        config, _ = _generate_mcp(template, "standard", tmp_path)
        data = _read_mcp_json(tmp_path)
        assert sorted(data["mcpServers"].keys()) == sorted(config.default_mcps)

    def test_github_mcp_replaced_by_plugin(self):
        """GitHub MCP is replaced by github plugin — no template has github MCP."""
        for template in BUILTIN_TEMPLATES:
            assert "github" not in TEMPLATE_MCPS[template], (
                f"{template} still has github MCP (should be replaced by plugin)"
            )

    def test_db_templates_include_postgres(self):
        """Templates with database backends should include postgres."""
        db_templates = ["fastapi", "django", "flask", "gin", "echo"]
        for template in db_templates:
            assert "postgres" in TEMPLATE_MCPS[template], f"{template} should have postgres MCP"

    def test_nextjs_includes_playwright(self):
        assert "playwright" in TEMPLATE_MCPS["nextjs"]

    def test_rust_cli_has_no_db(self):
        assert "postgres" not in TEMPLATE_MCPS["rust-cli"]

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_mcps_same_across_workflows(self, workflow, tmp_path):
        """MCP assignment is template-driven, not workflow-driven."""
        config, _ = _generate_mcp("fastapi", workflow, tmp_path)
        assert sorted(config.default_mcps) == ["postgres"]


class TestMcpServerDefinitions:
    """Verify the _MCP_SERVERS registry is well-formed."""

    @pytest.mark.parametrize("name", list(_MCP_SERVERS.keys()))
    def test_server_has_required_fields(self, name):
        server = _MCP_SERVERS[name]
        missing = REQUIRED_SERVER_FIELDS - set(server.keys())
        assert not missing, f"Server def '{name}' missing: {missing}"

    @pytest.mark.parametrize("name", list(_MCP_SERVERS.keys()))
    def test_server_command_is_npx(self, name):
        """All built-in MCP servers should use npx as the command."""
        assert _MCP_SERVERS[name]["command"] == "npx"

    @pytest.mark.parametrize("name", list(_MCP_SERVERS.keys()))
    def test_server_args_start_with_dash_y(self, name):
        """All npx-based servers should have -y flag for auto-install."""
        args = _MCP_SERVERS[name]["args"]
        assert args[0] == "-y", f"Server '{name}' args missing -y flag"

    @pytest.mark.parametrize("name", list(_MCP_SERVERS.keys()))
    def test_server_args_have_package_name(self, name):
        """Second arg should be an npm package name (contains /)."""
        args = _MCP_SERVERS[name]["args"]
        assert len(args) >= 2, f"Server '{name}' needs at least 2 args"
        assert "/" in args[1], f"Server '{name}' second arg '{args[1]}' doesn't look like a package"

    def test_known_server_count(self):
        """Guard against accidental additions/removals."""
        assert len(_MCP_SERVERS) == 7

    def test_all_template_mcps_are_defined(self):
        """Every MCP referenced by templates must exist in _MCP_SERVERS."""
        all_mcps = set()
        for mcps in TEMPLATE_MCPS.values():
            all_mcps.update(mcps)
        undefined = all_mcps - set(_MCP_SERVERS.keys())
        assert not undefined, f"Templates reference undefined MCPs: {undefined}"


class TestMcpDeepCopy:
    """Verify server definitions are deep-copied, not shared references."""

    def test_generated_servers_are_independent(self, tmp_path):
        _generate_mcp("fastapi", "standard", tmp_path)
        data1 = _read_mcp_json(tmp_path)

        # Mutate returned data — should not affect next generation
        data1["mcpServers"]["postgres"]["env"]["HACKED"] = "true"

        _generate_mcp("fastapi", "standard", tmp_path)
        data2 = _read_mcp_json(tmp_path)
        assert "HACKED" not in data2["mcpServers"]["postgres"]["env"]

    def test_registry_not_mutated_by_generation(self, tmp_path):
        original_keys = set(_MCP_SERVERS["postgres"]["env"].keys())
        _generate_mcp("fastapi", "standard", tmp_path)
        assert set(_MCP_SERVERS["postgres"]["env"].keys()) == original_keys
