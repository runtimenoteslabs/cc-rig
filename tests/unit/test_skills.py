"""Tests for skills generator output: Tier 1 content, Tier 3 stubs,
and recommended skills guide.

Covers spec scenarios S07–S09 from specs/skills-test-matrix.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.config.project import ProjectConfig, SkillRecommendation
from cc_rig.generators.skills import generate_skills

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate(
    tmp_path: Path,
    framework: str = "fastapi",
    language: str = "python",
    test_cmd: str = "pytest",
    recommended_skills: list[SkillRecommendation] | None = None,
    workflow: str = "standard",
) -> Path:
    """Generate skills into tmp_path and return it."""
    config = ProjectConfig(
        project_name="test",
        framework=framework,
        language=language,
        test_cmd=test_cmd,
        workflow=workflow,
        recommended_skills=recommended_skills or [],
    )
    generate_skills(config, tmp_path)
    return tmp_path


def _read_skill(tmp_path: Path, skill_name: str) -> str:
    return (tmp_path / ".claude" / "skills" / skill_name / "SKILL.md").read_text()


# ---------------------------------------------------------------------------
# S07: Tier 1 TDD Content — 8 tests
# ---------------------------------------------------------------------------


class TestTier1TddContent:
    """Verify framework-specific TDD guidance per template."""

    def test_tdd_fastapi(self, tmp_path):
        _generate(tmp_path, framework="fastapi")
        content = _read_skill(tmp_path, "tdd")
        assert "TestClient" in content
        assert "starlette" in content
        assert "fastapi" in content.lower()

    def test_tdd_django(self, tmp_path):
        _generate(tmp_path, framework="django")
        content = _read_skill(tmp_path, "tdd")
        assert "django.test.TestCase" in content

    def test_tdd_nextjs(self, tmp_path):
        _generate(tmp_path, framework="nextjs", language="typescript")
        content = _read_skill(tmp_path, "tdd")
        assert "Jest or Vitest" in content
        assert "React Testing Library" in content

    def test_tdd_gin(self, tmp_path):
        _generate(tmp_path, framework="gin", language="go", test_cmd="go test ./...")
        content = _read_skill(tmp_path, "tdd")
        assert "httptest.NewRecorder" in content
        assert "t.Run()" in content

    def test_tdd_echo(self, tmp_path):
        _generate(tmp_path, framework="echo", language="go", test_cmd="go test ./...")
        content = _read_skill(tmp_path, "tdd")
        assert "echo.New()" in content

    def test_tdd_clap(self, tmp_path):
        _generate(tmp_path, framework="clap", language="rust", test_cmd="cargo test")
        content = _read_skill(tmp_path, "tdd")
        assert "assert_cmd" in content
        assert "#[test]" in content

    def test_tdd_flask(self, tmp_path):
        _generate(tmp_path, framework="flask")
        content = _read_skill(tmp_path, "tdd")
        assert "test_client()" in content
        assert "FlaskClient" in content

    def test_tdd_unknown_generic(self, tmp_path):
        _generate(tmp_path, framework="unknown-framework")
        content = _read_skill(tmp_path, "tdd")
        assert "established test patterns" in content


# ---------------------------------------------------------------------------
# S07: Tier 1 Debug Content — 8 tests
# ---------------------------------------------------------------------------


class TestTier1DebugContent:
    """Verify framework-specific debug guidance per template."""

    def test_debug_fastapi(self, tmp_path):
        _generate(tmp_path, framework="fastapi")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "Depends" in content or "dependency injection" in content.lower()
        assert "uvicorn" in content

    def test_debug_django(self, tmp_path):
        _generate(tmp_path, framework="django")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "django-debug-toolbar" in content

    def test_debug_nextjs(self, tmp_path):
        _generate(tmp_path, framework="nextjs", language="typescript")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "React DevTools" in content
        assert "ydration" in content  # "Hydration" or "hydration"

    def test_debug_gin(self, tmp_path):
        _generate(tmp_path, framework="gin", language="go", test_cmd="go test ./...")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "DebugMode" in content
        assert "pprof" in content

    def test_debug_echo(self, tmp_path):
        _generate(tmp_path, framework="echo", language="go", test_cmd="go test ./...")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "echo.Debug" in content or "echo" in content.lower()

    def test_debug_clap(self, tmp_path):
        _generate(tmp_path, framework="clap", language="rust", test_cmd="cargo test")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "RUST_BACKTRACE" in content
        assert "dbg!()" in content

    def test_debug_flask(self, tmp_path):
        _generate(tmp_path, framework="flask")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "debug=True" in content
        assert "flask shell" in content

    def test_debug_unknown_generic(self, tmp_path):
        _generate(tmp_path, framework="unknown-framework")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "standard debugging tools" in content


# ---------------------------------------------------------------------------
# S08: Tier 3 Stub Content — 6 tests
# ---------------------------------------------------------------------------


class TestTier3Stubs:
    """Verify Tier 3 stub structure and skill-creator tip."""

    def test_project_patterns_has_sections(self, tmp_path):
        _generate(tmp_path)
        content = _read_skill(tmp_path, "project-patterns")
        assert "## Naming Conventions" in content
        assert "## Architecture Patterns" in content
        assert "## Code Organization" in content

    def test_project_patterns_has_skill_creator_tip(self, tmp_path):
        _generate(tmp_path)
        content = _read_skill(tmp_path, "project-patterns")
        assert "skill-creator" in content
        assert "## Tip" in content

    def test_project_patterns_is_stub(self, tmp_path):
        _generate(tmp_path)
        content = _read_skill(tmp_path, "project-patterns")
        assert "(Add your" in content

    def test_deployment_checklist_has_sections(self, tmp_path):
        _generate(tmp_path)
        content = _read_skill(tmp_path, "deployment-checklist")
        assert "## Pre-Deploy" in content
        assert "## Deploy Steps" in content
        assert "## Post-Deploy" in content

    def test_deployment_checklist_has_skill_creator_tip(self, tmp_path):
        _generate(tmp_path)
        content = _read_skill(tmp_path, "deployment-checklist")
        assert "skill-creator" in content
        assert "## Tip" in content

    def test_deployment_checklist_is_stub(self, tmp_path):
        _generate(tmp_path)
        content = _read_skill(tmp_path, "deployment-checklist")
        assert "(Add " in content


# ---------------------------------------------------------------------------
# S09: Recommended Skills Guide — 10 tests
# ---------------------------------------------------------------------------


class TestRecommendedSkillsGuide:
    """Verify generated docs/recommended-skills.md content."""

    @pytest.fixture()
    def guide_content(self, tmp_path) -> str:
        """Generate a standard fastapi config and return guide content."""
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_skills(config, tmp_path)
        return (tmp_path / "docs" / "recommended-skills.md").read_text()

    def test_guide_header_mentions_framework(self, guide_content):
        assert "fastapi" in guide_content

    def test_guide_header_mentions_workflow(self, guide_content):
        assert "standard" in guide_content

    def test_guide_groups_by_phase(self, guide_content):
        assert "## Coding" in guide_content
        assert "## Testing" in guide_content
        assert "## Security" in guide_content

    def test_guide_phase_ordering(self, guide_content):
        """Phases should appear in SDLC order."""
        coding_pos = guide_content.index("## Coding")
        testing_pos = guide_content.index("## Testing")
        review_pos = guide_content.index("## Review")
        security_pos = guide_content.index("## Security")
        assert coding_pos < testing_pos < review_pos < security_pos

    def test_guide_has_install_commands(self, guide_content):
        assert "```bash" in guide_content
        assert "npx skills add" in guide_content

    def test_guide_has_discovery_links(self, guide_content):
        assert "skills.sh" in guide_content
        assert "awesome-claude-code" in guide_content
        assert "awesome-claude-skills" in guide_content

    def test_guide_no_empty_phases(self, guide_content):
        """Each phase header should have at least one skill under it."""
        import re

        # Split into sections by ## headers
        sections = re.split(r"^## ", guide_content, flags=re.MULTILINE)
        for section in sections:
            if not section.strip() or section.startswith("Discover More"):
                continue
            # Skip the preamble (before first ## header)
            if section.startswith("# "):
                continue
            # Each phase section should contain at least one ### skill entry
            header = section.split("\n", 1)[0]
            assert "###" in section, f"Empty phase section: ## {header}"

    def test_guide_not_generated_when_no_skills(self, tmp_path):
        """Config with empty recommended_skills produces no guide file."""
        config = ProjectConfig(
            project_name="test",
            framework="fastapi",
            language="python",
            recommended_skills=[],
        )
        generate_skills(config, tmp_path)
        assert not (tmp_path / "docs" / "recommended-skills.md").exists()

    def test_guide_skill_count_matches_config(self, tmp_path):
        """Number of ### entries should match config.recommended_skills count."""
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_skills(config, tmp_path)
        content = (tmp_path / "docs" / "recommended-skills.md").read_text()
        h3_count = content.count("### ")
        assert h3_count == len(config.recommended_skills)

    def test_guide_all_skills_have_descriptions(self, tmp_path):
        """Every skill in the guide should have a description line."""
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_skills(config, tmp_path)
        content = (tmp_path / "docs" / "recommended-skills.md").read_text()
        for skill in config.recommended_skills:
            if skill.description:
                assert skill.description in content, f"Missing description for {skill.name}"
