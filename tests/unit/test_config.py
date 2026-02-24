"""Tests for ProjectConfig, Features, and SkillRecommendation dataclasses."""

import json

from cc_rig.config.project import Features, ProjectConfig, SkillRecommendation
from tests.conftest import make_valid_config as _make_valid_config


class TestFeatures:
    def test_defaults(self):
        f = Features()
        assert f.memory is False
        assert f.spec_workflow is False
        assert f.gtd is False
        assert f.worktrees is False

    def test_to_dict(self):
        f = Features(memory=True, worktrees=True)
        d = f.to_dict()
        assert d == {"memory": True, "spec_workflow": False, "gtd": False, "worktrees": True}

    def test_from_dict(self):
        f = Features.from_dict({"memory": True, "gtd": True})
        assert f.memory is True
        assert f.gtd is True
        assert f.spec_workflow is False

    def test_round_trip(self):
        f = Features(memory=True, spec_workflow=True, gtd=False, worktrees=True)
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
