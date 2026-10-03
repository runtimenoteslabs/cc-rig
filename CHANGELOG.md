# Changelog

All notable changes to cc-rig will be documented in this file.

## [4.0.0] - 2026-10-02 Config Tuner

cc-rig gains a second pillar. Alongside generating a config, it now scores your
Claude Code setup, ranks what to fix, and applies the safe fixes in one
command. Generate it right with `cc-rig init`, keep it right with
`cc-rig tune`. Both run on one engine: the generator is also the tuner's apply
layer.

### Added: `cc-rig tune`

The headline of v4.0. A scored report on your config, with fixes.

- **Score**: a composite 0-100 grade across six published, impact-weighted
  dimensions: cache hygiene (30%), safety guards (20%), context discipline
  (15%), workflow fit (15%), verification (10%), currency (10%). The weights
  are public, so the number is auditable.
- **Dollars, where measurable**: cache findings carry an estimated monthly
  cost derived from your real session logs (the same engine behind
  `cc-rig savings`), with zero extra LLM calls. Findings worth $1 a month or
  more rank first, then the rest by severity. Within a severity, a smaller
  measured cost yields to an unpriced finding, so a two-cent saving never
  outranks a missing safety guard. With no session history, dollar figures
  are left out rather than guessed.
- **Fix**: `cc-rig tune --fix` applies safe, additive fixes (version pin,
  guardrail and verification-gate additions), backs up CLAUDE.md via
  FileTracker, shows a unified diff, and re-scores. `--fix-unsafe` also
  relocates content (opt-in). The contract: never apply a fix that introduces
  a worse problem than it removes.
- **Gate and integrate**: `--ci` exits non-zero below `--min-score` (default
  60), `--json` for tooling, `--badge` emits a Shields.io endpoint.
- Detection reads hook script bodies, not just settings commands, so tools
  wired inside `format.sh` and friends are not false-flagged. A freshly
  generated project scores 100/100 on quick and standard for all 16 stacks,
  and on rigorous for 13; rigorous Django, Go stdlib and Spring Boot score 98
  because their CLAUDE.md runs past the size threshold.
- The Commands-section fix is offered only when `.cc-rig.json` exists, since
  that is where the fixer reads the commands from.
- The report closes by pointing to Claude Code's own in-session tools: `/cost`
  names the likely cause of each cache miss, `/doctor` trims CLAUDE.md and
  `/skill-doctor` finds unused skills. `tune` scores the repo before a session
  starts; those cover what happens inside one.
- `/cc-rig tune` joins the generated playbook command, next to `savings` and
  `audit`.

### Changed: aligned to Claude Code 2.1.287

- Version pin bumped from 2.1.126 to 2.1.287 (the generated CLAUDE.md identity
  line and doctor messages follow automatically).
- Doctor settings whitelist rebuilt from the official settings reference plus
  the schemastore schema: 188 top-level keys, up from 94. It is add-only, so a
  key dropped from the docs still validates for users who set it earlier.
  Stops false-positive warnings on valid keys such as `promptCacheTtl`,
  `autoCompactWindow` and `skillOverrides`.
- Generated CLAUDE.md leaned to the evidence (essential tooling and critical
  patterns only): standard drops from 127 to 120 lines, rigorous 157 to 142,
  quick 87 to 82.

### Fixed

- **Every dollar figure was overstated.** On the same 30 days of real session
  logs, 3.2.1 reports $10,521; 4.0.0 reports $1,068, within 1% of an
  independent check. Two causes, both fixed:
  - Claude Code writes one log line per content block, each repeating the
    message's usage, so a message was counted two to three times. Usage is
    now counted once per message id.
  - Prices were retired Claude 3 rates (Opus at $15/$75 per million) with no
    knowledge of Claude 5 models. A new module, `cc_rig/pricing.py`, prices
    by model id across Fable, Opus, Sonnet and Haiku (5.x, 4.x and legacy),
    with 1-hour cache writes at 2x input and 5-minute writes at 1.25x.
- The three generated scripts that print costs (the session-telemetry and
  budget-reminder hooks, and the autonomy loop's `loop.sh`) carried their own
  stale price tables. They now embed a copy generated from
  `cc_rig/pricing.py`, so regenerating a project fixes its numbers. `loop.sh`
  prefers Claude Code's own `total_cost_usd` when present.
- Session telemetry counted turns from `human` log entries, which current
  Claude Code no longer writes. It now counts user prompts and skips tool
  results.
- `tune`'s cache-break estimate uses the model's real cache-read rate and the
  observed 5-minute/1-hour write mix instead of a flat 1.15x of input, and
  model-switch breaks are priced at the session's model instead of Sonnet.
- Cached session summaries are re-parsed when prices change.
- Interrupted sessions read as model switches. Claude Code logs an interrupt
  or an API error as an assistant message with model `<synthetic>`, and the
  parser counted it as a switch to Sonnet. One interrupt was enough to put a
  phantom "Mid-session model switches" finding at the top of `tune`. Those
  messages now carry no model: they no longer count as a switch or set the
  session's model, in the parser and in the generated telemetry and
  budget-reminder hooks.
- A model switch was priced as if every cache read in the session had been
  uncached input, so the estimate could exceed the session's entire spend: on
  30 days of real logs, one phantom switch was priced at $92.32 against $26 of
  total spend. A switch is now priced from what the log records: the cache
  write on the new model's first turn, less what reading those tokens would
  have cost. Switching back to a model whose cache is still warm costs
  nothing. Cached session summaries from the old parser are re-parsed.
- The guided wizard dropped the project name, description and output
  directory typed on the Basics screen: the config was only recomputed after
  the tier and stack screens. The generated CLAUDE.md now carries them.

### Removed: third-party process packs

- The four community process packs (aihero, gstack, gtd, superpowers) and
  their wizard, config, and generator apparatus are removed. This reverses the
  v3 "aggregate external items" direction in favor of a focused setup.
- Backward compatible: legacy `--workflow <packname>` still resolves to its
  tier, and existing `.cc-rig.json` files that name a pack load cleanly with
  the pack ignored. Templates, the three workflow tiers, and the optional
  skill packs are unchanged.

### Changed: catalogs curated

- Skills reduced from 78 to 64 across 14 source repos (down from 17): only the
  14 orphaned process-pack skills were cut. The per-stack ECC skills and the
  superpowers set are kept.
- Plugins reduced from 96 to 87: nine non-dev-loop SaaS integrations removed
  (asana, discord, telegram, figma, shopify, twilio, sendgrid, amplitude,
  pagerduty). LSP, workflow, style, utility, autonomy, and the functional
  integrations remain.

### Changed: README and positioning

- The pitch stops crediting cc-rig with savings. Claude Code caches prompts
  on its own, and on Claude 5 pricing the cache breaks cc-rig prevents are
  worth a few cents to several dollars a month. The README, the wizard's
  Welcome and Confirm screens, the post-generation summary and the generated
  playbook no longer claim cc-rig "saves 80%+ on tokens" or "saves you
  money". They lead with the score, the safety guards and the fixes, and point
  to `/cc-rig tune` instead of `/cc-rig savings`. The README's tune sample is
  now real output instead of invented figures, and `docs/saving-tokens.md`
  prices Claude 5 models.
- README rewritten to the two-axis story: get it right with `init`, keep it
  right with `tune`. Mission-led opening, cache hygiene framed as one of the
  six things tune checks, all process-pack content removed, counts updated
  (87 plugins, 14 repos, Claude Code 2.1.287).
- Hero demo re-recorded on the tier-only wizard flow, plus a new `tune` demo
  (score, `--fix` diff, re-score).

### Internal

- New package `cc_rig/tune/` (`score.py`, `dimensions.py`, `fixers.py`) plus
  `cli_tune.py`, built as an additive layer over `doctor` and `baseline/`
  rather than refactoring either.
- 4451 tests green, ruff clean. Added 63 tune tests across `test_tune_score`,
  `test_tune_dimensions`, `test_tune_fixers`, and `test_tune_cli`; removed the
  process-pack test suite.
- New `test_pricing.py`, plus functional tests that run the generated cost
  hooks against a synthetic session log instead of checking their text.

## [3.2.1] - 2026-05-25

### Changed

- README: the `cc-rig savings` sample now shows the Rich-rendered output
  (hero panel, trend table with spend bars, cache-breaker callout, coaching
  read) instead of the pre-3.2 plain-text format. Docs-only patch; no code
  changes.

## [3.2.0] - 2026-05-25 Platform Spine

### Added: Longitudinal `cc-rig savings`

The `cc-rig savings` slash command is upgraded from a static cache-101 page
into a real longitudinal report driven by your local Claude Code session
logs. First step in the v3.2 platform-spine thesis: turn cc-rig from a
one-shot generator into a weekly return surface.

- **New CLI subcommand**: `cc-rig savings` reads
  `~/.claude/projects/<encoded-cwd>/*.jsonl`, aggregates the last 30 days
  (configurable via `--window-days`), and renders:
  - total tokens, cache read ratio, cost, savings vs uncached baseline,
  - a 4-week trend (configurable via `--weeks`),
  - top cache breakers (CLAUDE.md edits during a session, mid-session
    model switches) when present,
  - cross-project rank once you have at least two projects tracked.
- **Rendered report**: the human view is Rich-driven. A hero panel leads
  with dollars saved, a trend table carries per-week spend bars and a "you
  are here" marker, cache breakers surface as a severity-colored callout,
  and a short data-driven coaching read names the biggest lever. Color and
  box drawing adapt to the terminal and respect `NO_COLOR`; piped output
  and `--json` stay plain.
- **`~/.cc-rig/baseline.json`** (schema_version=1, frozen). User-scoped,
  cross-project. Stores weekly rollups so future runs can show trend and
  rank. Atomic writes; unreadable files fall back gracefully.
- **`~/.cc-rig/parse-cache.json`**: mtime-keyed parse cache so subsequent
  runs skip unchanged session files. Benchmark: under 2s for 100 sessions.
- Flags: `--no-baseline` (skip user-scoped state entirely), `--json`
  (machine output), `--weeks N`, `--window-days N`, `--tier <name>`.
- Generated `/cc-rig savings` playbook section now has a "Your numbers"
  preamble pointing at the CLI; cache-education content stays below.
- README gains a "Weekly practice" section above Install.

### Internal

- New package `cc_rig/baseline/` with `schema.py`, `paths.py`, `jsonl.py`,
  `savings.py`. All pure logic; the CLI module is a thin wire.
- 85 new tests: 80 unit (schema round-trip plus forward/backward compat,
  parser fixtures across three tiers, rollup math, week boundaries, cache
  breakers, cross-project rank) and 5 E2E covering the full CLI pipeline.
- Pricing table centralized with `PRICING_VERIFIED_DATE` for easy bumps.

### Added: Platform loop (audit, drift, refresh, retro)

cc-rig becomes a weekly return surface, not a one-shot generator. Four new
CLI subcommands read project state and session logs:

- **`cc-rig drift`**: reports three kinds of divergence: generated files
  edited by hand, `.cc-rig.json` changed since init, and the installed
  Claude Code drifting from cc-rig's pinned version. Read-only.
- **`cc-rig refresh <area>`**: re-runs one generator (agents, commands,
  skills, rules, settings, plugins, hooks, or all) with a unified-diff
  preview, then writes on confirm. Backs up overwritten files. Flags
  `--yes`, `--dry-run`, `--json`.
- **`cc-rig audit`**: scores the discipline signals that actually exist in
  session logs (cache hygiene, model pinning, cache read ratio, session
  shape) against the project tier and prints a tier-fit verdict. It does
  not invent slash-command compliance numbers, because that data is not in
  the JSONL stream.
- **`cc-rig retro`**: folds savings, audit, and drift into one weekly view
  with a single suggestion, and rolls the week into the cross-project
  baseline.

**Project state** (`.claude/cc-rig-state.json`, schema_version=1, frozen):
git-friendly, records a config hash, a config snapshot, and the last-run
timestamp for each subcommand. Written at init, preserved across
regeneration.

**Return trigger** (on by default): every generated CLAUDE.md ends with a
static one-line footer pointing at `/cc-rig retro` (cache-safe), and the
`session-context` SessionStart hook prints a nudge when it has been 7+ days
since the last retro.

The `/cc-rig` playbook gains four matching sections; new
`agent_docs/platform-loop.md` documents the loop thesis. 56 new tests
cover the state schema, the regenerate/diff engine, audit scoring, and the
four CLI surfaces.

## [3.1.0] - 2026-05-14

> This release bundles two phases of work. The v3.0 milestone (playbook pivot, tier rebrand, community process packs, session savings, attribution) was internal-only and never shipped to PyPI. v3.1 (CC v2.1.126 alignment, `.claude/rules/` generator, doctor checks 17–20) layered on top. PyPI users see one jump from 2.5.0 → 3.1.0; both phases ship together here.

### Added: Playbook & Tier System

- **Three-tier workflow model** (`quick`, `standard`, `rigorous`). Replaces the previous flat 5-workflow list as the primary axis. New `ResolvedWorkflow` dataclass and `_TIER_RESOLUTION` table in `cc_rig/presets/manager.py` are the single source of truth. Tiers compose with process packs independently.
- **Four community process packs** in `cc_rig/presets/packs/`: `gstack` (Garry Tan, 6 skills), `aihero` (mattpocock, 7 skills), `superpowers` (obra, 11 skills), `gtd` (OthmanAdi, 3 skills). Packs overlay curated process skills on a tier with full source attribution. Old workflow names (`gstack`, `aihero`, `superpowers`, `speedrun`, `verify-heavy`, `spec-driven`, `gtd-lite`) still work on the CLI and resolve to a tier + auto-pack via `_TIER_RESOLUTION`.
- **`/cc-rig` playbook command** with 6 subcommands: `dashboard`, `detail`, `recipes`, `savings`, `hooks`, `autonomous`. Teaches users how to use what was just generated. Generator at `cc_rig/generators/playbook.py`.
- **`PLAYBOOK.md`** written to project root during init. Tier-specific walkthrough explaining what was installed and the recipes for using it.
- **Session savings estimate** in the wizard's post-generation summary. Calculates cache-aware token savings based on the selected tier + features.
- **Brand attribution** for every community pack. Author, repo link, and license shown in the wizard pack picker, README, and generated `PLAYBOOK.md`. No community work appropriated without credit.
- **Wizard screens**: new `TierScreen` (three-radio tier picker) and `PackScreen` (optional process-pack overlay) replace the old single workflow picker. `WelcomeScreen` now leads with the value proposition; `ConfirmScreen` shows a value summary before generation.
- **Session-context nudge** in generated `CLAUDE.md`: one-line footer (`cc-rig | {tier} + {framework} | N plugins, N hooks | /cc-rig for help`) so users always know how to reach the playbook.

### Added: CC v2.1.126 Alignment

- **CC v2.1.126 alignment**. Pinned to v2.1.126 (verified live). All settings keys, hook events, and `.claude/rules/` mechanism verified against `code.claude.com/docs`.
- **`.claude/rules/` generator** (CC v2.1.108+). New `cc_rig/generators/rules.py` produces detection-driven path-scoped instruction files: `tests.md` (any recognized language), `migrations.md` (Django/FastAPI/Rails/Laravel/Phoenix/Spring frameworks), `security.md` (high-rigor tiers, eager-load), `frontend.md` (Next.js/Express or TypeScript). Frontmatter `paths` field uses brace-expansion globs.
- **Settings keys**: `attribution: {commit: "cc-rig"}` (always-on, CC v2.1.105+), `autoMemoryEnabled: true` (explicit, CC v2.1.59+), `worktree.symlinkDirectories` (language-driven: `.venv`/`node_modules`/`target`/`vendor`).
- **`autoMode` `$defaults` extension** (CC v2.1.119+). Generated `autoMode.{environment, allow, soft_deny}` arrays now lead with the literal `"$defaults"` string to merge with CC's built-in rules instead of replacing them.
- **`mcp_tool` hook handler type** (CC v2.1.118+) added to schema validators.
- **Plugin catalog expansion** (80 → 96, cap 120). Net 16 new entries: `amplitude`, `postgres-mcp`, `mysql-mcp`, `redis-mcp`, `sqlite-mcp`, `planetscale-mcp`, `vercel-deploy`, `fly-deploy`, `railway-deploy`, `semgrep`, `trivy`, `gitleaks`, `snyk`, `bandit-security`, `braintrust`, `langfuse`. All v3.1 additions are expert opt-in only. Selection criteria documented in registry docstring.
- **Doctor Check 17: `settings_key_validity`**. Validates every key in generated `settings.json` against pinned 87-key v2.1.126 schema. Warns on unknown keys (typos, deprecated, or new).
- **Doctor Check 18: `rules_glob_syntax`**. Validates `.claude/rules/*.md` frontmatter is parseable with a `paths:` array of glob entries.
- **Doctor Check 19: `model_id_validity`**. Validates agent `model:` frontmatter resolves to a known alias, full Anthropic ID, or 1M-context variant.
- **Doctor Check 20: `plugin_marketplace_format`**. Validates `enabledPlugins` keys match `name@marketplace` format.
- **Pinned CC version line in generated CLAUDE.md**. Project identity section now shows `Claude Code: v2.1.126 (cc-rig pinned)`.

### Changed
- **`settings.json` shallow-merge on regenerate** (Gate 2 contract). Generator-owned keys (`_OWNED_KEYS`: `permissions`, `hooks`, `enabledPlugins`, `effortLevel`, `attribution`, `autoMemoryEnabled`, `autoMode`, `showThinkingSummaries`, `includeGitInstructions`, `sandbox`, `worktree`) are overwritten on `cc-rig init` rerun. User-added top-level keys (e.g., `language`, `env` extensions) survive.
- **`FileTracker.is_user_authored(rel_path, prior_manifest)`** added. Generators (currently `rules.py`) skip user-authored files while still overwriting their own prior output via the persisted manifest.
- **Orchestrator** loads `.claude/.cc-rig-manifest.json` on rerun and threads it to generators that distinguish user content from prior cc-rig output.
- **Pricing tables** in `agent_docs/cache-friendly-workflow.md` and `docs/saving-tokens.md` bumped to Opus 4.7. cc-rig uses model aliases (`opus`/`sonnet`/`haiku`) which auto-resolve, so no agent file changes were needed.

### Architecture
- **Phase order** (decision 2026-05-03, semver assigned 2026-05-04): v3.1.0 CC alignment ships first; v3.2.0 platform spine builds on aligned base; v3.3.0 distribution after; Twitter outreach is a project phase, not a release; v3.4.0 strategic forks last.
- **Pinned CC version constants** added to `cc_rig/config/cc_version.py`: `PINNED_CC_VERSION = (2, 1, 126)` and `PINNED_CC_VERSION_STR = "2.1.126"`.

---

## [2.5.0] - 2026-04-11

### Added
- **Plugin catalog expansion** (47 to 80 plugins). 3 new LSP plugins (elixir-ls, scala-metals-lsp, dart-lsp), 18 integration (figma, stripe, aws, gcp, azure, datadog, pagerduty, grafana, redis, mongodb, twilio, sendgrid, cloudflare, docker, terraform, heroku, railway, shopify), 7 workflow (test-runner, doc-generator, perf-profiler, migration-helper, dependency-updater, changelog-generator, api-design), 3 style (concise-output-style, mentor-output-style, team-lead-output-style), 2 utility (config-doctor, context-optimizer). Elixir now has LSP support via elixir-ls.
- **Template plugin enrichment**. FastAPI gets docker, Django and Rails get redis, Next.js gets stripe, Spring gets aws. Spec-driven, superpowers, and verify-heavy workflows get test-runner and doc-generator.
- **GitHub Actions workflow generation**. New `github_actions` feature flag generates `.github/workflows/claude.yml` using `anthropics/claude-code-action@v1`. Triggers on pull_request (opened, synchronize) and issue_comment (created, filtered to @claude mentions). verify-heavy and superpowers workflows add a separate security-review job that checks for auth issues, injection risks, and credentials. Enabled by default for all workflows except speedrun. Toggleable in the features screen and expert mode.

---

## [2.4.1] - 2026-04-04

### Added
- **Output hygiene guardrails**. Every generated CLAUDE.md now includes 2 framework-specific compact command hints in the guardrails section (e.g., "Use `pytest -q --tb=short` for exploration"). Covers all 16 templates with framework-aware advice for test runners, dependency tools, and git commands. Reduces context token usage from verbose tool output.
- **Output hygiene in agent docs** (B1+ context_awareness). Projects with context awareness get an "Output Hygiene" section in `agent_docs/harness.md` covering general best practices: git diff stat, quiet test flags, dependency depth limits, large file handling, and RTK as a complementary tool.
- **Doctor Check 14: RTK detection**. Detects RTK (rtk-ai/rtk, tool output compression) binary in PATH and checks if its Bash auto-rewrite hook is configured in settings.json (project or global). Info-level only, never a warning. Reports version and configuration status.
- **JSONL deduplication**. Budget-reminder and session-telemetry hooks now collapse consecutive assistant entries with identical cache token pairs, filtering PRELIM entries from extended thinking. Fixes 2-3x token inflation in sessions with extended thinking enabled. Safe by construction: no-op when no duplicates exist.
- **`/session-health` command** (B2+ standard). Live current-session analysis: raw entry count, dedup ratio, token breakdown, cache read ratio, estimated cost. Reports raw data without thresholds.
- **Doctor Check 13: JSONL accounting**. Reports raw vs deduplicated entry count from the most recent session JSONL. Uses new `DoctorResult.info` field for informational (non-warning) output.
- **`cache_read_ratio` and `entries_deduped`** added to session telemetry records. `/health` command now shows cache ratio per session and dedup activity.

### Changed
- **Doctor CLI output**. Color-coded sections (green/yellow/red/cyan), project name header, horizontal rules, summary line with counts. Respects `NO_COLOR` and TTY detection.
- **Budget-reminder hook output**. Structured token breakdown (input, output, cache create, cache read), cache ratio percentage, ANSI color with `NO_COLOR` support.
- **Session-telemetry hook output**. Compact one-liner with turns, tokens, cost, cache ratio and dedup count.
- **CLAUDE.md line counts**. All per-workflow targets increased by 2 lines (compact command guardrails).

---

## [2.3.0] - 2026-04-03

### Added
- **Conditional hooks** (CC v2.1.85+). Hooks now generate an `if` field using permission rule syntax for precise targeting. Lint and typecheck hooks fire only on `Bash(git commit*)`, block-rm-rf on `Bash(rm *)`, block-main on `Bash(git push*)`. Reduces false triggers on unrelated Bash commands.
- **Agent `initialPrompt`** (CC v2.1.83+). Agents can auto-submit their first turn. Explorer, build-fixer, and techdebt-hunter now ship with initial prompts so they start working immediately without user input.
- **Auto mode** (CC v2.1.89+). `"auto"` is now a valid permission mode. When selected, cc-rig generates an `autoMode` block in settings.json with workflow-aware allow/soft_deny rules. High-rigor workflows (superpowers, verify-heavy, spec-driven) get stricter deny rules.
- **4 new CC events**. VALID_CC_EVENTS expanded from 21 to 25: `CwdChanged` (v2.1.83), `FileChanged` (v2.1.83), `TaskCreated` (v2.1.84), `PermissionDenied` (v2.1.89).
- **Feature compat checks** for conditional_hooks, initial_prompt, and auto_mode. `cc-rig doctor` warns when detected CC version is too old for these features.

### Changed
- **Minimum CC version** bumped from v2.1.50 to v2.1.83. Reflects new features requiring v2.1.83+ (initialPrompt, CwdChanged/FileChanged events, conditional hooks).

---

## [2.2.0] - 2026-04-03

### Added
- **Context Intelligence**. New harness features that help Claude preserve state through compaction and track token spend:
  - **Compaction Survival** (all projects). Generated CLAUDE.md now includes a "Compaction Survival" section with project-specific preserve/discard instructions so Claude retains critical context when the context window is compacted.
  - **context_awareness flag** (B1+ lite). Generates a PreCompact hook (`context-survival.sh`) that outputs project essentials before compaction, plus cache-break vector documentation in `harness.md` and a guardrail line in CLAUDE.md.
  - **session_telemetry flag** (B2+ standard). Generates a Stop hook (`session-telemetry.sh`) that writes turn count, token usage and estimated cost to `.claude/telemetry.jsonl`. Includes a `/health` command for quick session metrics.
- **Cache guardrails** (all projects). 4 unconditional guardrails in generated CLAUDE.md: never edit CLAUDE.md mid-session, never toggle hooks/MCP/plugins, never switch models (use subagents), load memory via Read tool.
- **Fork-session guidance** (spec-driven, aihero, superpowers). Workflow principles now include `--fork-session` tip for parallel investigations that share the prompt cache prefix (3 forks cost 1.55x vs 3.75x for 3 independent sessions).
- **Doctor cache-friendliness check**. `cc-rig doctor` now scans CLAUDE.md's static zone for anti-patterns (dates, timestamp markers) that break prompt cache. Warning-only, with line number and fix suggestion.
- **Doctor cache health check**. `cc-rig doctor` now parses the most recent Claude Code session JSONL to calculate cache hit ratio. Warns if ratio falls below 40%. Graceful skip when no session data exists.
- **Expanded cache-friendly-workflow.md**. Agent doc expanded from 23 to 62 lines: 14 cache-break vectors (from CC internals), pricing impact table, TTL info (5-min Pro, 1-hr Max), session forking tip.

### Changed
- **HarnessConfig** now has 6-position level flags (was 4): `context_awareness` and `session_telemetry` added as boolean fields with level-based derivation.
- **CLAUDE.md line counts** increased by 4 lines across all workflows (cache guardrails). Workflows with spec_workflow + worktrees get 2 additional lines (fork-session tip).

---

## [2.1.0] - 2026-03-23

### Added
- **Plugin catalog expansion** (24 to 47 plugins). 5 new LSP plugins (ruby-lsp, clangd-lsp, kotlin-lsp, lua-lsp, swift-lsp), 8 integration (asana, context7, discord, greptile, laravel-boost, playwright, serena, telegram), 8 workflow (code-simplifier, claude-md-management, skill-creator, frontend-design, agent-sdk-dev, mcp-server-dev, plugin-dev, claude-code-setup), 2 style (explanatory-output-style, learning-output-style). New "style" plugin category.
- **ECC skills integration** (55 to 78 skills). 23 framework-specific skills from affaan-m/everything-claude-code (97K stars): Python (2), Django (4), Spring Boot (4), Laravel (4), Go (2), Rust (2), plus 5 cross-cutting SDLC skills. New "ecc-sdlc" skill pack.
- **Template agents** (13 to 19 agents). 4 language-specific reviewers (python-reviewer, go-reviewer, rust-reviewer, java-reviewer) auto-added per template. 2 cross-cutting agents: build-fixer (all workflows), e2e-runner (non-CLI, non-speedrun).
- **Agent frontmatter enhancement**. New `effort` and `skills` optional fields on agent definitions. Opus agents (architect, pr-reviewer, pm-spec, security-auditor) set to `effort: high`.
- **Settings enhancement**. `effortLevel` per workflow (speedrun=low, standard/gstack/aihero/gtd=medium, spec-driven/superpowers=high). `includeGitInstructions: false` for high-rigor workflows (superpowers, verify-heavy, spec-driven) to reduce CLAUDE.md duplication.
- **CC platform alignment**. VALID_CC_EVENTS expanded from 9 to 21 (StopFailure, PostCompact, WorktreeCreate, WorktreeRemove, PostToolUseFailure, PermissionRequest, ConfigChange, InstructionsLoaded, Elicitation, ElicitationResult, TeammateIdle, TaskCompleted). LSP added to VALID_CC_TOOLS.

### Changed
- **Ruby template now has LSP**. ruby-lsp plugin auto-enabled for Rails template (was "no official LSP plugin yet").
- **csharp-lsp binary name**. Fixed `requires_binary` from "OmniSharp" to "csharp-ls" (matches current CC plugin).
- **Template plugin enrichment**. nextjs gets frontend-design + playwright; laravel gets laravel-boost; express gets playwright.
- **Workflow plugin enrichment**. spec-driven, superpowers, verify-heavy get code-simplifier plugin.
- **Django skills are now a superset of FastAPI/Flask**. All Python templates share ecc-python-patterns + ecc-python-testing; Django additionally gets 4 Django-specific ECC skills.

---

## [2.0.0] - 2026-03-22

### Added
- **Workflow-first pivot** - Workflow is now the primary axis. The wizard asks "how do you work?" before "what are you building?". Stack (template) is secondary, optional enrichment.
- **7 workflows** (was 5) - Added **gstack** (Garry Tan's cognitive gears), **aihero** (Matt Pocock's PRD-driven flow), **superpowers** (obra's full SDLC suite), and **gtd** (persistent task tracking with planning-with-files). Backward-compatible aliases: `verify-heavy` resolves to `superpowers`, `gtd-lite` resolves to `gtd`.
- **Process skills** - New concept: workflow-specific community skills that define the development process. Each community workflow installs its original skills with full attribution (e.g., gstack installs `/plan-ceo-review`, `/plan-eng-review`, `/gstack-review`, `/ship`, `/document-release` from garrytan/gstack). 14 new process skills from 3 repos. Skill catalog grows from 41 to 55.
- **CLAUDE.md process skills section** - Generated CLAUDE.md includes a dedicated "Process Skills" section with skill descriptions, workflow chain, and source attribution link.
- **Workflow preset v2 format** - Presets now include `version`, `process_skills`, `source`, and `source_url` fields. v1 presets handled gracefully (defaults apply).
- **3 new skill repos** - garrytan/gstack (6 skills), mattpocock/skills (7 skills), OthmanAdi/planning-with-files (1 skill). Downloader now supports per-skill branch override and recursive subdirectory downloads.
- **3 new E2E scenarios** - Gstack+FastAPI, Aihero+Generic, Superpowers+Django validated end-to-end.
- **`test_process_skills.py`** - Dedicated test suite (8 test classes) covering process skill resolution, workflow attribution, alias resolution, and CLAUDE.md integration.

### Changed
- **Wizard order** - Workflow screen now appears before Stack (Template) screen in both guided and quick flows. Stack defaults to Generic when no framework is detected.
- **Template picker UX** - Generic template relabeled from "DevOps, monorepos, docs, infra" to "No specific stack, just the workflow". Generic is now the default selection. Framework templates use `Language / Framework` labels for visual grouping.
- **Features screen** - Workflow-recommended features are now locked on (disabled checkbox, labeled "[included with workflow]"). Conflicting features are locked off (labeled "[not available with workflow]"). Only freely toggleable features remain interactive.
- **Skill packs screen** - Now workflow-aware. Shows overlap labels ("fully covered by your workflow", "N/M covered", "your workflow is comprehensive, this adds depth") instead of blind template-based recommendations.
- **`compute_defaults()`** - Reads `process_skills`, `source`, and `source_url` from workflow presets. Populates `ProjectConfig.process_skills`, `workflow_source`, `workflow_source_url`.
- **`ProjectConfig`** - Three new fields: `process_skills: list[str]`, `workflow_source: str`, `workflow_source_url: str`. Full serialization support.
- **Validator** - New `_check_process_skills()` validates process skill names exist in catalog.
- **Doctor** - New health check verifies process skill files are installed.
- **Display** - Summary output shows process skill count and source attribution.

---

## [1.4.4] - 2026-03-09

### Fixed
- **Textual import crash** - `cc-rig init` crashed with `ModuleNotFoundError: No module named 'textual'` when textual wasn't installed. Moved `should_use_textual()` from `textual_wizard.py` (which imports textual at module level) to `tui.py` (which guards optional imports with try/except). The stdlib fallback now works correctly.

### Changed
- **TUI deps are now default** - `rich`, `textual` and `prompt_toolkit` moved from optional `[rich]` extra to default dependencies. `pip install cc-rig` gives the full TUI experience. The `[rich]` extra is kept empty for backwards compatibility.
- **Expert screen tab styling** - Tab headers now use bright colors (cyan active, grey-blue inactive) instead of the default Textual styling that was nearly invisible on dark backgrounds. Added "Press 1-4 or click tabs to switch" hint.
- **Install instructions** - README now shows venv creation + activation + pip install as a 3-step block. Added troubleshooting tips for PEP 668 errors and pipx alternative. Removed zsh bracket quoting FAQ (no longer needed since `[rich]` extra is gone).
- **README opening** - Rewritten from feature list to problem framing ("Most Claude Code projects run on a CLAUDE.md and not much else"). Aligns with blog post tone.
- **README badges** - Replaced "zero dependencies" badge with live PyPI version badge.

---

## [1.4.3] - 2026-03-08

### Fixed
- **Clean leaves harness.md behind** - `FileTracker` now tracks files written in the current session so multi-pass writes (B1→B2→B3 harness appending to `agent_docs/harness.md`) are not falsely marked as pre-existing. Previously `cc-rig clean` restored the B1 backup instead of deleting the file.

### Changed
- **README FAQ** - Added troubleshooting entries for Python 3.8 on older Linux distros and zsh bracket quoting.

---

## [1.4.2] - 2026-03-08

### Fixed
- **Path traversal in skill removal** - `cc-rig skills remove` now validates the skill name against the skills directory root, preventing `../../` traversal in user-supplied names.
- **Path traversal in skill downloads** - GitHub API filenames are validated for path separators and `..` before writing, preventing malicious repo responses from writing outside `.claude/skills/`.
- **Path containment in FileTracker** - `write_text()` now verifies resolved paths stay within the output directory, raising `ValueError` on traversal attempts.
- **Worktree spawn permissions** - `--dangerously-skip-permissions` is no longer unconditionally passed to spawned Claude processes. Now opt-in via `cc-rig worktree spawn --skip-permissions`.
- **Shell injection regex** - Added newline (`\n`, `\r`) to `_SHELL_INJECTION_RE` character class, closing a bypass where multi-line command strings could inject additional shell statements.
- **Preset name validation** - `create_preset()` and `install_preset()` now reject names containing path separators or special characters (must match `[a-z0-9][a-z0-9_-]*`).
### Changed
- **README FAQ** - Corrected FAQ answer that incorrectly stated "There's no 'update' command." Now references `cc-rig config update`.
- **PyPI metadata** - Added `[project.urls]` (Homepage, Repository, Changelog) and MIT license classifier to `pyproject.toml`.
- **README images** - Switched logo and demo GIFs to absolute GitHub raw URLs for PyPI rendering.
- **Typing standardization** - Replaced `List[T]`/`Optional[T]` with lowercase generics in `cc_rig/worktree/` and `cc_rig/generators/agents.py`.
- **Import hygiene** - Moved `import re` and `import os` from function bodies to module level in `state.py` and `downloader.py`.
- **Error reporting** - `_download_community_skills()` now surfaces exception details in the failure report instead of silently swallowing them.
- **Publishing docs** - Added `docs/publishing.md` with PyPI build and upload procedure.

---

## [1.4.1] - 2026-03-06

### Added
- **Multi-worktree orchestration** - `cc-rig worktree spawn/list/status/pr/cleanup`. Launch multiple Claude sessions in parallel worktrees from the terminal. Each task gets an isolated git worktree and branch (`wt/<slug>`). State tracked in `.claude/worktrees.json`. PID-based status monitoring, PR creation via `gh`, batch cleanup. New `cc_rig/worktree/` package (state, manager, orchestrator). 92 new tests across 4 test files.
- **`cc-rig config update`** - Re-run wizard with existing config values pre-filled, show diff, regenerate on confirmation. Supports `--quick` and `--expert` modes.
- **`cc-rig doctor --check-compat`** - Check generated config features against installed Claude Code version. Warns about plugins, background agents, worktree isolation, and settings.local.json on older CC versions.
- **Community preset validation** - `validate_preset()` validates schema before installation. Template presets require `project_type`; workflow presets require `agents` and `commands` as lists.

### Changed
- **Data extraction (M6)** - Moved `_COMMAND_DEFS` (19 commands) and `_AGENT_DEFS` (13 agents) from inline Python to `cc_rig/data/commands.json` and `cc_rig/data/agents.json`. Pure refactor, zero behavior change.
- Added `package-data` to `pyproject.toml` to ensure JSON data files are included in wheels.
- TUI worktree feature description expanded with usage examples and workflow context.
- Workflow detail panels now show `parallel-worker` agent and `worktree` command for spec-driven, gtd-lite, verify-heavy.
- Generated CLAUDE.md worktree section includes `cc-rig worktree` CLI examples.
- `#feature-details` panel max-height bumped from 10 to 16 for longer descriptions.

---

## [1.4.0] - 2026-03-05

### Added
- **Official Claude Code Plugin Integration** - cc-rig now curates official Anthropic marketplace plugins alongside skills, hooks, agents, commands, and MCPs.
  - New `cc_rig/plugins/` module with 24-plugin catalog across 5 categories: LSP (7), integration (10), workflow (5), autonomy (1), utility (1).
  - `PluginRecommendation` dataclass on `ProjectConfig` with full serialization support.
  - Smart defaults: `compute_defaults()` resolves plugins by language (LSP), template (integrations), and workflow (workflow plugins). GitHub MCP replaced by github plugin (self-contained, auto-start).
  - `enabledPlugins` section in generated `settings.json` - format: `"name@marketplace": true`.
  - **Ralph-loop plugin** - official Anthropic autonomous loop as alternative to cc-rig's loop.sh. Harness picker shows 6th option. Custom-style B1/B2 feature confirms (task_tracking, budget_awareness, verification_gates). Mutual exclusion with `autonomy_loop`.
  - Expert mode plugins category - multi-select from full catalog (TUI tab + CLI).
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
- **Generation log**: `cc-rig init` now saves output to `.claude/cc-rig-init.log` - file list, validation results, next steps. Symlink at project root for discoverability. ANSI codes stripped. Log saved on both success and validation failure. Not tracked in manifest (preserved by `cc-rig clean`).

---

## [1.3.1] - 2026-03-03

### Added
- **V2 Runtime: Budget Enforcement + Cost Tracking** (Path A + Path B)
  - `budget-reminder.sh` (Stop hook) now parses JSONL session logs via inline Python heredoc - shows actual session tokens + estimated cost with model-aware pricing (Opus/Sonnet/Haiku auto-detected from session log). Project-scoped JSONL lookup (not global). Graceful degradation: no python3 or no JSONL → shows "unavailable", never blocks.
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
- `.claude/settings.local.json` generation - personal permission overrides file (`preserve_on_clean=True`)
- 66 new tests across 4 test files:
  - `test_memory_content.py` (18 tests) - memory file content, anti-ballooning rules, MEMORY-README
  - `test_workflow_diff.py` (17 tests) - cross-workflow comparison (speedrun vs standard vs verify-heavy vs spec-driven vs gtd-lite)
  - `test_command_frontmatter.py` (18 tests) - YAML frontmatter parsing, `$ARGUMENTS` validation, `_COMMAND_DEFS` consistency
  - `test_permission_modes.py` (13 tests) - default vs permissive mode comparison, allow/deny lists
- 12 tests (10 unit + 1 integration + 1 E2E) for settings.local.json

### Changed
- Refactored `_script_lint`/`_script_typecheck` into shared `_script_check_on_commit` helper (settings.py)
- Refactored `load_template`/`load_workflow` into shared `_load_preset` helper (manager.py)
- Polished TUI wizard screen descriptions (TemplateScreen, WorkflowScreen, FeaturesScreen)

### Fixed
- Version bump: `pyproject.toml` and `__init__.py` synced from 1.0.0 to 1.3.0
- Removed `memory-stop` prompt hook - Claude wraps JSON in markdown, causing validation failure every session exit. Auto-memory already handles learning persistence.
- Fixed `ruff format` issues in `textual_wizard.py` and `generate.py` (CI was failing)
- CI verified green on Python 3.9, 3.10, 3.11, 3.12

---

## [1.3.0] - 2026-03-02

### Added

**Generic Template**
- `generic` - Language-agnostic template for DevOps, monorepos, docs, infra projects
- First-class option on template picker (first in list), no framework or tool commands
- Uses excellent language-agnostic content from existing `generic.py` template module
- Default MCPs: GitHub only (no database assumption)
- Never auto-detected - user-selected only

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
- `laravel` - PHP + Laravel: MVC, Eloquent ORM, Artisan, PHPUnit, PHP-CS-Fixer
- `express` - Node.js + Express: middleware patterns, Router, Jest, ESLint, PM2 deployment
- `phoenix` - Elixir + Phoenix: LiveView, Ecto, ExUnit, Credo, mix release
- `go-std` - Go standard library: idiomatic Go patterns, go test, golangci-lint, no framework coupling

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
- 4 agent docs (architecture, conventions, testing, deployment) - framework-specific
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
