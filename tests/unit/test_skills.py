"""Tests for skills generator output: bundled fallbacks, project-patterns stub,
and download integration.

Updated for auto-install architecture: community skills are downloaded (mocked
in tests), bundled tdd/debug are fallbacks for speedrun or offline.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.skills import generate_skills
from cc_rig.skills.downloader import SkillInstallReport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate(
    tmp_path: Path,
    framework: str = "fastapi",
    language: str = "python",
    test_cmd: str = "pytest",
    workflow: str = "standard",
    template_preset: str = "",
) -> Path:
    """Generate skills into tmp_path and return it."""
    config = ProjectConfig(
        project_name="test",
        framework=framework,
        language=language,
        test_cmd=test_cmd,
        workflow=workflow,
        template_preset=template_preset or framework,
        default_mcps=["github", "postgres"],
    )
    # Mock downloads to avoid network calls — return empty report (all fail)
    with patch("cc_rig.generators.skills.download_skills") as mock_dl:
        report = SkillInstallReport()
        object.__setattr__(report, "_files", [])
        mock_dl.return_value = report
        generate_skills(config, tmp_path)
    return tmp_path


def _generate_speedrun(
    tmp_path: Path,
    framework: str = "fastapi",
    language: str = "python",
    test_cmd: str = "pytest",
) -> Path:
    """Generate skills in speedrun mode (always generates bundled tdd/debug)."""
    config = ProjectConfig(
        project_name="test",
        framework=framework,
        language=language,
        test_cmd=test_cmd,
        workflow="speedrun",
        template_preset=framework,
        default_mcps=["github", "postgres"],
    )
    # Mock downloads to avoid network calls
    with patch("cc_rig.generators.skills.download_skills") as mock_dl:
        report = SkillInstallReport()
        object.__setattr__(report, "_files", [])
        mock_dl.return_value = report
        generate_skills(config, tmp_path)
    return tmp_path


def _read_skill(tmp_path: Path, skill_name: str) -> str:
    return (tmp_path / ".claude" / "skills" / skill_name / "SKILL.md").read_text()


# ---------------------------------------------------------------------------
# Bundled TDD Fallback Content (speedrun mode) — 8 tests
# ---------------------------------------------------------------------------


class TestBundledTddContent:
    """Verify framework-specific TDD guidance in bundled fallback (speedrun)."""

    def test_tdd_fastapi(self, tmp_path):
        _generate_speedrun(tmp_path, framework="fastapi")
        content = _read_skill(tmp_path, "tdd")
        assert "TestClient" in content
        assert "starlette" in content
        assert "fastapi" in content.lower()

    def test_tdd_django(self, tmp_path):
        _generate_speedrun(tmp_path, framework="django")
        content = _read_skill(tmp_path, "tdd")
        assert "django.test.TestCase" in content

    def test_tdd_nextjs(self, tmp_path):
        _generate_speedrun(tmp_path, framework="nextjs", language="typescript")
        content = _read_skill(tmp_path, "tdd")
        assert "Jest or Vitest" in content
        assert "React Testing Library" in content

    def test_tdd_gin(self, tmp_path):
        _generate_speedrun(tmp_path, framework="gin", language="go", test_cmd="go test ./...")
        content = _read_skill(tmp_path, "tdd")
        assert "httptest.NewRecorder" in content
        assert "t.Run()" in content

    def test_tdd_echo(self, tmp_path):
        _generate_speedrun(tmp_path, framework="echo", language="go", test_cmd="go test ./...")
        content = _read_skill(tmp_path, "tdd")
        assert "echo.New()" in content

    def test_tdd_clap(self, tmp_path):
        _generate_speedrun(tmp_path, framework="clap", language="rust", test_cmd="cargo test")
        content = _read_skill(tmp_path, "tdd")
        assert "assert_cmd" in content
        assert "#[test]" in content

    def test_tdd_flask(self, tmp_path):
        _generate_speedrun(tmp_path, framework="flask")
        content = _read_skill(tmp_path, "tdd")
        assert "test_client()" in content
        assert "FlaskClient" in content

    def test_tdd_unknown_generic(self, tmp_path):
        _generate_speedrun(tmp_path, framework="unknown-framework")
        content = _read_skill(tmp_path, "tdd")
        assert "established test patterns" in content


# ---------------------------------------------------------------------------
# Bundled Debug Fallback Content (speedrun mode) — 8 tests
# ---------------------------------------------------------------------------


class TestBundledDebugContent:
    """Verify framework-specific debug guidance in bundled fallback (speedrun)."""

    def test_debug_fastapi(self, tmp_path):
        _generate_speedrun(tmp_path, framework="fastapi")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "Depends" in content or "dependency injection" in content.lower()
        assert "uvicorn" in content

    def test_debug_django(self, tmp_path):
        _generate_speedrun(tmp_path, framework="django")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "django-debug-toolbar" in content

    def test_debug_nextjs(self, tmp_path):
        _generate_speedrun(tmp_path, framework="nextjs", language="typescript")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "React DevTools" in content
        assert "ydration" in content  # "Hydration" or "hydration"

    def test_debug_gin(self, tmp_path):
        _generate_speedrun(tmp_path, framework="gin", language="go", test_cmd="go test ./...")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "DebugMode" in content
        assert "pprof" in content

    def test_debug_echo(self, tmp_path):
        _generate_speedrun(tmp_path, framework="echo", language="go", test_cmd="go test ./...")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "echo.Debug" in content or "echo" in content.lower()

    def test_debug_clap(self, tmp_path):
        _generate_speedrun(tmp_path, framework="clap", language="rust", test_cmd="cargo test")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "RUST_BACKTRACE" in content
        assert "dbg!()" in content

    def test_debug_flask(self, tmp_path):
        _generate_speedrun(tmp_path, framework="flask")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "debug=True" in content
        assert "flask shell" in content

    def test_debug_unknown_generic(self, tmp_path):
        _generate_speedrun(tmp_path, framework="unknown-framework")
        content = _read_skill(tmp_path, "systematic-debug")
        assert "standard debugging tools" in content


# ---------------------------------------------------------------------------
# Project Patterns Stub — 3 tests
# ---------------------------------------------------------------------------


class TestProjectPatternsStub:
    """Verify project-patterns stub structure and skill-creator tip."""

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


# ---------------------------------------------------------------------------
# Speedrun generates bundled tdd + debug — 4 tests
# ---------------------------------------------------------------------------


class TestSpeedrunBundledSkills:
    """Speedrun always generates bundled tdd/debug regardless of download."""

    def test_speedrun_generates_tdd(self, tmp_path):
        _generate_speedrun(tmp_path)
        assert (tmp_path / ".claude" / "skills" / "tdd" / "SKILL.md").exists()

    def test_speedrun_generates_debug(self, tmp_path):
        _generate_speedrun(tmp_path)
        assert (tmp_path / ".claude" / "skills" / "systematic-debug" / "SKILL.md").exists()

    def test_speedrun_generates_project_patterns(self, tmp_path):
        _generate_speedrun(tmp_path)
        assert (tmp_path / ".claude" / "skills" / "project-patterns" / "SKILL.md").exists()

    def test_speedrun_no_deployment_checklist(self, tmp_path):
        """deployment-checklist stub was killed."""
        _generate_speedrun(tmp_path)
        assert not (tmp_path / ".claude" / "skills" / "deployment-checklist" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# Standard+ uses downloads (mocked) — 5 tests
# ---------------------------------------------------------------------------


class TestDownloadIntegration:
    """Standard+ workflows attempt to download community skills."""

    def test_standard_calls_download(self, tmp_path):
        config = ProjectConfig(
            project_name="test",
            framework="fastapi",
            language="python",
            workflow="standard",
            template_preset="fastapi",
            default_mcps=["github", "postgres"],
        )
        with patch("cc_rig.generators.skills.download_skills") as mock_dl:
            report = SkillInstallReport()
            object.__setattr__(report, "_files", [])
            mock_dl.return_value = report
            generate_skills(config, tmp_path)
            mock_dl.assert_called_once()

    def test_successful_download_creates_files(self, tmp_path):
        config = ProjectConfig(
            project_name="test",
            framework="fastapi",
            language="python",
            workflow="standard",
            template_preset="fastapi",
            default_mcps=["github", "postgres"],
        )
        with patch("cc_rig.generators.skills.download_skills") as mock_dl:
            report = SkillInstallReport()
            object.__setattr__(report, "_files", [".claude/skills/owasp-security/SKILL.md"])
            report.installed.append("owasp-security")
            mock_dl.return_value = report
            files = generate_skills(config, tmp_path)
            assert ".claude/skills/owasp-security/SKILL.md" in files

    def test_failed_tdd_download_generates_fallback(self, tmp_path):
        """When TDD download fails for spec-driven+, fallback is generated."""
        config = ProjectConfig(
            project_name="test",
            framework="fastapi",
            language="python",
            workflow="spec-driven",
            template_preset="fastapi",
            default_mcps=["github", "postgres"],
        )
        with patch("cc_rig.generators.skills.download_skills") as mock_dl:
            report = SkillInstallReport()
            object.__setattr__(report, "_files", [])
            report.failed.append(("test-driven-development", "timeout"))
            mock_dl.return_value = report
            generate_skills(config, tmp_path)
            assert (tmp_path / ".claude" / "skills" / "tdd" / "SKILL.md").exists()

    def test_failed_debug_download_generates_fallback(self, tmp_path):
        """When debug download fails for spec-driven+, fallback is generated."""
        config = ProjectConfig(
            project_name="test",
            framework="fastapi",
            language="python",
            workflow="spec-driven",
            template_preset="fastapi",
            default_mcps=["github", "postgres"],
        )
        with patch("cc_rig.generators.skills.download_skills") as mock_dl:
            report = SkillInstallReport()
            object.__setattr__(report, "_files", [])
            report.failed.append(("systematic-debugging", "timeout"))
            mock_dl.return_value = report
            generate_skills(config, tmp_path)
            assert (tmp_path / ".claude" / "skills" / "systematic-debug" / "SKILL.md").exists()

    def test_no_recommended_skills_guide(self, tmp_path):
        """recommended-skills.md is no longer generated."""
        _generate(tmp_path)
        assert not (tmp_path / "docs" / "recommended-skills.md").exists()


# ---------------------------------------------------------------------------
# Skill packs — generate_skills() passes pack specs to download — 10 tests
# ---------------------------------------------------------------------------


class TestGenerateSkillsWithPacks:
    """Verify generate_skills() resolves and downloads pack skills."""

    def _generate_with_packs(
        self,
        tmp_path: Path,
        skill_packs: list[str],
        *,
        framework: str = "fastapi",
        workflow: str = "standard",
    ) -> tuple[list[str], list]:
        """Generate with packs, return (files_written, download_call_specs)."""
        config = ProjectConfig(
            project_name="test",
            framework=framework,
            language="python",
            test_cmd="pytest",
            workflow=workflow,
            template_preset=framework,
            default_mcps=["github", "postgres"],
            skill_packs=skill_packs,
        )
        with patch("cc_rig.generators.skills.download_skills") as mock_dl:
            report = SkillInstallReport()
            object.__setattr__(report, "_files", [])
            mock_dl.return_value = report
            files = generate_skills(config, tmp_path)
            call_specs = mock_dl.call_args[0][0] if mock_dl.called else []
            return files, call_specs

    def test_security_pack_adds_specs_to_download(self, tmp_path):
        """Security pack skills are passed to download_skills."""
        _, specs = self._generate_with_packs(tmp_path, ["security"])
        spec_names = {s.name for s in specs}
        assert "supply-chain-risk-auditor" in spec_names
        assert "variant-analysis" in spec_names
        assert "sharp-edges" in spec_names
        assert "differential-review" in spec_names

    def test_devops_pack_adds_specs_to_download(self, tmp_path):
        _, specs = self._generate_with_packs(tmp_path, ["devops"])
        spec_names = {s.name for s in specs}
        assert "iac-terraform" in spec_names
        assert "k8s-troubleshooter" in spec_names
        assert "monitoring-observability" in spec_names
        assert "gitops-workflows" in spec_names

    def test_web_quality_pack_adds_specs_to_download(self, tmp_path):
        _, specs = self._generate_with_packs(tmp_path, ["web-quality"])
        spec_names = {s.name for s in specs}
        assert "web-quality-audit" in spec_names
        assert "accessibility" in spec_names
        assert "performance" in spec_names

    def test_database_pro_pack_adds_specs_to_download(self, tmp_path):
        _, specs = self._generate_with_packs(tmp_path, ["database-pro"])
        spec_names = {s.name for s in specs}
        assert "database-migrations" in spec_names
        assert "query-efficiency-auditor" in spec_names

    def test_no_packs_same_specs_as_before(self, tmp_path):
        """Without packs, download specs are identical to old behavior."""
        _, specs_no_packs = self._generate_with_packs(tmp_path / "a", [])
        _, specs_none = self._generate_with_packs(tmp_path / "b", [])
        assert {s.name for s in specs_no_packs} == {s.name for s in specs_none}

    def test_pack_specs_include_base_specs(self, tmp_path):
        """Pack specs are added to (not replace) base specs."""
        _, specs_base = self._generate_with_packs(tmp_path / "a", [])
        _, specs_pack = self._generate_with_packs(tmp_path / "b", ["security"])
        base_names = {s.name for s in specs_base}
        pack_names = {s.name for s in specs_pack}
        assert base_names.issubset(pack_names)

    def test_multiple_packs_combine_specs(self, tmp_path):
        _, specs = self._generate_with_packs(
            tmp_path, ["security", "devops"]
        )
        spec_names = {s.name for s in specs}
        # From security
        assert "supply-chain-risk-auditor" in spec_names
        # From devops
        assert "iac-terraform" in spec_names

    def test_no_duplicate_specs_with_packs(self, tmp_path):
        _, specs = self._generate_with_packs(
            tmp_path, ["security", "devops", "web-quality", "database-pro"]
        )
        names = [s.name for s in specs]
        assert len(names) == len(set(names))

    def test_pack_bypasses_speedrun_gating(self, tmp_path):
        """Pack skills appear in specs even with speedrun workflow."""
        _, specs = self._generate_with_packs(
            tmp_path, ["security"], workflow="speedrun"
        )
        spec_names = {s.name for s in specs}
        assert "supply-chain-risk-auditor" in spec_names

    def test_project_patterns_still_generated_with_packs(self, tmp_path):
        """Project-patterns stub is always generated, even with packs."""
        files, _ = self._generate_with_packs(tmp_path, ["security"])
        assert ".claude/skills/project-patterns/SKILL.md" in files
