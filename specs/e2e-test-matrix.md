# Spec: E2E Test Matrix for cc-rig TUI Wizard

**Author**: cc-rig
**Date**: 2026-02-27
**Status**: Implemented

## Summary

Systematic end-to-end verification that `cc-rig init` produces correct output across all configuration dimensions. 12 representative scenarios cover every template, workflow, harness level, feature flag, and flow type at least once. A full 7×5 cross-product test ensures every template×workflow combination generates without error.

## Implementation

**Test file**: `tests/integration/test_e2e_matrix.py`
**Runner**: `pytest tests/integration/test_e2e_matrix.py`
**Total tests**: 188 (all passing)
**Runtime**: ~1.2 seconds

## Test Dimensions

| Dimension | Options |
|-----------|---------|
| **Template** | fastapi, django, flask, gin, echo, nextjs, rust-cli |
| **Workflow** | speedrun, standard, spec-driven, gtd-lite, verify-heavy |
| **Harness** | none (B0), lite (B1), standard (B2), autonomy (B3) |
| **Features** | memory, spec_workflow, gtd, worktrees |
| **Expert** | agent removal + feature toggle |
| **Rerun** | workflow switch with orphan cleanup |
| **Clean** | full cleanup verification |

## Scenario Matrix

### S01: FastAPI + Standard + B0
- **Purpose**: Baseline — most common path, default everything
- **Tests**: 21
- **Verifies**: 43 files, 5 agents, 8 commands, 9 hook scripts, memory/, no specs/, no tasks/, permissive permissions, manifest consistency, no duplicates, hooks executable, CLAUDE.md content

### S02: FastAPI + Verify-Heavy + B3 Autonomy
- **Purpose**: Maximum rigor — all agents, all commands, autonomy harness
- **Tests**: 18
- **Verifies**: 13 agents (12 from workflow + parallel-worker), 15 commands (GTD stripped), spec files, harness B1/B2/B3 files, loop.sh executable, harness-config.json, budget-reminder hook

### S03: FastAPI + GTD-Lite + B0
- **Purpose**: GTD feature path
- **Tests**: 11
- **Verifies**: 8 agents, 12 commands (GTD present, spec absent), tasks/inbox.md + todo.md + someday.md, worktree command, no specs/

### S04: FastAPI + Speedrun + B0
- **Purpose**: Minimal config — fewest files
- **Tests**: 13
- **Verifies**: 30 files, 3 agents, 6 commands, 6 hooks (no typecheck, no stop-validator, no memory), no memory/, no remember/refactor commands, default permissions

### S05: NextJS + Standard + B2
- **Purpose**: Non-Python template — template-specific hooks
- **Tests**: 13
- **Verifies**: prettier/npm/tsc in hook scripts, typescript/nextjs in CLAUDE.md, B2 harness files (verification-gates, review-notes), budget-reminder hook

### S06: Gin + Spec-Driven + B0
- **Purpose**: Go template + spec workflow
- **Tests**: 12
- **Verifies**: goimports/golangci-lint/go-vet in hooks, specs/TEMPLATE.md, spec-create/spec-execute commands, pm-spec/implementer/parallel-worker agents, go/gin in CLAUDE.md

### S07: Rust-CLI + Standard + B3 Autonomy
- **Purpose**: Rust template + autonomy loop
- **Tests**: 12
- **Verifies**: cargo fmt/clippy/check in hooks, loop.sh executable, PROMPT.md, autonomy-loop doc, harness-config.json, cargo test in stop-validator, rust in CLAUDE.md

### S08: Expert Customization
- **Purpose**: Simulated expert mode — remove agents, add features
- **Tests**: 7
- **Verifies**: architect/refactorer removed, pm-spec/implementer added (spec_workflow=true), spec commands present, specs/TEMPLATE.md generated

### S09: Feature Mutual Exclusion
- **Purpose**: spec_workflow and gtd radio behavior
- **Tests**: 3
- **Verifies**: verify-heavy defaults (spec=on, gtd=off), toggling GTD on produces correct commands/files, spec commands absent when spec_workflow=false

### S10: Django + Speedrun + B0
- **Purpose**: Different Python template + minimal
- **Tests**: 12
- **Verifies**: django/python in CLAUDE.md, manage.py test in config, 30 files, 3 agents, 6 commands, no memory/specs/tasks, default permissions

### S11: Rerun — Standard → Verify-Heavy
- **Purpose**: Re-init with workflow change, orphan cleanup
- **Tests**: 4
- **Verifies**: new agents/commands present, orphan files removed, no duplicates, manifest updated to verify-heavy

### S12: Clean After Init
- **Purpose**: Full cleanup verification
- **Tests**: 6
- **Verifies**: generated files removed, empty dirs cleaned, pre-existing README preserved, backup dir removed, .cc-rig.json removed, manifest gone

## Cross-Cutting Tests

| Test | Count | Coverage |
|------|-------|----------|
| Every template with standard | 7 | All 7 templates generate successfully |
| Every workflow with fastapi | 5 | All 5 workflows generate successfully |
| Full cross-product (7×5) | 35 | All 35 combinations produce consistent manifests |
| Every harness level | 4 | none/lite/standard/autonomy produce correct files |
| Feature isolation | 5 | memory, spec_workflow, gtd, worktrees toggle correctly |

## Coverage Matrix

| Dimension | Scenarios |
|-----------|-----------|
| **fastapi** | S01, S02, S03, S04, S08, S09, S11, S12 |
| **nextjs** | S05 |
| **gin** | S06 |
| **rust-cli** | S07 |
| **django** | S10 |
| **flask** | cross-product |
| **echo** | cross-product |
| **speedrun** | S04, S10 |
| **standard** | S01, S05, S07, S08, S11 |
| **spec-driven** | S06 |
| **gtd-lite** | S03 |
| **verify-heavy** | S02, S09, S11, S12 |
| **B0 none** | S01, S03, S04, S06, S08, S09, S10 |
| **B1 lite** | harness level test |
| **B2 standard** | S05 |
| **B3 autonomy** | S02, S07 |
| **expert mode** | S08, S09 |
| **rerun** | S11 |
| **clean** | S12 |
| **memory=true** | S01, S02, S03, S05, S06, S07, S08 |
| **memory=false** | S04, S10 |
| **spec_workflow=true** | S02, S06, S08, S09 |
| **gtd=true** | S03, S09 |
| **worktrees=true** | S02, S03, S06 |

## Verification Checks (Per Scenario)

Each scenario verifies a subset of:

1. **V1**: File count matches expected
2. **V2**: No duplicate commands in `.claude/commands/`
3. **V3**: No duplicate skills in `.claude/skills/`
4. **V4**: No .bak files outside backup directory
5. **V5**: Feature-gated commands present/absent correctly
6. **V6**: Feature-gated files present/absent correctly
7. **V7**: All hook scripts executable (chmod 755)
8. **V8**: Harness files present/absent per level
9. **V9**: CLAUDE.md content matches template/features
10. **V10**: Settings permissions match workflow mode
11. **V11**: Manifest lists only files that exist on disk
12. **V12**: Template-specific hook content (language-correct commands)

## Technical Notes

- Tests use the Python API directly (`compute_defaults` + `generate_all`) for reliable non-interactive execution
- Expert mode (S08, S09) is simulated by modifying the config object after `compute_defaults`
- Harness levels are set via `config.harness = HarnessConfig(level=...)` before `generate_all`
- Rerun (S11) calls `generate_all` twice and verifies orphan cleanup via `cleanup_files`
- Clean (S12) uses `run_clean(force=True)` to skip confirmation
- All tests use pytest's `tmp_path` fixture for isolation
