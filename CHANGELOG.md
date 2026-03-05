# Changelog

All notable changes to cc-rig will be documented in this file.

## [1.4.1] - 2026-03-06

### Added
- **Multi-worktree orchestration** — `cc-rig worktree spawn/list/status/pr/cleanup`. Launch multiple Claude sessions in parallel worktrees from the terminal. Each task gets an isolated git worktree and branch (`wt/<slug>`). State tracked in `.claude/worktrees.json`. PID-based status monitoring, PR creation via `gh`, batch cleanup. New `cc_rig/worktree/` package (state, manager, orchestrator). 92 new tests across 4 test files.
- **`cc-rig config update`** — Re-run wizard with existing config values pre-filled, show diff, regenerate on confirmation. Supports `--quick` and `--expert` modes.
- **`cc-rig doctor --check-compat`** — Check generated config features against installed Claude Code version. Warns about plugins, background agents, worktree isolation, and settings.local.json on older CC versions.
- **Community preset validation** — `validate_preset()` validates schema before installation. Template presets require `project_type`; workflow presets require `agents` and `commands` as lists.

### Changed
- **Data extraction (M6)** — Moved `_COMMAND_DEFS` (19 commands) and `_AGENT_DEFS` (13 agents) from inline Python to `cc_rig/data/commands.json` and `cc_rig/data/agents.json`. Pure refactor, zero behavior change.
- Added `package-data` to `pyproject.toml` to ensure JSON data files are included in wheels.
- TUI worktree feature description expanded with usage examples and workflow context.
- Workflow detail panels now show `parallel-worker` agent and `worktree` command for spec-driven, gtd-lite, verify-heavy.
- Generated CLAUDE.md worktree section includes `cc-rig worktree` CLI examples.
- `#feature-details` panel max-height bumped from 10 to 16 for longer descriptions.

---

## [1.4.0] - 2026-03-05

### Added
- **Official Claude Code Plugin Integration** — cc-rig now curates official Anthropic marketplace plugins alongside skills, hooks, agents, commands, and MCPs.
  - New `cc_rig/plugins/` module with 24-plugin catalog across 5 categories: LSP (7), integration (10), workflow (5), autonomy (1), utility (1).
  - `PluginRecommendation` dataclass on `ProjectConfig` with full serialization support.
  - Smart defaults: `compute_defaults()` resolves plugins by language (LSP), template (integrations), and workflow (workflow plugins). GitHub MCP replaced by github plugin (self-contained, auto-start).
  - `enabledPlugins` section in generated `settings.json` — format: `"name@marketplace": true`.
  - **Ralph-loop plugin** — official Anthropic autonomous loop as alternative to cc-rig's loop.sh. Harness picker shows 6th option. Custom-style B1/B2 feature confirms (task_tracking, budget_awareness, verification_gates). Mutual exclusion with `autonomy_loop`.
  - Expert mode plugins category — multi-select from full catalog (TUI tab + CLI).
  - TUI: Plugins tab in ExpertScreen, ralph-loop RadioButton in HarnessScreen with detail panel.
  - Doctor check: LSP binary PATH detection (warning if binary not found).
  - Schema validation: plugin category values, ralph-loop + autonomy_loop mutual exclusion.
  - 184 new tests across 10 test files: plugin registry (33), config (16), defaults (15), settings (8), schema (5), harness (8), E2E (26), TUI wizard (9), wizard flow (1).
  - Workflow detail panel: each workflow shows its plugin set (LSP + workflow plugins).
  - Configuration preview and "Ready to generate" screens show plugin count.
  - Templates grouped by language in picker (Python, TypeScript, Go, Rust, Ruby, Java, C#, PHP, Elixir).
  - Ralph-loop TUI: B1/B2 feature checkboxes (task tracking, budget, gates) shown when selected.
  - Generated CLAUDE.md: 6 new workflow principles (plan first, clarify ambiguity, suggest tests, break up large changes, test-first debugging, learn from corrections).

---

## [1.3.2] - 2026-03-04

### Added
- **Generation log**: `cc-rig init` now saves output to `.claude/cc-rig-init.log` — file list, validation results, next steps. Symlink at project root for discoverability. ANSI codes stripped. Log saved on both success and validation failure. Not tracked in manifest (preserved by `cc-rig clean`).

---

## [1.3.1] - 2026-03-03

### Added
- **V2 Runtime: Budget Enforcement + Cost Tracking** (Path A + Path B)
  - `budget-reminder.sh` (Stop hook) now parses JSONL session logs via inline Python heredoc — shows actual session tokens + estimated cost with model-aware pricing (Opus/Sonnet/Haiku auto-detected from session log). Project-scoped JSONL lookup (not global). Graceful degradation: no python3 or no JSONL → shows "unavailable", never blocks.
  - `loop.sh` (B3 autonomy) enhanced with: `--output-format json` for cost capture, model-aware pricing, budget tracking accumulators including cache tokens, budget enforcement (breaks loop on exceed, warns at threshold), checkpoint auto-commit (when Claude doesn't commit), progress ledger with cost per iteration, `cleanup()` trap with cost summary on exit.
  - loop.sh refactored from single string into 12 named parts for maintainability.
  - 14 new tests: 4 for budget-reminder (session cost parsing, graceful degradation, estimated cost display, session tokens display), 8 for loop.sh (output-format json, budget enforcement, budget tracking, auto-checkpoint, cost summary, progress logging, cleanup trap, bash syntax), 2 E2E (S02/S07 `--output-format json` assertions).

### Fixed
- Validator V14 placeholder check no longer false-positives on community skill files (webapp-testing, requesting-code-review). Only project-patterns stub is checked.
- Budget-reminder JSONL parsing: fixed field paths (`msg.type` not `msg.role`, usage nested under `msg.message`).
- Budget-reminder JSONL scoping: now searches current project's directory only, not all projects globally.
- loop.sh budget enforcement: cache tokens now included in total (were 80%+ of usage but ignored).
- loop.sh cost accumulation: replaced fragile triple-escaped bash interpolation with `sys.argv` passing.
- loop.sh cost summary: shows "unavailable" instead of misleading "$0" when python3 absent.
- `.claude/settings.local.json` generation — personal permission overrides file (`preserve_on_clean=True`)
- 66 new tests across 4 test files:
  - `test_memory_content.py` (18 tests) — memory file content, anti-ballooning rules, MEMORY-README
  - `test_workflow_diff.py` (17 tests) — cross-workflow comparison (speedrun vs standard vs verify-heavy vs spec-driven vs gtd-lite)
  - `test_command_frontmatter.py` (18 tests) — YAML frontmatter parsing, `$ARGUMENTS` validation, `_COMMAND_DEFS` consistency
  - `test_permission_modes.py` (13 tests) — default vs permissive mode comparison, allow/deny lists
- 12 tests (10 unit + 1 integration + 1 E2E) for settings.local.json

### Changed
- Refactored `_script_lint`/`_script_typecheck` into shared `_script_check_on_commit` helper (settings.py)
- Refactored `load_template`/`load_workflow` into shared `_load_preset` helper (manager.py)
- Polished TUI wizard screen descriptions (TemplateScreen, WorkflowScreen, FeaturesScreen)

### Fixed
- Version bump: `pyproject.toml` and `__init__.py` synced from 1.0.0 to 1.3.0
- Removed `memory-stop` prompt hook — Claude wraps JSON in markdown, causing validation failure every session exit. Auto-memory already handles learning persistence.
- Fixed `ruff format` issues in `textual_wizard.py` and `generate.py` (CI was failing)
- CI verified green on Python 3.9, 3.10, 3.11, 3.12

---

## [1.3.0] - 2026-03-02

### Added

**Generic Template**
- `generic` — Language-agnostic template for DevOps, monorepos, docs, infra projects
- First-class option on template picker (first in list), no framework or tool commands
- Uses excellent language-agnostic content from existing `generic.py` template module
- Default MCPs: GitHub only (no database assumption)
- Never auto-detected — user-selected only

**À La Carte Harness**
- Custom harness level: pick individual features without B0→B1→B2→B3 tier progression
- 4 boolean feature flags: `task_tracking`, `budget_awareness`, `verification_gates`, `autonomy_loop`
- Auto-dependency: `autonomy_loop=True` auto-enables `task_tracking` (PROMPT.md references todo.md)
- Backward compatible: old configs without flags derive them from level via `__post_init__`
- Wizard "Custom" option with individual confirm prompts for each feature
- Generator/hook/guardrail logic refactored from level-based to flag-based

**Total**: 16 templates × 5 workflows = 80 valid combinations.

**Tests**
- `TestHarnessConfigFlags`: level→flags derivation, round-trip, old-config backward compat
- `TestCustomHarness`: autonomy-only, task-only, gates-only, budget-only, combined flags
- `TestCustomHarnessHooks`: hook generation per individual flag
- `TestGenericTemplateHooks`: no format/lint/typecheck hooks for generic
- `TestS22GenericStandardB0`: full E2E scenario for generic template
- Generic added to cross-product (16×5), skill registry, MCP, detection tests
- All guard counts updated (16 templates)

---

## [1.2.0] - 2026-03-02

### Added

**4 New Framework Templates**
- `laravel` — PHP + Laravel: MVC, Eloquent ORM, Artisan, PHPUnit, PHP-CS-Fixer
- `express` — Node.js + Express: middleware patterns, Router, Jest, ESLint, PM2 deployment
- `phoenix` — Elixir + Phoenix: LiveView, Ecto, ExUnit, Credo, mix release
- `go-std` — Go standard library: idiomatic Go patterns, go test, golangci-lint, no framework coupling

**Total**: 15 templates × 5 workflows = 75 valid combinations.

**Tests**
- Unit detection/hooks/markers tests for each new template
- Generator parametrization auto-covers all 15 templates
- E2E scenarios S18 (Laravel+Standard), S19 (Express+Standard), S20 (Phoenix+Standard), S21 (Go-Std+Standard)
- Full 15×5 cross-product verified
- Test count updated accordingly

---

## [1.1.0] - 2026-02-25

### Added

**Textual Full-Screen TUI Wizard**
- Full-screen interactive wizard using Textual when installed + TTY detected
- 9 screens: Welcome, Basics, Template, Workflow, Review, Expert, Features, Harness, Confirm
- Arrow-key navigation with RadioSet, SelectionList, and Checkbox widgets
- Back-navigation across all screens, Cancel/Escape to exit
- Branding header (cc-rig + step label) on every screen
- Save Config button on ConfirmScreen (saves to `~/.cc-rig/configs/`)
- QuickWizardApp for `--quick` flow (4 screens: Template, Workflow, Basics, Confirm)
- In-wizard migrate mode: detection runs inline, falls back to template picker on failure
- In-wizard quick mode: switches screen sequence without exiting TUI
- Focus management: primary widget auto-focused on every screen for immediate keyboard use
- Falls back to existing CLI stepper when Textual not installed or no TTY
- `should_use_textual(io)` detection helper (skips TUI for test-injected IO)
- `HAS_TEXTUAL` flag in `cc_rig/ui/tui.py`

**Migrate Flow Improvements**
- `--migrate` now falls back to template/workflow picker when framework detection fails (was hard error)
- Workflow selection added to all migrate paths (was hardcoded to "standard")

**TUI Wizard UX Improvements**
- Harness descriptions (B0-B3) rewritten to match actual generated files and behavior
- Features screen: rich user-benefit descriptions with workflow recommendation indicators (★)
- Review screen: explains what agents, commands, hooks are and what customize gives you
- Centralized descriptions in `cc_rig/ui/descriptions.py` (single source of truth)
- Renamed "Feature flags" step label to "Features"
- Space key now activates focused buttons (standard UI convention, was Enter-only)

**Testing**
- 21 async Textual pilot-based tests in `tests/unit/test_textual_wizard.py`
- `pytest-asyncio` added to dev dependencies
- Test count: 1288 → 1343

## [1.0.0] - 2026-02-22

### Added

**Core**
- Two-axis architecture: Config Experience (A0-A3) x Runtime Discipline (B0-B3)
- 11 framework templates: FastAPI, Django, Flask, Next.js, Gin, Echo, Rust CLI, Rust/Axum, Ruby/Rails, Spring Boot, ASP.NET Core (16 as of v1.3.0)
- 5 workflow presets: speedrun, standard, spec-driven, gtd-lite, verify-heavy
- Smart defaults engine: template + workflow compose independently (55 valid combos, 80 as of v1.3.0)
- ProjectConfig dataclass with full serialization round-trip

**Generators**
- CLAUDE.md generator with cache-aware static-first ordering (~55 lines)
- settings.json with hook schema (command + prompt types)
- Up to 12 agent definitions with role-specific prompts and tool restrictions
- Up to 16 slash commands with YAML frontmatter
- 4 bundled skills (TDD, systematic-debug, project-patterns, deployment-checklist)
- 4 agent docs (architecture, conventions, testing, deployment) — framework-specific
- 5-file memory system with anti-ballooning rules
- MCP server configuration
- Hook shell scripts (format, lint, typecheck, safety guards)
- Post-generation validator with 19 checks

**CLI & Wizard**
- `cc-rig init` with 6 flow paths: zero-config, guided, quick, expert, config-load, migrate
- `cc-rig preset list` to browse templates and workflows
- Interactive wizard with testable IO (injectable input/output)
- Project detection for `--migrate` (pyproject.toml, package.json, go.mod, Cargo.toml, etc.)

**Config Management**
- `cc-rig config save/load/list/inspect/diff/lock/unlock`
- Personal configs in `~/.cc-rig/configs/`
- Team configs in `.cc-rig.json` (committable)
- Portable export strips machine-specific paths
- Locked configs prevent modification via wizard

**Doctor & Clean**
- `cc-rig doctor` with 10+ health checks (files, hooks, memory, manifest, staleness)
- `cc-rig doctor --fix` for safe auto-remediation (permissions, missing memory files)
- `cc-rig clean` manifest-based removal (only deletes generated files)
- Empty directory cleanup after clean

**Runtime Harness**
- `cc-rig harness init --lite` (B1): task tracking + budget awareness
- `cc-rig harness init` (B2): + verification gates + review notes
- `cc-rig harness init --autonomy` (B3): autonomous loop with safety rails
- Safety config: max iterations, checkpoint commits, blocked-state handling
- `--ralph` hidden alias preserved

**Infrastructure**
- Zero runtime dependencies (Python stdlib only)
- pytest test suite (685 tests)
- ruff linting and formatting
- GitHub Actions CI (Python 3.9-3.12)
- MIT license
