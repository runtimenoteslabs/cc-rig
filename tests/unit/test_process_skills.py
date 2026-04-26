"""Tests for v2 process skills: workflow-specific community skill curation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.claude_md import generate_claude_md
from cc_rig.presets.manager import BUILTIN_WORKFLOWS, load_pack, load_workflow
from cc_rig.skills.registry import (
    SKILL_CATALOG,
    WORKFLOW_PROCESS_SKILLS,
)

# ---------------------------------------------------------------------------
# WORKFLOW_PROCESS_SKILLS dict completeness
# ---------------------------------------------------------------------------


class TestWorkflowProcessSkillsDict:
    """Verify WORKFLOW_PROCESS_SKILLS has entries for all workflows."""

    def test_all_builtin_workflows_have_entry(self):
        for wf in BUILTIN_WORKFLOWS:
            assert wf in WORKFLOW_PROCESS_SKILLS, (
                f"WORKFLOW_PROCESS_SKILLS missing entry for {wf!r}"
            )

    def test_all_skill_names_exist_in_catalog(self):
        for wf, skills in WORKFLOW_PROCESS_SKILLS.items():
            for skill_name in skills:
                assert skill_name in SKILL_CATALOG, (
                    f"Process skill {skill_name!r} (workflow={wf}) not in SKILL_CATALOG"
                )

    def test_no_duplicate_skills_per_workflow(self):
        for wf, skills in WORKFLOW_PROCESS_SKILLS.items():
            assert len(skills) == len(set(skills)), f"Workflow {wf!r} has duplicate process skills"


# ---------------------------------------------------------------------------
# Per-workflow process skill counts
# ---------------------------------------------------------------------------


class TestProcessSkillCounts:
    def test_speedrun_has_no_process_skills(self):
        assert WORKFLOW_PROCESS_SKILLS["speedrun"] == []

    def test_standard_has_no_process_skills(self):
        assert WORKFLOW_PROCESS_SKILLS["standard"] == []

    def test_gstack_has_6_process_skills(self):
        assert len(WORKFLOW_PROCESS_SKILLS["gstack"]) == 6

    def test_aihero_has_7_process_skills(self):
        assert len(WORKFLOW_PROCESS_SKILLS["aihero"]) == 7

    def test_spec_driven_has_4_process_skills(self):
        assert len(WORKFLOW_PROCESS_SKILLS["spec-driven"]) == 4

    def test_superpowers_has_11_process_skills(self):
        assert len(WORKFLOW_PROCESS_SKILLS["superpowers"]) == 11

    def test_gtd_has_3_process_skills(self):
        assert len(WORKFLOW_PROCESS_SKILLS["gtd"]) == 3


# ---------------------------------------------------------------------------
# Repo attribution
# ---------------------------------------------------------------------------


class TestProcessSkillRepos:
    def test_gstack_skills_from_garrytan(self):
        for name in WORKFLOW_PROCESS_SKILLS["gstack"]:
            spec = SKILL_CATALOG[name]
            assert spec.repo == "garrytan/gstack", f"{name} not from garrytan/gstack"

    def test_aihero_skills_from_mattpocock(self):
        for name in WORKFLOW_PROCESS_SKILLS["aihero"]:
            spec = SKILL_CATALOG[name]
            assert spec.repo == "mattpocock/skills", f"{name} not from mattpocock/skills"

    def test_superpowers_skills_from_obra(self):
        for name in WORKFLOW_PROCESS_SKILLS["superpowers"]:
            spec = SKILL_CATALOG[name]
            assert spec.repo == "obra/superpowers", f"{name} not from obra/superpowers"

    def test_spec_driven_has_mixed_repos(self):
        repos = {SKILL_CATALOG[n].repo for n in WORKFLOW_PROCESS_SKILLS["spec-driven"]}
        assert len(repos) >= 2, "spec-driven should mix skills from multiple repos"

    def test_gtd_includes_planning_with_files(self):
        assert "planning-with-files" in WORKFLOW_PROCESS_SKILLS["gtd"]
        spec = SKILL_CATALOG["planning-with-files"]
        assert spec.repo == "OthmanAdi/planning-with-files"
        assert spec.branch == "master"


# ---------------------------------------------------------------------------
# compute_defaults populates process skill fields
# ---------------------------------------------------------------------------


class TestComputeDefaultsProcessSkills:
    def test_gstack_populates_process_skills(self):
        config = compute_defaults("fastapi", "gstack", project_name="test")
        assert len(config.process_skills) == 6
        assert "plan-ceo-review" in config.process_skills

    def test_speedrun_has_empty_process_skills(self):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        assert config.process_skills == []

    def test_standard_has_empty_process_skills(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert config.process_skills == []

    def test_workflow_source_gstack(self):
        config = compute_defaults("fastapi", "gstack", project_name="test")
        assert config.workflow_source == "garrytan/gstack"

    def test_workflow_source_ccrig_for_standard(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert config.workflow_source == "cc-rig"

    def test_workflow_source_url_gstack(self):
        config = compute_defaults("fastapi", "gstack", project_name="test")
        assert "github.com/garrytan/gstack" in config.workflow_source_url

    def test_workflow_source_url_empty_for_standard(self):
        config = compute_defaults("fastapi", "standard", project_name="test")
        assert config.workflow_source_url == ""

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_all_workflows_have_valid_process_skills(self, workflow):
        config = compute_defaults("generic", workflow, project_name="test")
        for skill_name in config.process_skills:
            assert skill_name in SKILL_CATALOG, f"Process skill {skill_name!r} not in SKILL_CATALOG"


# ---------------------------------------------------------------------------
# Alias resolution produces same config as canonical
# ---------------------------------------------------------------------------


class TestAliasResolution:
    def test_verify_heavy_resolves_to_superpowers(self):
        """verify-heavy resolves to the rigorous tier (superpowers is now a pack)."""
        data = load_workflow("verify-heavy")
        assert data["name"] == "rigorous"

    def test_gtd_lite_resolves_to_gtd(self):
        """gtd-lite resolves to the standard tier (gtd is now a pack)."""
        data = load_workflow("gtd-lite")
        assert data["name"] == "standard"

    def test_alias_config_matches_canonical(self):
        alias_config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        canonical_config = compute_defaults("fastapi", "superpowers", project_name="test")
        assert alias_config.workflow == canonical_config.workflow
        assert alias_config.agents == canonical_config.agents
        assert alias_config.process_skills == canonical_config.process_skills


# ---------------------------------------------------------------------------
# CLAUDE.md process skills section
# ---------------------------------------------------------------------------


class TestCLAUDEmdProcessSkills:
    @staticmethod
    def _generate(workflow: str) -> str:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            config = compute_defaults("fastapi", workflow, project_name="test", output_dir=td)
            generate_claude_md(config, tdp)
            return (tdp / "CLAUDE.md").read_text()

    def test_gstack_has_process_skills_section(self):
        content = self._generate("gstack")
        assert "## Process Skills" in content

    def test_speedrun_no_process_skills_section(self):
        content = self._generate("speedrun")
        assert "## Process Skills" not in content

    def test_standard_no_process_skills_section(self):
        content = self._generate("standard")
        assert "## Process Skills" not in content

    def test_gstack_has_attribution(self):
        content = self._generate("gstack")
        assert "garrytan/gstack" in content

    def test_aihero_has_attribution(self):
        content = self._generate("aihero")
        assert "mattpocock/skills" in content

    def test_superpowers_has_attribution(self):
        content = self._generate("superpowers")
        assert "obra/superpowers" in content

    def test_process_skills_lists_skill_names(self):
        content = self._generate("gstack")
        assert "/plan-ceo-review" in content
        assert "/ship" in content

    def test_gstack_has_full_suite_note(self):
        content = self._generate("gstack")
        assert "github.com/garrytan/gstack" in content


# ---------------------------------------------------------------------------
# Preset v2 format
# ---------------------------------------------------------------------------


class TestPresetV2Format:
    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_all_presets_have_version_field(self, workflow):
        data = load_workflow(workflow)
        assert data.get("version") == 2, f"{workflow} preset missing version=2"

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_all_presets_have_process_skills_field(self, workflow):
        data = load_workflow(workflow)
        assert "process_skills" in data, f"{workflow} preset missing process_skills"
        assert isinstance(data["process_skills"], list)

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_all_presets_have_source_field(self, workflow):
        data = load_workflow(workflow)
        assert "source" in data, f"{workflow} preset missing source"

    def test_gstack_preset_process_skills_match_registry(self):
        """gstack is now a pack; use load_pack() to get its process skills."""
        data = load_pack("gstack")
        assert data["process_skills"] == WORKFLOW_PROCESS_SKILLS["gstack"]

    def test_aihero_preset_process_skills_match_registry(self):
        """aihero is now a pack; use load_pack() to get its process skills."""
        data = load_pack("aihero")
        assert data["process_skills"] == WORKFLOW_PROCESS_SKILLS["aihero"]
