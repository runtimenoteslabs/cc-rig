"""Tests for skill resolution internals: phase filtering, pack expansion,
normalization, deduplication, and edge cases.

Covers spec scenarios S01–S04, S12 from specs/skills-test-matrix.md.
"""

from __future__ import annotations

from cc_rig.config.defaults import (
    _merge_skills,
    _normalize_skills,
    _phase_is_active,
    _resolve_skill_packs,
)
from cc_rig.config.project import SkillRecommendation

# ---------------------------------------------------------------------------
# S01: Phase Filtering (_phase_is_active) — 8 tests
# ---------------------------------------------------------------------------


class TestPhaseFiltering:
    """Direct tests for _phase_is_active()."""

    def test_true_is_active(self):
        assert _phase_is_active({"coding": True}, "coding") is True

    def test_included_string_is_active(self):
        assert _phase_is_active({"coding": "included"}, "coding") is True

    def test_false_is_inactive(self):
        assert _phase_is_active({"coding": False}, "coding") is False

    def test_reference_is_inactive(self):
        assert _phase_is_active({"security": "reference"}, "security") is False

    def test_bundled_only_is_inactive(self):
        assert _phase_is_active({"testing": "bundled_only"}, "testing") is False

    def test_if_applicable_is_inactive(self):
        assert _phase_is_active({"database": "if_applicable"}, "database") is False

    def test_absent_key_is_inactive(self):
        assert _phase_is_active({}, "coding") is False

    def test_empty_phase_name_is_inactive(self):
        assert _phase_is_active({"": True}, "") is False


# ---------------------------------------------------------------------------
# S02: Pack Expansion (_resolve_skill_packs) — 14 tests
# ---------------------------------------------------------------------------


class TestPackExpansion:
    """Direct tests for _resolve_skill_packs()."""

    # -- superpowers --

    def test_superpowers_full_expands_all_active(self):
        phases = {
            "planning": True,
            "coding": True,
            "testing": True,
            "review": True,
            "devops": True,
        }
        packs = {"superpowers": "full"}
        result = _resolve_skill_packs(packs, phases)
        result_names = {s.name for s in result if s.source == "obra/superpowers"}
        # Should include skills from all active phases
        assert "brainstorming" in result_names  # planning
        assert "dispatching-parallel-agents" in result_names  # coding
        assert "test-driven-development" in result_names  # testing
        assert "requesting-code-review" in result_names  # review
        assert "finishing-a-development-branch" in result_names  # devops

    def test_superpowers_list_expands_named(self):
        phases = {"planning": True}
        packs = {"superpowers": ["brainstorming"]}
        result = _resolve_skill_packs(packs, phases)
        superpowers = [s for s in result if s.source == "obra/superpowers"]
        assert len(superpowers) == 1
        assert superpowers[0].name == "brainstorming"

    def test_superpowers_empty_expands_none(self):
        phases = {"planning": True, "coding": True}
        packs = {"superpowers": []}
        result = _resolve_skill_packs(packs, phases)
        superpowers = [s for s in result if s.source == "obra/superpowers"]
        assert superpowers == []

    def test_superpowers_full_respects_phases(self):
        """Planning skills excluded when planning phase is inactive."""
        phases = {"coding": True, "planning": False}
        packs = {"superpowers": "full"}
        result = _resolve_skill_packs(packs, phases)
        result_names = {s.name for s in result}
        assert "brainstorming" not in result_names
        assert "writing-plans" not in result_names
        assert "executing-plans" not in result_names

    # -- trailofbits --

    def test_trailofbits_list_expands_named(self):
        phases = {"security": True}
        packs = {"trailofbits_core": ["static-analysis"]}
        result = _resolve_skill_packs(packs, phases)
        tob = [s for s in result if s.source == "trailofbits/skills"]
        assert len(tob) == 1
        assert tob[0].name == "static-analysis"

    def test_trailofbits_reference_skipped(self):
        """'reference' string means docs-only — no skills in active list."""
        phases = {"security": True}
        packs = {"trailofbits_core": "reference"}
        result = _resolve_skill_packs(packs, phases)
        tob = [s for s in result if s.source == "trailofbits/skills"]
        assert tob == []

    def test_trailofbits_empty_expands_none(self):
        phases = {"security": True}
        packs = {"trailofbits_core": []}
        result = _resolve_skill_packs(packs, phases)
        tob = [s for s in result if s.source == "trailofbits/skills"]
        assert tob == []

    # -- anthropic official --

    def test_anthropic_full_expands_all_active(self):
        phases = {"testing": True, "devops": True, "coding": True}
        packs = {"anthropic_official": "full"}
        result = _resolve_skill_packs(packs, phases)
        anthropic = [s for s in result if s.source == "anthropics/skills"]
        names = {s.name for s in anthropic}
        assert names == {"webapp-testing", "mcp-builder", "skill-creator"}

    def test_anthropic_list_expands_named(self):
        phases = {"devops": True}
        packs = {"anthropic_official": ["mcp-builder"]}
        result = _resolve_skill_packs(packs, phases)
        anthropic = [s for s in result if s.source == "anthropics/skills"]
        assert len(anthropic) == 1
        assert anthropic[0].name == "mcp-builder"

    def test_anthropic_empty_expands_none(self):
        phases = {"devops": True, "coding": True}
        packs = {"anthropic_official": []}
        result = _resolve_skill_packs(packs, phases)
        anthropic = [s for s in result if s.source == "anthropics/skills"]
        assert anthropic == []

    def test_anthropic_full_respects_phases(self):
        """mcp-builder (devops) excluded when devops phase inactive."""
        phases = {"coding": True, "testing": True, "devops": False}
        packs = {"anthropic_official": "full"}
        result = _resolve_skill_packs(packs, phases)
        names = {s.name for s in result if s.source == "anthropics/skills"}
        assert "mcp-builder" not in names
        assert "webapp-testing" in names
        assert "skill-creator" in names

    # -- OWASP --

    def test_owasp_injected_when_security_active(self):
        phases = {"security": True}
        packs = {}
        result = _resolve_skill_packs(packs, phases)
        names = {s.name for s in result}
        assert "claude-code-owasp" in names

    def test_owasp_excluded_when_security_inactive(self):
        phases = {"security": False}
        packs = {}
        result = _resolve_skill_packs(packs, phases)
        names = {s.name for s in result}
        assert "claude-code-owasp" not in names

    # -- unknown names --

    def test_unknown_skill_name_silently_skipped(self):
        phases = {"planning": True, "coding": True}
        packs = {"superpowers": ["nonexistent-skill-xyz"]}
        result = _resolve_skill_packs(packs, phases)
        superpowers = [s for s in result if s.source == "obra/superpowers"]
        assert superpowers == []


# ---------------------------------------------------------------------------
# S03: Normalization (_normalize_skills) — 5 tests
# ---------------------------------------------------------------------------


class TestNormalization:
    """Direct tests for _normalize_skills()."""

    def test_dict_converts_to_recommendation(self):
        raw = [
            {
                "name": "test-skill",
                "sdlc_phase": "coding",
                "source": "test/repo",
                "install": "npx skills add test/repo --skill test-skill",
                "description": "A test skill",
            }
        ]
        result = _normalize_skills(raw)
        assert len(result) == 1
        assert isinstance(result[0], SkillRecommendation)
        assert result[0].name == "test-skill"
        assert result[0].sdlc_phase == "coding"

    def test_bare_string_converts(self):
        raw = ["my-skill"]
        result = _normalize_skills(raw)
        assert len(result) == 1
        assert isinstance(result[0], SkillRecommendation)
        assert result[0].name == "my-skill"

    def test_recommendation_passthrough(self):
        skill = SkillRecommendation(name="existing", sdlc_phase="testing")
        raw = [skill]
        result = _normalize_skills(raw)
        assert len(result) == 1
        assert result[0] is skill

    def test_mixed_formats(self):
        raw = [
            {"name": "dict-skill", "sdlc_phase": "coding"},
            "string-skill",
            SkillRecommendation(name="obj-skill"),
        ]
        result = _normalize_skills(raw)
        assert len(result) == 3
        assert all(isinstance(s, SkillRecommendation) for s in result)
        names = [s.name for s in result]
        assert names == ["dict-skill", "string-skill", "obj-skill"]

    def test_empty_list(self):
        assert _normalize_skills([]) == []


# ---------------------------------------------------------------------------
# S04: Deduplication and Merge — 7 tests
# ---------------------------------------------------------------------------


class TestDeduplication:
    """Tests for deduplication behavior in _merge_skills()."""

    def _make_tmpl(self, skills: list[dict]) -> dict:
        return {"recommended_skills": skills, "name": "test"}

    def _make_wf(
        self,
        skill_phases: dict | None = None,
        skill_packs: dict | None = None,
    ) -> dict:
        return {
            "skill_phases": skill_phases or {},
            "skill_packs": skill_packs or {},
        }

    def test_template_skill_survives_when_no_overlap(self):
        tmpl = self._make_tmpl(
            [{"name": "modern-python", "sdlc_phase": "coding", "install": "cmd"}]
        )
        wf = self._make_wf(skill_phases={"coding": True})
        result = _merge_skills(tmpl, wf, [])
        names = {s.name for s in result}
        assert "modern-python" in names

    def test_pack_skill_overrides_template_same_name(self):
        """When template and pack both have same skill name, pack (later) wins."""
        tmpl = self._make_tmpl(
            [
                {
                    "name": "requesting-code-review",
                    "sdlc_phase": "review",
                    "source": "template-source",
                    "install": "template-install",
                }
            ]
        )
        wf = self._make_wf(
            skill_phases={"review": True},
            skill_packs={"superpowers": ["requesting-code-review"]},
        )
        result = _merge_skills(tmpl, wf, [])
        matches = [s for s in result if s.name == "requesting-code-review"]
        assert len(matches) == 1
        # Pack version wins (obra/superpowers source)
        assert matches[0].source == "obra/superpowers"

    def test_dedup_preserves_last_source(self):
        """Dedup uses last-wins — cross-cutting pack takes precedence."""
        tmpl = self._make_tmpl(
            [
                {
                    "name": "insecure-defaults",
                    "sdlc_phase": "security",
                    "source": "template",
                    "install": "old",
                }
            ]
        )
        wf = self._make_wf(
            skill_phases={"security": True},
            skill_packs={"trailofbits_core": ["insecure-defaults"]},
        )
        result = _merge_skills(tmpl, wf, [])
        matches = [s for s in result if s.name == "insecure-defaults"]
        assert len(matches) == 1
        assert matches[0].source == "trailofbits/skills"

    def test_merge_no_duplicates(self):
        """Full merge scenario should have no duplicate names."""
        tmpl = self._make_tmpl(
            [
                {"name": "a", "sdlc_phase": "coding", "install": "x"},
                {"name": "b", "sdlc_phase": "testing", "install": "y"},
            ]
        )
        wf = self._make_wf(
            skill_phases={"coding": True, "testing": True, "security": True},
            skill_packs={"superpowers": ["test-driven-development"]},
        )
        result = _merge_skills(tmpl, wf, [])
        names = [s.name for s in result]
        assert len(names) == len(set(names)), f"Duplicates found: {names}"

    def test_merge_with_empty_template_skills(self):
        tmpl = self._make_tmpl([])
        wf = self._make_wf(
            skill_phases={"coding": True},
            skill_packs={"superpowers": ["dispatching-parallel-agents"]},
        )
        result = _merge_skills(tmpl, wf, [])
        assert len(result) >= 1
        names = {s.name for s in result}
        assert "dispatching-parallel-agents" in names

    def test_merge_with_empty_packs(self):
        tmpl = self._make_tmpl([{"name": "solo", "sdlc_phase": "coding", "install": "cmd"}])
        wf = self._make_wf(skill_phases={"coding": True}, skill_packs={})
        result = _merge_skills(tmpl, wf, [])
        names = {s.name for s in result}
        assert "solo" in names

    def test_phase_filter_removes_before_dedup(self):
        """Template skill in inactive phase should be filtered out entirely."""
        tmpl = self._make_tmpl(
            [{"name": "planning-skill", "sdlc_phase": "planning", "install": "cmd"}]
        )
        wf = self._make_wf(skill_phases={"planning": False, "coding": True})
        result = _merge_skills(tmpl, wf, [])
        names = {s.name for s in result}
        assert "planning-skill" not in names


# ---------------------------------------------------------------------------
# S12: Edge Cases — 8 tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and error handling for skill resolution."""

    def test_none_phase_value(self):
        assert _phase_is_active({"coding": None}, "coding") is False

    def test_integer_phase_value(self):
        assert _phase_is_active({"coding": 1}, "coding") is False

    def test_empty_skill_packs_dict(self):
        phases = {"coding": True, "security": True}
        result = _resolve_skill_packs({}, phases)
        # Only OWASP should be injected (security active, no pack skills)
        names = {s.name for s in result}
        assert "claude-code-owasp" in names
        # No superpowers, trailofbits, or anthropic
        assert not any(s.source == "obra/superpowers" for s in result)

    def test_missing_skill_phases_key(self):
        """Workflow with no skill_phases dict should produce no pack skills."""
        wf = {"skill_packs": {"superpowers": "full"}}
        phases = wf.get("skill_phases", {})
        result = _resolve_skill_packs(wf.get("skill_packs", {}), phases)
        # No phases active → no skills pass filter (except OWASP check also fails)
        assert result == []

    def test_all_phases_false(self):
        phases = {
            "planning": False,
            "coding": False,
            "testing": False,
            "review": False,
            "security": False,
            "database": False,
            "devops": False,
        }
        packs = {"superpowers": "full", "anthropic_official": "full"}
        result = _resolve_skill_packs(packs, phases)
        assert result == []

    def test_skill_with_empty_name(self):
        """Empty name skill shouldn't crash normalization."""
        raw = [{"name": "", "sdlc_phase": "coding"}]
        result = _normalize_skills(raw)
        assert len(result) == 1
        assert result[0].name == ""

    def test_skill_with_missing_sdlc_phase(self):
        """Skill with empty phase is excluded by phase filter."""
        assert _phase_is_active({"": True}, "") is False

    def test_string_true_is_not_active(self):
        """String 'true' (not boolean True) should be inactive."""
        assert _phase_is_active({"coding": "true"}, "coding") is False
