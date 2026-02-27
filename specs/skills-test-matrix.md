# Spec: Skills Test Matrix for cc-rig

**Author**: cc-rig
**Date**: 2026-02-27
**Status**: Implemented

## Summary

Comprehensive test coverage for cc-rig's skills system: phase filtering, pack expansion, normalization, deduplication, template-specific skills, generator output (Tier 1/3), recommended skills guide, and edge cases. 110 tests across 12 scenarios in 3 test files.

## Implementation

**Test files**:
- `tests/unit/test_skill_resolution.py` — NEW — isolated config logic (S01–S04, S12)
- `tests/unit/test_skills.py` — NEW — generator output (S07–S09)
- `tests/unit/test_defaults.py` — EXTEND — template/workflow integration (S05, S06, S10, S11)

**Runner**: `pytest tests/unit/test_skill_resolution.py tests/unit/test_skills.py tests/unit/test_defaults.py -v`
**Total tests**: 144 (42 resolution + 32 generator + 70 defaults integration)
**Existing skill tests in test_defaults.py**: 278 (pre-existing, now part of 348 total in that file)
**Combined skill-related tests**: 422

## Bug Found — FIXED

`_phase_is_active()` in `cc_rig/config/defaults.py` (line 376-390): docstring claims `"included"` returns True but code only checks `value is True`. **Fixed**: added `if value == "included": return True`. Tested by `TestPhaseFiltering::test_included_string_is_active`.

## Identified Gaps — ALL CLOSED

| # | Gap | Severity | Resolution |
|---|-----|----------|------------|
| 1 | `_phase_is_active()` "included" bug | Bug | **Fixed** in defaults.py + `TestPhaseFiltering::test_included_string_is_active` |
| 2 | `_resolve_skill_packs()` not unit-tested | High | **Closed** by `TestPackExpansion` (14 tests) |
| 3 | `_normalize_skills()` not unit-tested | Medium | **Closed** by `TestNormalization` (5 tests) |
| 4 | Dedup mechanics untested | High | **Closed** by `TestDeduplication` (7 tests) |
| 5 | Tier 1 content not verified | High | **Closed** by `TestTier1TddContent` + `TestTier1DebugContent` (16 tests) |
| 6 | Tier 3 stub content not verified | Medium | **Closed** by `TestTier3Stubs` (6 tests) |
| 7 | recommended-skills.md content untested | High | **Closed** by `TestRecommendedSkillsGuide` (10 tests) |
| 8 | if_applicable only tested for 2 templates | Medium | **Closed** by `TestDatabaseConditional` (7 tests, all 7 templates) |
| 9 | No skill count expectations | Medium | **Closed** by `TestSkillCountScaling` (10 tests + 35 parametrized combos) |
| 10 | GTD-lite skill coverage missing | Medium | **Closed** by `TestGtdLiteSkills` (5 tests) |
| 11 | Template-specific skill identity untested | High | **Closed** by `TestTemplateSkillIdentity` (14 tests) |
| 12 | Pack "reference" string never tested | Medium | **Closed** by `TestPackExpansion::test_trailofbits_reference_skipped` + `TestGtdLiteSkills::test_trailofbits_reference_excluded` |
| 13 | OWASP injection conditional never isolated | Low | **Closed** by `TestPackExpansion::test_owasp_injected_when_security_active` + `test_owasp_excluded_when_security_inactive` |
| 14 | Empty skills → no guide file never tested | Low | **Closed** by `TestRecommendedSkillsGuide::test_guide_not_generated_when_no_skills` |

## Source Files Under Test

| File | Functions/Classes |
|------|-------------------|
| `cc_rig/config/defaults.py` | `_phase_is_active`, `_resolve_skill_packs`, `_normalize_skills`, `_merge_skills`, `compute_defaults` |
| `cc_rig/generators/skills.py` | `generate_skills`, `_write_tdd_skill`, `_write_debug_skill`, `_write_project_patterns_stub`, `_write_deployment_checklist_stub`, `_write_recommended_skills_guide` |

## Scenario Matrix

### S01: Phase Filtering (`_phase_is_active`) — 8 tests

File: `test_skill_resolution.py` | Class: `TestPhaseFiltering`

| Test | Input | Expected |
|------|-------|----------|
| `test_true_is_active` | `True` | `True` |
| `test_included_string_is_active` | `"included"` | `True` (requires bug fix) |
| `test_false_is_inactive` | `False` | `False` |
| `test_reference_is_inactive` | `"reference"` | `False` |
| `test_bundled_only_is_inactive` | `"bundled_only"` | `False` |
| `test_if_applicable_is_inactive` | `"if_applicable"` | `False` |
| `test_absent_key_is_inactive` | missing key | `False` |
| `test_empty_phase_name_is_inactive` | phase=`""` | `False` |

### S02: Pack Expansion (`_resolve_skill_packs`) — 14 tests

File: `test_skill_resolution.py` | Class: `TestPackExpansion`

| Test | Pack | Value | Expected |
|------|------|-------|----------|
| `test_superpowers_full_expands_all_active` | superpowers | `"full"` | all phase-matching skills |
| `test_superpowers_list_expands_named` | superpowers | `["brainstorming"]` | only brainstorming |
| `test_superpowers_empty_expands_none` | superpowers | `[]` | no superpowers skills |
| `test_superpowers_full_respects_phases` | superpowers | `"full"` + planning=False | planning skills excluded |
| `test_trailofbits_list_expands_named` | trailofbits_core | `["static-analysis"]` | only static-analysis |
| `test_trailofbits_reference_skipped` | trailofbits_core | `"reference"` | no skills (silent skip) |
| `test_trailofbits_empty_expands_none` | trailofbits_core | `[]` | no ToB skills |
| `test_anthropic_full_expands_all_active` | anthropic_official | `"full"` | all phase-matching |
| `test_anthropic_list_expands_named` | anthropic_official | `["mcp-builder"]` | only mcp-builder |
| `test_anthropic_empty_expands_none` | anthropic_official | `[]` | no anthropic skills |
| `test_anthropic_full_respects_phases` | anthropic_official | `"full"` + devops=False | mcp-builder excluded |
| `test_owasp_injected_when_security_active` | N/A | security=True | OWASP in result |
| `test_owasp_excluded_when_security_inactive` | N/A | security=False | no OWASP |
| `test_unknown_skill_name_silently_skipped` | superpowers | `["nonexistent"]` | empty list |

### S03: Normalization (`_normalize_skills`) — 5 tests

File: `test_skill_resolution.py` | Class: `TestNormalization`

| Test | Input | Expected |
|------|-------|----------|
| `test_dict_converts_to_recommendation` | `[{"name": "x", ...}]` | SkillRecommendation |
| `test_bare_string_converts` | `["my-skill"]` | SkillRecommendation(name="my-skill") |
| `test_recommendation_passthrough` | `[SkillRecommendation(...)]` | unchanged |
| `test_mixed_formats` | dict + string + object | all converted |
| `test_empty_list` | `[]` | `[]` |

### S04: Deduplication and Merge — 7 tests

File: `test_skill_resolution.py` | Class: `TestDeduplication`

| Test | Scenario | Expected |
|------|----------|----------|
| `test_template_skill_survives_when_no_overlap` | template has "modern-python", packs don't | modern-python in result |
| `test_pack_skill_overrides_template_same_name` | template + pack both have same name | pack version wins (last entry) |
| `test_dedup_preserves_last_source` | two sources, same name | source from pack |
| `test_merge_no_duplicates` | full merge scenario | no duplicate names |
| `test_merge_with_empty_template_skills` | template has no skills | only pack skills |
| `test_merge_with_empty_packs` | packs all empty | only template skills |
| `test_phase_filter_removes_before_dedup` | template skill in inactive phase | filtered out |

### S05: Template-Specific Skill Identity — 14 tests

File: `test_defaults.py` | Class: `TestTemplateSkillIdentity`

| Test | Template | Expected Skills |
|------|----------|-----------------|
| `test_fastapi_has_modern_python` | fastapi | modern-python |
| `test_fastapi_has_property_testing` | fastapi | property-based-testing |
| `test_fastapi_has_webapp_testing` | fastapi | webapp-testing |
| `test_fastapi_has_db_skills` | fastapi+standard | supabase + planetscale |
| `test_django_matches_fastapi_skills` | django | same skill set as fastapi |
| `test_flask_matches_fastapi_skills` | flask | same skill set as fastapi |
| `test_nextjs_has_vercel_skills` | nextjs | vercel-react-best-practices |
| `test_nextjs_has_frontend_skills` | nextjs | frontend-design, tailwind-design-system |
| `test_nextjs_has_webapp_testing` | nextjs | webapp-testing |
| `test_nextjs_no_modern_python` | nextjs | modern-python NOT present |
| `test_gin_has_static_analysis` | gin | static-analysis |
| `test_gin_no_modern_python` | gin | modern-python NOT present |
| `test_rust_cli_minimal_skills` | rust-cli | fewest template skills |
| `test_rust_cli_no_db_skills` | rust-cli+standard | no database phase skills |

### S06: Database `if_applicable` Conditional — 7 tests

File: `test_defaults.py` | Class: `TestDatabaseConditional`

| Test | Template | Has DB MCP? | Expected |
|------|----------|-------------|----------|
| `test_fastapi_has_db` | fastapi | yes (postgres) | database skills present |
| `test_django_has_db` | django | yes (postgres) | database skills present |
| `test_flask_has_db` | flask | yes (postgres) | database skills present |
| `test_nextjs_db_conditional` | nextjs | check MCPs | database if DB MCP present |
| `test_gin_has_db` | gin | yes (postgres) | database skills present |
| `test_echo_has_db` | echo | yes (postgres) | database skills present |
| `test_rust_cli_no_db` | rust-cli | no | no database skills |

### S07: Tier 1 Content Generation — 16 tests

File: `test_skills.py` | Class: `TestTier1TddContent` + `TestTier1DebugContent`

| Test | Framework | Skill | Content Markers |
|------|-----------|-------|-----------------|
| `test_tdd_fastapi` | fastapi | tdd | "TestClient", "starlette" |
| `test_tdd_django` | django | tdd | "django.test.TestCase" |
| `test_tdd_nextjs` | nextjs | tdd | "Jest or Vitest", "React Testing Library" |
| `test_tdd_gin` | gin | tdd | "httptest.NewRecorder", "t.Run()" |
| `test_tdd_echo` | echo | tdd | "echo.New()" |
| `test_tdd_clap` | rust-cli | tdd | "assert_cmd", "#[test]" |
| `test_tdd_flask` | flask | tdd | "test_client()", "FlaskClient" |
| `test_tdd_unknown_generic` | unknown | tdd | "established test patterns" |
| `test_debug_fastapi` | fastapi | debug | "dependency injection", "uvicorn" |
| `test_debug_django` | django | debug | "django-debug-toolbar" |
| `test_debug_nextjs` | nextjs | debug | "React DevTools", "Hydration" |
| `test_debug_gin` | gin | debug | "gin.DebugMode", "pprof" |
| `test_debug_echo` | echo | debug | "echo.Debug" |
| `test_debug_clap` | rust-cli | debug | "RUST_BACKTRACE", "dbg!()" |
| `test_debug_flask` | flask | debug | "debug=True", "flask shell" |
| `test_debug_unknown_generic` | unknown | debug | "standard debugging tools" |

### S08: Tier 3 Stub Content — 6 tests

File: `test_skills.py` | Class: `TestTier3Stubs`

| Test | Stub | Verifies |
|------|------|----------|
| `test_project_patterns_has_sections` | project-patterns | "Naming Conventions", "Architecture Patterns", "Code Organization" |
| `test_project_patterns_has_skill_creator_tip` | project-patterns | "skill-creator" in Tip |
| `test_project_patterns_is_stub` | project-patterns | "(Add your" placeholder text |
| `test_deployment_checklist_has_sections` | deployment-checklist | "Pre-Deploy", "Deploy Steps", "Post-Deploy" |
| `test_deployment_checklist_has_skill_creator_tip` | deployment-checklist | "skill-creator" in Tip |
| `test_deployment_checklist_is_stub` | deployment-checklist | "(Add your" placeholder text |

### S09: Recommended Skills Guide — 10 tests

File: `test_skills.py` | Class: `TestRecommendedSkillsGuide`

| Test | Verifies |
|------|----------|
| `test_guide_header_mentions_framework` | "fastapi" in header |
| `test_guide_header_mentions_workflow` | "standard" in header |
| `test_guide_groups_by_phase` | `## Coding`, `## Testing`, etc. |
| `test_guide_phase_ordering` | coding before testing before review before security |
| `test_guide_has_install_commands` | "```bash" + "npx skills add" |
| `test_guide_has_discovery_links` | skills.sh, awesome-claude-code, awesome-claude-skills |
| `test_guide_no_empty_phases` | no `## Phase` without skills |
| `test_guide_not_generated_when_no_skills` | empty recommended_skills → no file |
| `test_guide_skill_count_matches_config` | ### count matches config count |
| `test_guide_all_skills_have_descriptions` | every ### has description |

### S10: Skill Count Scaling — 10 tests

File: `test_defaults.py` | Class: `TestSkillCountScaling`

| Test | Verifies |
|------|----------|
| `test_speedrun_fewest_skills` | speedrun < standard |
| `test_verify_heavy_most_skills` | verify-heavy >= all others |
| `test_standard_more_than_speedrun` | standard > speedrun |
| `test_spec_driven_more_than_standard` | spec-driven >= standard |
| `test_gtd_lite_similar_to_spec_driven` | gtd-lite count ≈ spec-driven |
| `test_fastapi_more_skills_than_rust_cli` | DB templates have more |
| `test_nextjs_has_frontend_bonus` | nextjs has more coding skills |
| `test_skill_counts_per_workflow` | exact count ranges per workflow |
| `test_all_combos_have_at_least_one_skill` | min 1 for all 35 combos |
| `test_no_combo_exceeds_reasonable_max` | no combo > 40 skills |

### S11: GTD-Lite Full Coverage — 5 tests

File: `test_defaults.py` | Class: `TestGtdLiteSkills`

| Test | Verifies |
|------|----------|
| `test_has_all_standard_phases` | coding, testing, review, security, devops |
| `test_has_planning_phase` | planning active |
| `test_superpowers_list` | 7 specific superpowers |
| `test_trailofbits_reference_excluded` | "reference" → no ToB skills |
| `test_similar_skills_to_spec_driven` | same skill set as spec-driven |

### S12: Edge Cases — 8 tests

File: `test_skill_resolution.py` | Class: `TestEdgeCases`

| Test | Scenario | Expected |
|------|----------|----------|
| `test_included_string_is_active` | phase="included" | True (after bug fix) |
| `test_none_phase_value` | phase=None | False |
| `test_integer_phase_value` | phase=1 | False |
| `test_empty_skill_packs_dict` | `{}` | no pack skills |
| `test_missing_skill_phases_key` | no skill_phases | all inactive |
| `test_all_phases_false` | every phase=False | empty result |
| `test_skill_with_empty_name` | name="" | doesn't crash |
| `test_skill_with_missing_sdlc_phase` | sdlc_phase="" | excluded by filter |

## Implementation Order

```
Bug fix: _phase_is_active "included" ──→ first (S01 depends on it)

S01 (Phase) ──┐
S02 (Packs) ──┤
S03 (Normalize)┼──→ test_skill_resolution.py (34 tests)
S04 (Dedup) ──┤
S12 (Edge)  ──┘

S05 (Template)─┐
S06 (DB cond) ─┼──→ test_defaults.py extensions (36 tests)
S10 (Counts) ──┤
S11 (GTD-lite)─┘

S07 (Tier 1) ──┐
S08 (Tier 3) ──┼──→ test_skills.py (32 tests)
S09 (Guide)  ──┘
```

All three test files are independent — can implement in parallel.

## Coverage Matrix

| Dimension | Scenarios |
|-----------|-----------|
| **_phase_is_active** | S01, S12 |
| **_resolve_skill_packs** | S02 |
| **_normalize_skills** | S03 |
| **_merge_skills** | S04 |
| **compute_defaults** | S05, S06, S10, S11 |
| **generate_skills** | S07, S08 |
| **_write_recommended_skills_guide** | S09 |
| **fastapi template** | S05, S06, S07, S09 |
| **django template** | S05, S06 |
| **flask template** | S05, S06 |
| **nextjs template** | S05, S06, S07 |
| **gin template** | S05, S06, S07 |
| **echo template** | S06, S07 |
| **rust-cli template** | S05, S06, S07 |
| **speedrun workflow** | S10 |
| **standard workflow** | S05, S09, S10 |
| **spec-driven workflow** | S10 |
| **gtd-lite workflow** | S10, S11 |
| **verify-heavy workflow** | S10 |
| **superpowers pack** | S02 |
| **trailofbits_core pack** | S02, S11 |
| **anthropic_official pack** | S02 |
| **OWASP injection** | S02 |
| **deduplication** | S04 |
| **if_applicable** | S06 |
| **edge cases** | S12 |
