"""Tests for ProjectConfig, Features, SkillRecommendation, and PluginRecommendation."""

import json

from cc_rig.config.project import (
    Features,
    HarnessConfig,
    PluginRecommendation,
    ProjectConfig,
    SkillRecommendation,
)
from tests.conftest import make_valid_config as _make_valid_config


class TestFeatures:
    def test_defaults(self):
        f = Features()
        assert f.memory is False
        assert f.spec_workflow is False
        assert f.gtd is False
        assert f.worktrees is False
        assert f.agents_md is False
        assert f.github_actions is False

    def test_to_dict(self):
        f = Features(memory=True, worktrees=True)
        d = f.to_dict()
        assert d == {
            "memory": True,
            "spec_workflow": False,
            "gtd": False,
            "worktrees": True,
            "agents_md": False,
            "github_actions": False,
        }

    def test_from_dict(self):
        f = Features.from_dict({"memory": True, "gtd": True})
        assert f.memory is True
        assert f.gtd is True
        assert f.spec_workflow is False
        assert f.agents_md is False
        assert f.github_actions is False

    def test_from_dict_github_actions(self):
        f = Features.from_dict({"github_actions": True})
        assert f.github_actions is True
        assert f.memory is False

    def test_round_trip(self):
        f = Features(memory=True, spec_workflow=True, gtd=False, worktrees=True)
        assert Features.from_dict(f.to_dict()) == f

    def test_round_trip_github_actions(self):
        f = Features(github_actions=True, memory=True)
        assert Features.from_dict(f.to_dict()) == f


class TestProjectConfig:
    def test_creation(self):
        config = _make_valid_config()
        assert config.project_name == "test-project"
        assert config.language == "python"
        assert config.framework == "fastapi"
        assert config.workflow == "standard"
        assert config.features.memory is True
        assert len(config.agents) == 5
        assert len(config.commands) == 8

    def test_defaults(self):
        config = ProjectConfig()
        assert config.project_name == ""
        assert config.permission_mode == "default"
        assert config.claude_plan == "pro"
        assert config.agents == []
        assert isinstance(config.features, Features)

    def test_to_dict(self):
        config = _make_valid_config()
        d = config.to_dict()
        assert d["project_name"] == "test-project"
        assert d["language"] == "python"
        assert isinstance(d["features"], dict)
        assert d["features"]["memory"] is True
        assert isinstance(d["agents"], list)
        assert isinstance(d["model_overrides"], dict)

    def test_from_dict(self):
        config = _make_valid_config()
        d = config.to_dict()
        restored = ProjectConfig.from_dict(d)
        assert restored.project_name == config.project_name
        assert restored.framework == config.framework
        assert restored.features.memory == config.features.memory
        assert restored.agents == config.agents

    def test_json_round_trip(self):
        config = _make_valid_config(model_overrides={"architect": "opus"})
        json_str = config.to_json()
        restored = ProjectConfig.from_json(json_str)
        assert restored == config

    def test_json_is_valid_json(self):
        config = _make_valid_config()
        json_str = config.to_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["project_name"] == "test-project"

    def test_from_dict_with_missing_fields(self):
        """from_dict should handle missing fields gracefully with defaults."""
        config = ProjectConfig.from_dict({"project_name": "minimal"})
        assert config.project_name == "minimal"
        assert config.language == ""
        assert config.features.memory is False
        assert config.agents == []

    def test_lists_are_independent_copies(self):
        """Ensure to_dict returns copies, not references."""
        config = _make_valid_config()
        d = config.to_dict()
        d["agents"].append("extra-agent")
        assert "extra-agent" not in config.agents


class TestSkillRecommendation:
    def test_creation(self):
        s = SkillRecommendation(
            name="modern-python",
            sdlc_phase="coding",
            source="trailofbits/skills",
            install="npx skills add trailofbits/skills --skill modern-python",
            description="Modern Python",
        )
        assert s.name == "modern-python"
        assert s.sdlc_phase == "coding"

    def test_to_dict(self):
        s = SkillRecommendation(name="test", sdlc_phase="coding")
        d = s.to_dict()
        assert d["name"] == "test"
        assert d["sdlc_phase"] == "coding"
        assert d["source"] == ""
        assert d["install"] == ""

    def test_from_dict(self):
        d = {"name": "test", "sdlc_phase": "security", "source": "foo/bar"}
        s = SkillRecommendation.from_dict(d)
        assert s.name == "test"
        assert s.sdlc_phase == "security"
        assert s.source == "foo/bar"
        assert s.install == ""

    def test_round_trip(self):
        s = SkillRecommendation(
            name="owasp",
            sdlc_phase="security",
            source="agamm/claude-code-owasp",
            install="curl ...",
            description="OWASP Top 10",
        )
        assert SkillRecommendation.from_dict(s.to_dict()) == s

    def test_defaults(self):
        s = SkillRecommendation()
        assert s.name == ""
        assert s.sdlc_phase == ""


class TestSkillBackwardCompat:
    """ProjectConfig.from_dict handles both bare strings and rich skill objects."""

    def test_from_dict_with_bare_strings(self):
        data = {"project_name": "test", "recommended_skills": ["owasp", "tdd"]}
        config = ProjectConfig.from_dict(data)
        assert len(config.recommended_skills) == 2
        assert isinstance(config.recommended_skills[0], SkillRecommendation)
        assert config.recommended_skills[0].name == "owasp"
        assert config.recommended_skills[0].sdlc_phase == ""

    def test_from_dict_with_rich_objects(self):
        data = {
            "project_name": "test",
            "recommended_skills": [
                {"name": "modern-python", "sdlc_phase": "coding", "source": "x"}
            ],
        }
        config = ProjectConfig.from_dict(data)
        assert config.recommended_skills[0].name == "modern-python"
        assert config.recommended_skills[0].sdlc_phase == "coding"

    def test_from_dict_with_mixed_formats(self):
        data = {
            "project_name": "test",
            "recommended_skills": [
                "bare-string",
                {"name": "rich-obj", "sdlc_phase": "testing"},
            ],
        }
        config = ProjectConfig.from_dict(data)
        assert len(config.recommended_skills) == 2
        assert config.recommended_skills[0].name == "bare-string"
        assert config.recommended_skills[1].name == "rich-obj"

    def test_to_dict_serializes_rich_objects(self):
        config = _make_valid_config()
        d = config.to_dict()
        assert isinstance(d["recommended_skills"][0], dict)
        assert "name" in d["recommended_skills"][0]
        assert "sdlc_phase" in d["recommended_skills"][0]

    def test_json_round_trip_with_skills(self):
        config = _make_valid_config()
        json_str = config.to_json()
        restored = ProjectConfig.from_json(json_str)
        assert restored.recommended_skills == config.recommended_skills


class TestPluginRecommendation:
    """PluginRecommendation dataclass serialization."""

    def test_creation(self):
        p = PluginRecommendation(
            name="pyright-lsp",
            category="lsp",
            description="Python LSP",
            requires_binary="pyright",
        )
        assert p.name == "pyright-lsp"
        assert p.marketplace == "claude-plugins-official"
        assert p.requires_binary == "pyright"

    def test_defaults(self):
        p = PluginRecommendation()
        assert p.name == ""
        assert p.marketplace == "claude-plugins-official"
        assert p.requires_binary == ""
        assert p.replaces_mcp == ""

    def test_to_dict(self):
        p = PluginRecommendation(name="github", category="integration", replaces_mcp="github")
        d = p.to_dict()
        assert d["name"] == "github"
        assert d["marketplace"] == "claude-plugins-official"
        assert d["replaces_mcp"] == "github"

    def test_from_dict(self):
        d = {"name": "gopls-lsp", "category": "lsp", "requires_binary": "gopls"}
        p = PluginRecommendation.from_dict(d)
        assert p.name == "gopls-lsp"
        assert p.category == "lsp"
        assert p.requires_binary == "gopls"
        assert p.marketplace == "claude-plugins-official"

    def test_round_trip(self):
        p = PluginRecommendation(
            name="github",
            marketplace="claude-plugins-official",
            category="integration",
            description="GitHub integration",
            replaces_mcp="github",
        )
        assert PluginRecommendation.from_dict(p.to_dict()) == p


class TestPluginInProjectConfig:
    """PluginRecommendation integration with ProjectConfig."""

    def test_default_is_empty_list(self):
        config = ProjectConfig()
        assert config.recommended_plugins == []

    def test_to_dict_includes_plugins(self):
        config = _make_valid_config()
        config.recommended_plugins = [PluginRecommendation(name="pyright-lsp", category="lsp")]
        d = config.to_dict()
        assert "recommended_plugins" in d
        assert len(d["recommended_plugins"]) == 1
        assert d["recommended_plugins"][0]["name"] == "pyright-lsp"

    def test_from_dict_parses_plugins(self):
        data = {
            "project_name": "test",
            "recommended_plugins": [
                {"name": "github", "category": "integration", "replaces_mcp": "github"}
            ],
        }
        config = ProjectConfig.from_dict(data)
        assert len(config.recommended_plugins) == 1
        assert config.recommended_plugins[0].name == "github"
        assert config.recommended_plugins[0].replaces_mcp == "github"

    def test_backward_compat_missing_key(self):
        """Old configs without recommended_plugins should default to empty list."""
        data = {"project_name": "test"}
        config = ProjectConfig.from_dict(data)
        assert config.recommended_plugins == []

    def test_json_round_trip_with_plugins(self):
        config = _make_valid_config()
        config.recommended_plugins = [
            PluginRecommendation(name="pyright-lsp", category="lsp"),
            PluginRecommendation(name="github", category="integration"),
        ]
        json_str = config.to_json()
        restored = ProjectConfig.from_json(json_str)
        assert restored.recommended_plugins == config.recommended_plugins


class TestHarnessRalphLoopPlugin:
    """HarnessConfig ralph_loop_plugin field."""

    def test_default_is_false(self):
        h = HarnessConfig()
        assert h.ralph_loop_plugin is False

    def test_ralph_loop_level_sets_flag(self):
        h = HarnessConfig(level="ralph-loop")
        assert h.ralph_loop_plugin is True

    def test_to_dict_includes_ralph_loop_plugin(self):
        h = HarnessConfig(level="ralph-loop")
        d = h.to_dict()
        assert d["ralph_loop_plugin"] is True

    def test_from_dict_with_ralph_loop_plugin(self):
        data = {"level": "custom", "ralph_loop_plugin": True, "task_tracking": True}
        h = HarnessConfig.from_dict(data)
        assert h.ralph_loop_plugin is True

    def test_backward_compat_missing_ralph_loop(self):
        """Old configs without ralph_loop_plugin default to False."""
        data = {"level": "none"}
        h = HarnessConfig.from_dict(data)
        assert h.ralph_loop_plugin is False

    def test_ralph_loop_preserves_individual_flags(self):
        """ralph-loop level preserves flags set before __post_init__."""
        h = HarnessConfig(
            level="ralph-loop",
            task_tracking=True,
            budget_awareness=True,
            verification_gates=False,
        )
        assert h.ralph_loop_plugin is True
        assert h.task_tracking is True
        assert h.budget_awareness is True
        assert h.verification_gates is False
