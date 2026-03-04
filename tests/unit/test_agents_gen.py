"""Tests for agent file generator."""

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.agents import _AGENT_DEFS, generate_agents
from cc_rig.presets.manager import BUILTIN_WORKFLOWS

# ── Valid values for frontmatter fields ──────────────────────────────

VALID_MODELS = {"opus", "sonnet", "haiku"}

VALID_TOOLS = {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}

# Read-only agents must NOT have Write, Edit, or Bash
READ_ONLY_AGENTS = {
    "code-reviewer",
    "explorer",
    "security-auditor",
    "techdebt-hunter",
}

# Expected model per agent (from architecture: opus for deep reasoning,
# haiku for fast scanning, sonnet for everything else)
EXPECTED_MODELS = {
    "code-reviewer": "sonnet",
    "test-writer": "sonnet",
    "explorer": "haiku",
    "architect": "opus",
    "refactorer": "sonnet",
    "pr-reviewer": "opus",
    "implementer": "sonnet",
    "pm-spec": "opus",
    "security-auditor": "opus",
    "doc-writer": "sonnet",
    "techdebt-hunter": "sonnet",
    "db-reader": "sonnet",
    "parallel-worker": "sonnet",
}

WRITE_TOOLS = {"Write", "Edit", "Bash"}


def _generate_agents(template, workflow, tmp_path):
    config = compute_defaults(template, workflow, project_name="test-project")
    files = generate_agents(config, tmp_path)
    return config, files


def _parse_frontmatter(content):
    """Parse YAML frontmatter from agent markdown file.

    Returns (fields_dict, body) or raises ValueError.
    """
    if not content.startswith("---\n"):
        raise ValueError("Missing opening ---")
    end = content.index("\n---\n", 4)
    yaml_block = content[4:end]
    body = content[end + 5 :]
    fields = {}
    for line in yaml_block.splitlines():
        key, _, value = line.partition(": ")
        fields[key.strip()] = value.strip()
    return fields, body


class TestAgentFileGeneration:
    def test_correct_number_of_files(self, tmp_path):
        config, files = _generate_agents("fastapi", "standard", tmp_path)
        assert len(files) == len(config.agents)

    def test_files_exist(self, tmp_path):
        config, files = _generate_agents("fastapi", "standard", tmp_path)
        for agent in config.agents:
            path = tmp_path / ".claude" / "agents" / f"{agent}.md"
            assert path.exists(), f"Missing: {agent}.md"

    def test_files_not_empty(self, tmp_path):
        config, _ = _generate_agents("fastapi", "standard", tmp_path)
        for agent in config.agents:
            path = tmp_path / ".claude" / "agents" / f"{agent}.md"
            assert path.stat().st_size > 20, f"{agent}.md too small"

    def test_agent_has_role_description(self, tmp_path):
        config, _ = _generate_agents("fastapi", "standard", tmp_path)
        for agent in config.agents:
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            # Should have some description of role
            assert len(content.strip()) > 50, f"{agent}.md has insufficient content"


class TestAllWorkflows:
    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_agents_generated_for_workflow(self, workflow, tmp_path):
        config, files = _generate_agents("fastapi", workflow, tmp_path)
        assert len(files) == len(config.agents)
        for f in files:
            path = tmp_path / f
            assert path.exists()
            assert path.stat().st_size > 0


class TestSpecificAgents:
    def test_parallel_worker_when_worktrees(self, tmp_path):
        config, _ = _generate_agents("fastapi", "spec-driven", tmp_path)
        assert "parallel-worker" in config.agents
        path = tmp_path / ".claude" / "agents" / "parallel-worker.md"
        assert path.exists()
        content = path.read_text()
        assert "worktree" in content.lower() or "parallel" in content.lower()

    def test_verify_heavy_has_all_agents(self, tmp_path):
        config, files = _generate_agents("fastapi", "verify-heavy", tmp_path)
        # 12 base + parallel-worker
        assert len(files) >= 12


# ── Frontmatter validation tests ─────────────────────────────────────


class TestFrontmatterStructure:
    """Verify every generated agent file has valid YAML frontmatter."""

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_all_agents_have_frontmatter(self, workflow, tmp_path):
        config, _ = _generate_agents("fastapi", workflow, tmp_path)
        for agent in config.agents:
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            assert content.startswith("---\n"), f"{agent}.md missing opening frontmatter delimiter"
            assert "\n---\n" in content[4:], f"{agent}.md missing closing frontmatter delimiter"

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_all_agents_have_required_fields(self, workflow, tmp_path):
        config, _ = _generate_agents("fastapi", workflow, tmp_path)
        required = {"name", "description", "model", "tools"}
        for agent in config.agents:
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            missing = required - fields.keys()
            assert not missing, f"{agent}.md frontmatter missing fields: {missing}"

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_frontmatter_name_matches_filename(self, workflow, tmp_path):
        config, _ = _generate_agents("fastapi", workflow, tmp_path)
        for agent in config.agents:
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            assert fields["name"] == agent, (
                f"{agent}.md: name field '{fields['name']}' != filename '{agent}'"
            )

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_frontmatter_has_non_empty_body(self, workflow, tmp_path):
        config, _ = _generate_agents("fastapi", workflow, tmp_path)
        for agent in config.agents:
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            _, body = _parse_frontmatter(content)
            assert len(body.strip()) > 30, f"{agent}.md body too short ({len(body.strip())} chars)"


class TestModelAssignment:
    """Verify model field values are valid and match architectural intent."""

    @pytest.mark.parametrize("agent_name", list(_AGENT_DEFS.keys()))
    def test_model_is_valid(self, agent_name):
        defn = _AGENT_DEFS[agent_name]
        assert defn.model in VALID_MODELS, (
            f"{agent_name}: model '{defn.model}' not in {VALID_MODELS}"
        )

    @pytest.mark.parametrize("agent_name", list(EXPECTED_MODELS.keys()))
    def test_model_matches_expected(self, agent_name):
        defn = _AGENT_DEFS[agent_name]
        assert defn.model == EXPECTED_MODELS[agent_name], (
            f"{agent_name}: expected model '{EXPECTED_MODELS[agent_name]}', got '{defn.model}'"
        )

    def test_opus_agents_are_reasoning_tasks(self):
        """Opus should be reserved for agents requiring deep reasoning."""
        opus_agents = {name for name, raw in _AGENT_DEFS.items() if raw.model == "opus"}
        # These should use opus (architecture, PR decisions, specs, security)
        expected_opus = {"architect", "pr-reviewer", "pm-spec", "security-auditor"}
        assert opus_agents == expected_opus

    def test_haiku_agents_are_read_only_fast_tasks(self):
        """Haiku should only be used for fast, read-only scanning."""
        haiku_agents = {name for name, raw in _AGENT_DEFS.items() if raw.model == "haiku"}
        assert haiku_agents == {"explorer"}

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_generated_model_matches_definition(self, workflow, tmp_path):
        """Verify model in generated file matches tier-resolved model."""
        config, _ = _generate_agents("fastapi", workflow, tmp_path)
        for agent in config.agents:
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            defn = _AGENT_DEFS[agent]
            expected_model = config.model_overrides.get(agent, defn.model)
            assert fields["model"] == expected_model, (
                f"{agent}.md: generated model '{fields['model']}' "
                f"!= expected model '{expected_model}'"
            )


class TestToolRestrictions:
    """Verify tool lists are valid and enforce read-only vs write separation."""

    @pytest.mark.parametrize("agent_name", list(_AGENT_DEFS.keys()))
    def test_tools_are_valid(self, agent_name):
        defn = _AGENT_DEFS[agent_name]
        tools = {t.strip() for t in defn.tools.split(",")}
        invalid = tools - VALID_TOOLS
        assert not invalid, f"{agent_name}: invalid tools {invalid}"

    @pytest.mark.parametrize("agent_name", sorted(READ_ONLY_AGENTS))
    def test_read_only_agents_have_no_write_tools(self, agent_name):
        defn = _AGENT_DEFS[agent_name]
        tools = {t.strip() for t in defn.tools.split(",")}
        forbidden = tools & WRITE_TOOLS
        assert not forbidden, f"{agent_name} is read-only but has write tools: {forbidden}"

    @pytest.mark.parametrize("agent_name", list(_AGENT_DEFS.keys()))
    def test_all_agents_can_read(self, agent_name):
        """Every agent should at minimum have Read access."""
        defn = _AGENT_DEFS[agent_name]
        tools = {t.strip() for t in defn.tools.split(",")}
        assert "Read" in tools, f"{agent_name} missing Read tool"

    def test_write_agents_have_full_toolset(self):
        """Non-read-only agents that edit code should have Write+Edit+Bash."""
        code_writers = {
            "test-writer",
            "refactorer",
            "implementer",
            "parallel-worker",
        }
        for name in code_writers:
            defn = _AGENT_DEFS[name]
            tools = {t.strip() for t in defn.tools.split(",")}
            assert WRITE_TOOLS <= tools, f"{name} should have {WRITE_TOOLS}, has {tools}"

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_generated_tools_match_definition(self, workflow, tmp_path):
        """Verify tools in generated file match _AGENT_DEFS."""
        config, _ = _generate_agents("fastapi", workflow, tmp_path)
        for agent in config.agents:
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            defn = _AGENT_DEFS[agent]
            assert fields["tools"] == defn.tools, (
                f"{agent}.md: generated tools '{fields['tools']}' != defined tools '{defn.tools}'"
            )


class TestSpecAgentContent:
    """Validate pm-spec and implementer agent content for spec workflow."""

    def test_pm_spec_model_is_opus_on_max_tier(self, tmp_path):
        config = compute_defaults(
            "fastapi", "spec-driven", project_name="test-project", claude_plan="max"
        )
        generate_agents(config, tmp_path)
        assert "pm-spec" in config.agents
        content = (tmp_path / ".claude" / "agents" / "pm-spec.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["model"] == "opus"

    def test_pm_spec_tools_exclude_bash(self, tmp_path):
        _generate_agents("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / ".claude" / "agents" / "pm-spec.md").read_text()
        fields, _ = _parse_frontmatter(content)
        tools = {t.strip() for t in fields["tools"].split(",")}
        assert "Bash" not in tools

    def test_pm_spec_body_mentions_interview(self, tmp_path):
        _generate_agents("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / ".claude" / "agents" / "pm-spec.md").read_text()
        _, body = _parse_frontmatter(content)
        assert "interview" in body.lower()

    def test_pm_spec_body_mentions_user_stories(self, tmp_path):
        _generate_agents("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / ".claude" / "agents" / "pm-spec.md").read_text()
        _, body = _parse_frontmatter(content)
        assert "user stories" in body.lower()

    def test_pm_spec_body_mentions_acceptance_criteria(self, tmp_path):
        _generate_agents("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / ".claude" / "agents" / "pm-spec.md").read_text()
        _, body = _parse_frontmatter(content)
        assert "acceptance criteria" in body.lower()

    def test_implementer_model_is_sonnet(self, tmp_path):
        _generate_agents("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / ".claude" / "agents" / "implementer.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["model"] == "sonnet"

    def test_implementer_tools_include_bash(self, tmp_path):
        _generate_agents("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / ".claude" / "agents" / "implementer.md").read_text()
        fields, _ = _parse_frontmatter(content)
        tools = {t.strip() for t in fields["tools"].split(",")}
        assert "Bash" in tools

    def test_implementer_body_mentions_test(self, tmp_path):
        _generate_agents("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / ".claude" / "agents" / "implementer.md").read_text()
        _, body = _parse_frontmatter(content)
        assert "test" in body.lower()

    def test_spec_agents_absent_in_speedrun(self, tmp_path):
        config, _ = _generate_agents("fastapi", "speedrun", tmp_path)
        assert "pm-spec" not in config.agents
        assert "implementer" not in config.agents


class TestAgentDefConsistency:
    """Verify _AGENT_DEFS is internally consistent."""

    def test_all_agents_have_non_empty_description(self):
        for name, raw in _AGENT_DEFS.items():
            defn = raw
            assert len(defn.description) >= 10, (
                f"{name}: description too short ({len(defn.description)} chars)"
            )

    def test_all_agents_have_non_empty_body(self):
        for name, raw in _AGENT_DEFS.items():
            defn = raw
            assert len(defn.body) >= 50, f"{name}: body too short ({len(defn.body)} chars)"

    def test_no_duplicate_descriptions(self):
        descriptions = [raw.description for raw in _AGENT_DEFS.values()]
        assert len(descriptions) == len(set(descriptions)), "Duplicate descriptions"

    def test_agent_count(self):
        """Catch accidental additions/removals of agents."""
        assert len(_AGENT_DEFS) == 13


# ── Tier-aware model resolution tests ─────────────────────────────────


class TestTierAwareModelResolution:
    """Verify tier-based model overrides produce correct frontmatter."""

    def test_pro_tier_all_sonnet(self, tmp_path):
        """Pro tier overrides all non-sonnet agents to sonnet."""
        config = compute_defaults("fastapi", "verify-heavy", project_name="test", claude_plan="pro")
        generate_agents(config, tmp_path)
        for agent in config.agents:
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            assert fields["model"] == "sonnet", (
                f"{agent}: pro tier should use sonnet, got '{fields['model']}'"
            )

    def test_max_tier_uses_opus_for_deep_reasoning(self, tmp_path):
        """Max tier keeps opus for reasoning agents."""
        config = compute_defaults("fastapi", "verify-heavy", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        for agent in ("architect", "pr-reviewer", "pm-spec", "security-auditor"):
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            assert fields["model"] == "opus", (
                f"{agent}: max tier should use opus, got '{fields['model']}'"
            )

    def test_max_tier_explorer_uses_haiku(self, tmp_path):
        """Max tier keeps haiku for explorer."""
        config = compute_defaults("fastapi", "verify-heavy", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "explorer.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["model"] == "haiku"

    def test_team_tier_all_sonnet(self, tmp_path):
        """Team tier behaves same as pro — all sonnet."""
        config = compute_defaults(
            "fastapi", "verify-heavy", project_name="test", claude_plan="team"
        )
        generate_agents(config, tmp_path)
        for agent in config.agents:
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            assert fields["model"] == "sonnet", (
                f"{agent}: team tier should use sonnet, got '{fields['model']}'"
            )

    def test_enterprise_tier_same_as_max(self, tmp_path):
        """Enterprise tier keeps _AGENT_DEFS defaults (no overrides)."""
        config = compute_defaults(
            "fastapi", "verify-heavy", project_name="test", claude_plan="enterprise"
        )
        assert config.model_overrides == {}
        generate_agents(config, tmp_path)
        for agent in config.agents:
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            defn = _AGENT_DEFS[agent]
            assert fields["model"] == defn.model


# ── Optional frontmatter field tests ──────────────────────────────────


class TestOptionalFrontmatterFields:
    """Verify optional CC frontmatter fields are emitted correctly."""

    def test_parallel_worker_has_background_true(self, tmp_path):
        config = compute_defaults("fastapi", "spec-driven", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "parallel-worker.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["background"] == "true"

    def test_parallel_worker_has_isolation_worktree(self, tmp_path):
        config = compute_defaults("fastapi", "spec-driven", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "parallel-worker.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["isolation"] == "worktree"

    def test_explorer_has_plan_permission_mode(self, tmp_path):
        config = compute_defaults("fastapi", "standard", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "explorer.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["permissionMode"] == "plan"

    def test_explorer_has_max_turns(self, tmp_path):
        config = compute_defaults("fastapi", "standard", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "explorer.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["maxTurns"] == "15"

    def test_code_reviewer_has_project_memory(self, tmp_path):
        config = compute_defaults("fastapi", "standard", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "code-reviewer.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["memory"] == "project"

    def test_architect_has_project_memory(self, tmp_path):
        config = compute_defaults("fastapi", "standard", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "architect.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["memory"] == "project"

    def test_code_reviewer_has_disallowed_tools(self, tmp_path):
        config = compute_defaults("fastapi", "standard", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "code-reviewer.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["disallowedTools"] == "Write, Edit, Bash"

    def test_explorer_has_disallowed_tools(self, tmp_path):
        config = compute_defaults("fastapi", "standard", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "explorer.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["disallowedTools"] == "Write, Edit, Bash"

    def test_security_auditor_has_disallowed_tools(self, tmp_path):
        config = compute_defaults("fastapi", "verify-heavy", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "security-auditor.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["disallowedTools"] == "Write, Edit, Bash"

    def test_techdebt_hunter_has_disallowed_tools(self, tmp_path):
        config = compute_defaults("fastapi", "verify-heavy", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "techdebt-hunter.md").read_text()
        fields, _ = _parse_frontmatter(content)
        assert fields["disallowedTools"] == "Write, Edit, Bash"

    def test_write_agents_have_no_disallowed_tools(self, tmp_path):
        """Agents with write access should NOT have disallowedTools."""
        config = compute_defaults("fastapi", "verify-heavy", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        for agent in ("test-writer", "refactorer", "implementer", "architect"):
            content = (tmp_path / ".claude" / "agents" / f"{agent}.md").read_text()
            fields, _ = _parse_frontmatter(content)
            assert "disallowedTools" not in fields, f"{agent} should not have disallowedTools"

    def test_agents_without_optional_fields_omit_them(self, tmp_path):
        """Agents like test-writer should NOT have optional fields in frontmatter."""
        config = compute_defaults("fastapi", "standard", project_name="test", claude_plan="max")
        generate_agents(config, tmp_path)
        content = (tmp_path / ".claude" / "agents" / "test-writer.md").read_text()
        fields, _ = _parse_frontmatter(content)
        for optional_field in (
            "permissionMode",
            "maxTurns",
            "background",
            "isolation",
            "memory",
            "disallowedTools",
        ):
            assert optional_field not in fields, f"test-writer.md should not have {optional_field}"
