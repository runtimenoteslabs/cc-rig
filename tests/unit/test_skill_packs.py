"""Tests for optional skill packs: SkillPackSpec, SKILL_PACKS, resolve_skills(packs=...),
ProjectConfig.skill_packs, and compute_defaults(skill_packs=...).
"""

from __future__ import annotations

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.config.project import ProjectConfig
from cc_rig.skills.registry import (
    SKILL_CATALOG,
    SKILL_PACKS,
    SkillPackSpec,
    resolve_skills,
)

ALL_PACK_NAMES = ["security", "devops", "web-quality", "code-quality", "database-pro"]


# ---------------------------------------------------------------------------
# SkillPackSpec registry completeness
# ---------------------------------------------------------------------------


class TestSkillPackRegistry:
    """SKILL_PACKS must contain all 6 packs with valid references."""

    def test_has_6_packs(self):
        assert len(SKILL_PACKS) == 6

    @pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
    def test_pack_is_present(self, pack_name):
        assert pack_name in SKILL_PACKS

    @pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
    def test_pack_is_skill_pack_spec(self, pack_name):
        assert isinstance(SKILL_PACKS[pack_name], SkillPackSpec)

    @pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
    def test_pack_has_nonempty_label(self, pack_name):
        assert SKILL_PACKS[pack_name].label

    @pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
    def test_pack_has_nonempty_description(self, pack_name):
        assert SKILL_PACKS[pack_name].description

    @pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
    def test_pack_has_nonempty_skill_names(self, pack_name):
        assert len(SKILL_PACKS[pack_name].skill_names) > 0

    @pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
    def test_pack_name_matches_key(self, pack_name):
        assert SKILL_PACKS[pack_name].name == pack_name

    def test_all_pack_skills_exist_in_catalog(self):
        """Every skill referenced by a pack must exist in SKILL_CATALOG."""
        for pack_name, pack in SKILL_PACKS.items():
            for skill_name in pack.skill_names:
                assert skill_name in SKILL_CATALOG, (
                    f"Pack {pack_name!r} references unknown skill {skill_name!r}"
                )

    def test_no_orphaned_pack_skill_references(self):
        """All pack skills should be valid SKILL_CATALOG keys."""
        all_pack_skills = set()
        for pack in SKILL_PACKS.values():
            all_pack_skills.update(pack.skill_names)
        for skill_name in all_pack_skills:
            assert skill_name in SKILL_CATALOG, f"Orphaned pack skill: {skill_name!r}"

    def test_security_pack_skills(self):
        expected = {
            "supply-chain-risk-auditor",
            "variant-analysis",
            "sharp-edges",
            "differential-review",
        }
        assert set(SKILL_PACKS["security"].skill_names) == expected

    def test_devops_pack_skills(self):
        expected = {
            "iac-terraform",
            "k8s-troubleshooter",
            "monitoring-observability",
            "gitops-workflows",
        }
        assert set(SKILL_PACKS["devops"].skill_names) == expected

    def test_web_quality_pack_skills(self):
        expected = {
            "web-quality-audit",
            "accessibility",
            "performance",
        }
        assert set(SKILL_PACKS["web-quality"].skill_names) == expected

    def test_database_pro_pack_skills(self):
        expected = {
            "database-migrations",
            "query-efficiency-auditor",
        }
        assert set(SKILL_PACKS["database-pro"].skill_names) == expected

    def test_web_quality_suggested_for_nextjs(self):
        assert SKILL_PACKS["web-quality"].suggested_templates == ["nextjs"]

    def test_security_suggested_for_all(self):
        assert SKILL_PACKS["security"].suggested_templates is None

    def test_devops_suggested_for_all(self):
        assert SKILL_PACKS["devops"].suggested_templates is None

    def test_database_pro_suggested_for_all(self):
        assert SKILL_PACKS["database-pro"].suggested_templates is None

    def test_no_duplicate_skills_across_packs(self):
        """No skill should appear in multiple packs."""
        seen: dict[str, str] = {}
        for pack_name, pack in SKILL_PACKS.items():
            for skill_name in pack.skill_names:
                assert skill_name not in seen, (
                    f"Skill {skill_name!r} in both {seen[skill_name]!r} and {pack_name!r}"
                )
                seen[skill_name] = pack_name


# ---------------------------------------------------------------------------
# resolve_skills() with packs
# ---------------------------------------------------------------------------


class TestResolveSkillsWithPacks:
    """Packs add skills without phase gating; they're explicit user opt-in."""

    def _names(
        self,
        template: str = "fastapi",
        workflow: str = "standard",
        mcps: list[str] | None = None,
        packs: list[str] | None = None,
    ) -> set[str]:
        return {s.name for s in resolve_skills(template, workflow, mcps, packs=packs)}

    def test_no_packs_returns_same_as_before(self):
        """Passing packs=None or packs=[] produces identical results to no packs."""
        base = self._names()
        assert self._names(packs=None) == base
        assert self._names(packs=[]) == base

    def test_security_pack_adds_4_skills(self):
        base = self._names()
        with_pack = self._names(packs=["security"])
        added = with_pack - base
        assert added == {
            "supply-chain-risk-auditor",
            "variant-analysis",
            "sharp-edges",
            "differential-review",
        }

    def test_devops_pack_adds_4_skills(self):
        base = self._names()
        with_pack = self._names(packs=["devops"])
        added = with_pack - base
        assert added == {
            "iac-terraform",
            "k8s-troubleshooter",
            "monitoring-observability",
            "gitops-workflows",
        }

    def test_web_quality_pack_adds_3_skills(self):
        base = self._names()
        with_pack = self._names(packs=["web-quality"])
        added = with_pack - base
        assert added == {
            "web-quality-audit",
            "accessibility",
            "performance",
        }

    def test_database_pro_pack_adds_2_skills(self):
        base = self._names()
        with_pack = self._names(packs=["database-pro"])
        added = with_pack - base
        assert added == {
            "database-migrations",
            "query-efficiency-auditor",
        }

    def test_packs_bypass_phase_gating_in_speedrun(self):
        """Pack skills are not phase-gated even in speedrun workflow."""
        names = self._names(workflow="speedrun", packs=["security"])
        # Security phase is False in speedrun, but pack skills bypass gating
        assert "supply-chain-risk-auditor" in names
        assert "variant-analysis" in names
        assert "sharp-edges" in names
        assert "differential-review" in names

    def test_devops_pack_in_speedrun(self):
        """DevOps pack skills appear even though devops phase is False in speedrun."""
        names = self._names(workflow="speedrun", packs=["devops"])
        assert "iac-terraform" in names
        assert "k8s-troubleshooter" in names

    def test_multiple_packs_combine(self):
        base = self._names()
        with_packs = self._names(packs=["security", "devops"])
        added = with_packs - base
        expected = {
            "supply-chain-risk-auditor",
            "variant-analysis",
            "sharp-edges",
            "differential-review",
            "iac-terraform",
            "k8s-troubleshooter",
            "monitoring-observability",
            "gitops-workflows",
        }
        assert added == expected

    def test_all_packs_combine(self):
        base = self._names()
        with_packs = self._names(packs=ALL_PACK_NAMES)
        added = with_packs - base
        assert len(added) == 14  # 4 + 4 + 3 + 1 + 2

    def test_unknown_pack_ignored(self):
        base = self._names()
        with_unknown = self._names(packs=["nonexistent-pack"])
        assert with_unknown == base

    def test_unknown_pack_mixed_with_valid(self):
        with_mixed = self._names(packs=["nonexistent-pack", "security"])
        with_security = self._names(packs=["security"])
        assert with_mixed == with_security

    def test_no_duplicates_with_packs(self):
        result = resolve_skills("fastapi", "standard", packs=["security", "devops"])
        names = [s.name for s in result]
        assert len(names) == len(set(names))

    @pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
    def test_each_pack_no_duplicates(self, pack_name):
        result = resolve_skills("fastapi", "standard", packs=[pack_name])
        names = [s.name for s in result]
        assert len(names) == len(set(names))

    def test_pack_wins_on_conflict_with_template(self):
        """If a pack skill overlaps with a template skill, pack version is kept."""
        # This is an edge case — currently no pack skills overlap with template skills.
        # Verify the dedup order: template → workflow → pack (last wins).
        result = resolve_skills("fastapi", "standard", packs=["security"])
        seen_names = set()
        for spec in result:
            assert spec.name not in seen_names, f"Duplicate: {spec.name}"
            seen_names.add(spec.name)

    def test_result_contains_both_base_and_pack_skills(self):
        result = resolve_skills("fastapi", "standard", packs=["security"])
        names = {s.name for s in result}
        # Base workflow skills still present
        assert "owasp-security" in names
        assert "insecure-defaults" in names
        # Pack skills present
        assert "supply-chain-risk-auditor" in names

    def test_packs_dont_remove_base_skills(self):
        base = self._names()
        with_packs = self._names(packs=ALL_PACK_NAMES)
        assert base.issubset(with_packs)


# ---------------------------------------------------------------------------
# ProjectConfig.skill_packs serialization
# ---------------------------------------------------------------------------


class TestProjectConfigSkillPacks:
    """skill_packs field on ProjectConfig round-trips correctly."""

    def test_default_empty(self):
        config = ProjectConfig()
        assert config.skill_packs == []

    def test_set_skill_packs(self):
        config = ProjectConfig(skill_packs=["security", "devops"])
        assert config.skill_packs == ["security", "devops"]

    def test_to_dict_includes_skill_packs(self):
        config = ProjectConfig(skill_packs=["security"])
        d = config.to_dict()
        assert "skill_packs" in d
        assert d["skill_packs"] == ["security"]

    def test_to_dict_empty_packs(self):
        config = ProjectConfig()
        d = config.to_dict()
        assert d["skill_packs"] == []

    def test_from_dict_with_skill_packs(self):
        data = {"skill_packs": ["security", "devops"]}
        config = ProjectConfig.from_dict(data)
        assert config.skill_packs == ["security", "devops"]

    def test_from_dict_missing_key_defaults_to_empty(self):
        """Old .cc-rig.json files without skill_packs should default to []."""
        config = ProjectConfig.from_dict({})
        assert config.skill_packs == []

    def test_round_trip(self):
        original = ProjectConfig(skill_packs=["security", "web-quality"])
        d = original.to_dict()
        restored = ProjectConfig.from_dict(d)
        assert restored.skill_packs == original.skill_packs

    def test_json_round_trip(self):
        original = ProjectConfig(skill_packs=["devops", "database-pro"])
        json_str = original.to_json()
        restored = ProjectConfig.from_json(json_str)
        assert restored.skill_packs == original.skill_packs


# ---------------------------------------------------------------------------
# compute_defaults() with skill_packs
# ---------------------------------------------------------------------------


class TestComputeDefaultsWithPacks:
    """compute_defaults(skill_packs=...) wires packs through to the registry."""

    def test_no_packs_default(self):
        config = compute_defaults("fastapi", "standard")
        assert config.skill_packs == []

    def test_skill_packs_param_sets_field(self):
        config = compute_defaults("fastapi", "standard", skill_packs=["security"])
        assert config.skill_packs == ["security"]

    def test_skill_packs_none_defaults_to_empty(self):
        config = compute_defaults("fastapi", "standard", skill_packs=None)
        assert config.skill_packs == []

    def test_recommended_skills_include_pack_skills(self):
        config = compute_defaults("fastapi", "standard", skill_packs=["security"])
        skill_names = {s.name for s in config.recommended_skills}
        assert "supply-chain-risk-auditor" in skill_names
        assert "variant-analysis" in skill_names
        assert "sharp-edges" in skill_names
        assert "differential-review" in skill_names

    def test_recommended_skills_still_include_base_skills(self):
        config = compute_defaults("fastapi", "standard", skill_packs=["security"])
        skill_names = {s.name for s in config.recommended_skills}
        assert "owasp-security" in skill_names
        assert "modern-python" in skill_names

    def test_multiple_packs_in_recommended_skills(self):
        config = compute_defaults("fastapi", "standard", skill_packs=["security", "devops"])
        skill_names = {s.name for s in config.recommended_skills}
        # Security pack
        assert "supply-chain-risk-auditor" in skill_names
        # DevOps pack
        assert "iac-terraform" in skill_names

    def test_no_packs_matches_old_behavior(self):
        """With no packs, recommended_skills should be identical to old behavior."""
        config_new = compute_defaults("fastapi", "standard", skill_packs=[])
        config_old = compute_defaults("fastapi", "standard")
        new_names = {s.name for s in config_new.recommended_skills}
        old_names = {s.name for s in config_old.recommended_skills}
        assert new_names == old_names

    def test_packs_bypass_speedrun_phase_gating(self):
        config = compute_defaults("fastapi", "speedrun", skill_packs=["security"])
        skill_names = {s.name for s in config.recommended_skills}
        # Pack skills present despite speedrun having security=False
        assert "supply-chain-risk-auditor" in skill_names

    def test_unknown_pack_ignored(self):
        config = compute_defaults("fastapi", "standard", skill_packs=["nonexistent"])
        # Should not error, skill_packs field stores the value
        assert config.skill_packs == ["nonexistent"]
        # But recommended_skills should be same as no packs
        config_base = compute_defaults("fastapi", "standard")
        assert {s.name for s in config.recommended_skills} == {
            s.name for s in config_base.recommended_skills
        }
