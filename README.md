<p align="center">
  <img alt="cc-rig" src="https://raw.githubusercontent.com/runtimenoteslabs/cc-rig/main/assets/cc-rig-logo.png" width="200">
</p>

<h3 align="center">Set up Claude Code right, then keep it right.</h3>

<p align="center">
  <a href="#the-two-commands">Two Commands</a> ·
  <a href="#why-cache-hygiene">Why Cache</a> ·
  <a href="#install">Install</a> ·
  <a href="#cc-rig-tune">Tune</a> ·
  <a href="#what-gets-generated">What Gets Generated</a> ·
  <a href="#faq">FAQ</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-MIT-f59e0b?style=flat-square" alt="MIT License">
  <a href="https://pypi.org/project/cc-rig/"><img src="https://img.shields.io/pypi/v/cc-rig?style=flat-square&color=22c55e" alt="PyPI"></a>
</p>

---

cc-rig started with one mission: make setting up Claude Code painless, back when the config surface was a scattered mess of docs and community repos. That part is mostly solved now. Native tooling scaffolds a CLAUDE.md and the marketplace has the plugins, so getting a config is easy. Getting it right is still the hard part: most configs are generic, bloat the context window, skip the guards that stop a destructive command and quietly break the prompt cache.

**cc-rig gets your config right, then keeps it right.** `cc-rig init` generates a lean, stack-tailored setup in one command: a tight CLAUDE.md, hooks that gate on your framework's real test and lint commands, plus agents, skills, memory and curated plugins. `cc-rig tune` then scores that config on six published dimensions, ranks what to fix and applies the safe fixes, so it stays correct as your project and Claude Code both move.

```bash
cc-rig init     # generate a lean, stack-tailored config
cc-rig tune     # score it, rank what to fix, apply the safe fixes
```

Native Claude Code files, nothing proprietary. Delete cc-rig tomorrow and your project keeps working.

<p align="center">
  <img src="https://raw.githubusercontent.com/runtimenoteslabs/cc-rig/main/assets/demo-2-guided.gif" alt="cc-rig demo" width="800">
</p>

---

## The two commands

### `cc-rig init` writes the config

Tell it what you're building and how you like to work. It writes 30-65 native Claude Code files tuned to your framework: a cache-aware CLAUDE.md, settings with hooks and permissions, specialized agents, slash commands, skills, memory and curated plugins.

A typical Claude Code project:

```
CLAUDE.md
```

After `cc-rig init` (one command, two questions, ~30 seconds):

```
CLAUDE.md                    # Cache-aware, framework-tuned, under 100 lines
CLAUDE.local.md              # Personal preferences (gitignored)
.claude/settings.json        # Permissions, hooks, 87 curated plugins
.claude/agents/              # 3-19 specialized agents with YAML frontmatter
.claude/commands/            # 6-19 slash commands matched to your tier
.claude/hooks/               # Auto-format, lint gates, safety blocks
.claude/skills/              # Community skills from 14 repos
.github/workflows/claude.yml # Claude reviews your PRs (opt-out for quick tier)
agent_docs/                  # Framework-specific guides (auto-loaded via @import)
memory/                      # Git-tracked team knowledge across sessions
```

### `cc-rig tune` keeps it correct

Run it any time. It reads your config, plus your session history when there is one, scores six weighted dimensions and ranks the fixes by severity. Where your own logs can measure what a cache problem costs, the finding carries that figure.

Real output on a hand-grown CLAUDE.md with a month of session logs (44 synthetic Opus 5.5 sessions, the same scenario as the tune demo):

```
$ cc-rig tune
╭──────── cc-rig tune · acme-api ────────╮
│ 66 / 100   Getting There               │
│ cache reads 95%   ·   44 sessions seen │
╰────────────────────────────────────────╯
Dimension           Weight              Score
Cache hygiene          30%  ████████··     75
Safety guards          20%  ██········     20
Context discipline     15%  ██████████    100
Workflow fit           15%  ███████···     70
Verification           10%  █████·····     50
Currency               10%  ████████··     85

Top opportunities (ranked by impact)
  1. Add a verification gate   [high]  [safe fix]
     Require tests/lint to pass before committing (guardrail or commit hook).
  2. Add destructive-command protection   [high]  [safe fix]
     Block rm -rf, DROP TABLE, etc. via a PreToolUse hook or a guardrail.
  3. Remove the date/timestamp from CLAUDE.md's static section   ~$0.02/mo  [--fix-unsafe]
     Line 3 changes the cached prefix, re-creating it every session. Move it below '## Current Context' or into CLAUDE.local.md.
  4. Add a Commands section to CLAUDE.md   [med]
     List build/test/lint commands so Claude uses the right tooling.
  5. Add a block-push-to-main protection   [med]  [safe fix]
     Prevent accidental direct pushes to the default branch.
  6. Add a secrets guardrail   [med]  [safe fix]
     Tell Claude never to read, output, or log API keys, tokens, or secrets.
  7. Pin the Claude Code version in CLAUDE.md   [low]  [safe fix]
     A pinned version line makes drift visible after a CC upgrade.

Run `cc-rig tune --fix` to apply 5 safe fix(es).
```

The cache finding is real but small here: this CLAUDE.md is only 251 bytes, so re-writing it 44 times a month costs about two cents. The same date in a 2,000-token CLAUDE.md across 100 sessions a month would cost roughly $1.60. Either way, the missing safety guard and verification gate are what actually put this project at risk, so they rank first.

`cc-rig tune --fix` applies the safe fixes (backed up via FileTracker), shows a diff and re-scores. `--ci` gates a pipeline on a threshold. `--badge` emits a Shields.io endpoint. Full detail in [the tune section](#cc-rig-tune).

---

## Why cache hygiene

Claude Code assembles every request as a prefix (tools, system prompt, your CLAUDE.md, then the conversation) and caches it. If the prefix is byte-for-byte identical to a previous request, the cached tokens cost **10% of the uncached price** ($0.20/M vs $2.00/M on Sonnet 5.5). A single changed byte invalidates everything after it, and that part is written to the cache again at the cache-write rate (1.25x to 2x the uncached price).

Claude Code does the caching on its own, so cc-rig doesn't claim the savings. What a config can do is break it: a date in the static zone, a hook toggled mid-session, an inlined memory file that changes every session, a model switch. What that costs depends on your CLAUDE.md size, model and session count, and `cc-rig tune` reports it from your own logs. cc-rig treats it as a correctness bug, not a cost line: the config is doing something it shouldn't, whatever the bill says. Inside a session, Claude Code's own `/cost` names the likely cause of each cache miss. `cc-rig tune` works one step earlier, on the repo itself: it traces the break to a specific config line and patches it before the next session starts.

---

## Install

**Try it without installing anything:**

```bash
uvx cc-rig init        # or: pipx run cc-rig init
```

[uv](https://docs.astral.sh/uv/) fetches cc-rig and its dependencies into a
throwaway environment and runs it. Nothing is added to your system, and you
always get the latest release. Good for a one-off run or a first look.

**Install it permanently:**

```bash
python3 -m venv ~/.cc-rig
source ~/.cc-rig/bin/activate
pip install cc-rig
```

Python 3.9+. Includes the full-screen TUI wizard with arrow keys, radio buttons, checkboxes, colors, tables and progress bars.

> **Already have a venv?** Just `pip install cc-rig` inside it. The venv step above is for first-time setup. Without it, macOS and Linux block global pip installs.
>
> **Prefer pipx?** `pipx install cc-rig` works too. No venv needed.
>
> **Next session?** Remember to `source ~/.cc-rig/bin/activate` before running `cc-rig`.

- Compatible with Claude Code **v2.1.287** (pinned, verified live). Works on v2.1.83+. Older versions or missing installs get a warning, but cc-rig generates everything anyway.

---

## Getting Started

### Start a new project

The interactive wizard walks you through it. You get a full-screen TUI with arrow-key navigation, radio buttons and checkboxes.

```bash
cc-rig init
```

Or skip the wizard and specify everything directly:

```bash
cc-rig init --workflow rigorous --template fastapi --name my-api
```

### Set up an existing project

Already have a codebase? cc-rig detects your stack from `package.json`, `go.mod`, `Cargo.toml`, `pyproject.toml` and more. It proposes what to add and won't touch existing files.

```bash
cd my-existing-project
cc-rig init --migrate
```

<details>
<summary>See it in action</summary>

<p align="center">
  <img src="https://raw.githubusercontent.com/runtimenoteslabs/cc-rig/main/assets/demo-5-auto-detect.gif" alt="cc-rig auto-detection demo" width="800">
</p>
</details>

### Use a team config

A teammate already set up cc-rig? Load their config and get the same setup:

```bash
cc-rig init --config .cc-rig.json
```

### Quick picker

Don't want the full wizard? Pick from numbered lists:

```bash
cc-rig init --quick
```

---

## cc-rig tune

`cc-rig tune` scores your Claude Code config, ranks what to fix and applies the safe fixes in place. It reuses the same engine that generates configs, so a recommendation and an applied fix are the same code path.

### The score model

A composite 0-100 score, decomposed into published, impact-weighted dimensions. The weights are public, so you can audit the number.

| Dimension | Weight | What it measures |
|---|---|---|
| Cache hygiene | 30% | static/dynamic split, no timestamps in the static prefix, `@import` for agent docs, no inlined memory, MCP schema stability |
| Safety guards | 20% | PreToolUse destructive-command block, secret handling, block-main hook |
| Context discipline | 15% | CLAUDE.md token size, memory file caps, context-window alerts |
| Workflow fit | 15% | tier matches the detected stack, hooks match the tool commands |
| Verification | 10% | test, lint and typecheck gates wired into hooks |
| Currency | 10% | config aligned to the current Claude Code version and schema |

Findings rank by severity. Cache findings also carry a monthly dollar figure when your session logs (`~/.claude/projects/`) can ground one, computed with zero extra LLM calls from your CLAUDE.md size, your model's cache write and read rates, your cache TTL mix and your session count. A figure of $1/mo or more ranks ahead of the severity order. Anything smaller is shown but never outranks a structural finding of the same severity, so a missing destructive-command guard always sits above a few cents of cache churn. With no session history, the dollar figures are left out rather than guessed.

### Three modes

```bash
cc-rig tune              # the human report (score + ranked opportunities)
cc-rig tune --fix        # apply safe fixes, show a diff, re-score
cc-rig tune --fix-unsafe # also apply fixes that relocate content (opt-in)
cc-rig tune --ci         # exit non-zero below --min-score (pipeline gate)
cc-rig tune --json       # machine-readable
cc-rig tune --badge      # Shields.io endpoint JSON
```

`--fix` applies additive, safe changes only by default (version pin, guardrail additions, verification gates): every change is backed up to `.cc-rig-backup/` via FileTracker. The safety contract is the Ruff and Snyk model: never apply a fix that could introduce a worse problem than it removes. Anything that relocates user content is opt-in behind `--fix-unsafe`.

A freshly generated project scores 100/100 with zero opportunities on the quick and standard tiers, for all 16 stacks. On rigorous, 13 stacks score 100. Django, Go stdlib and Spring Boot score 98, because their framework guidance pushes CLAUDE.md past the size threshold. The tool grades its own output to the same bar it grades yours, and it says so when that output falls short.

---

## How It Works

cc-rig is **tier-first**. You pick how you like to work, then optionally pick your stack. The two axes compose independently: any tier works with any template.

<details>
<summary>Full showcase: 16 templates x 3 tiers x harness levels</summary>

<p align="center">
  <img src="https://raw.githubusercontent.com/runtimenoteslabs/cc-rig/main/assets/demo-4-showcase.gif" alt="cc-rig full showcase demo" width="800">
</p>
</details>

### How you like to work: Tiers

Your tier is the primary axis. It determines agents, commands, hooks, plugins and features.

| Tier | Best for | What you get |
|------|----------|-------------|
| **quick** | Side projects, prototypes, scripts | 3 agents, 6 commands. Minimal ceremony. Just code fast. |
| **standard** | Most projects, teams, day-to-day | 5 agents, 9 commands. Memory, safety hooks, code review. |
| **rigorous** | Critical systems, compliance, teams | 10 agents, 15 commands. Spec workflow, security auditor, worktrees. |

The three tiers are depth settings on one spine. They define how many agents ship, what hooks fire and which safety nets are active.

Legacy workflow names still work on the CLI for backward compatibility: `--workflow speedrun` resolves to `quick`, `--workflow verify-heavy` resolves to `rigorous` and so on. They map to a tier; there is no separate pack to choose.

### What you're building: Stack (optional)

Stack is secondary enrichment. It adds framework-specific tool commands, agent docs, rules and language-specific reviewer agents. The default is Generic (no stack-specific content). This per-stack tailoring is what makes the tuner's gates correct: a FastAPI project gates on `pytest` and `ruff`, Next.js on `vitest` and `tsc`, Rust on `cargo test` and `clippy`.

| Template | Stack | Highlights |
|----------|-------|-----------|
| `generic` | No specific stack | Just the workflow. No framework assumptions. |
| `fastapi` | Python + FastAPI | Async patterns, Pydantic, pytest, ruff |
| `django` | Python + Django | Fat models, ORM patterns, manage.py test |
| `flask` | Python + Flask | Blueprints, extensions, pytest, ruff |
| `nextjs` | TypeScript + Next.js | App Router, RSC patterns, Tailwind |
| `express` | TypeScript + Express | Middleware patterns, Router, Jest, ESLint |
| `gin` | Go + Gin | Handler, Service, Repository, golangci-lint |
| `echo` | Go + Echo | Echo conventions, go test |
| `go-std` | Go (stdlib) | Idiomatic Go, no framework, go test, golangci-lint |
| `rust-cli` | Rust + Clap | CLI patterns, cargo test, clippy |
| `rust-web` | Rust + Axum | Async extractors, tower middleware, cargo test |
| `rails` | Ruby + Rails | MVC, ActiveRecord, minitest, rubocop |
| `spring` | Java + Spring Boot | DI, JPA, JUnit 5, Checkstyle/Spotless |
| `dotnet` | .NET + ASP.NET Core | DI, EF Core, xUnit, dotnet format |
| `laravel` | PHP + Laravel | MVC, Eloquent, Artisan, PHPUnit, PHP-CS-Fixer |
| `phoenix` | Elixir + Phoenix | LiveView, Ecto, ExUnit, Credo |

### Add-ons

Some tiers include compound features that span multiple Claude Code primitives:

**Spec Workflow** (rigorous tier). Plan-first development: `/spec-create` and `/spec-execute` commands, `pm-spec` and `implementer` agents, `specs/TEMPLATE.md` starter file. Based on [Pimzino's spec workflow](https://github.com/Pimzino/claude-code-spec-workflow).

**GTD System** (opt-in feature). Getting Things Done for Claude Code: `/gtd-capture`, `/gtd-process`, `/daily-plan` commands and pre-created task files. Based on [adagradschool's cc-gtd](https://github.com/adagradschool/cc-gtd).

**Worktrees** (standard + rigorous tiers). Parallel development using Claude Code's native git worktree support: `parallel-worker` agent and `/worktree` command. For batch orchestration, `cc-rig worktree spawn` launches multiple Claude sessions in isolated worktrees simultaneously.

### Mix and match

```bash
# Rigorous tier, no specific stack
cc-rig init --workflow rigorous

# FastAPI with the standard tier
cc-rig init --template fastapi --workflow standard

# Go microservice, rigorous tier
cc-rig init --template gin --workflow rigorous
```

---

## What Gets Generated

cc-rig generates **native Claude Code files**, the same formats from the [official docs](https://docs.anthropic.com/en/docs/claude-code). Everything is editable, nothing is proprietary. For the complete reference, see [docs/generated-output.md](docs/generated-output.md).

### CLAUDE.md

Targets under 100 lines, leaned to the evidence: essential tooling (build, test, lint commands) and critical patterns only, no README duplication. Static content first, dynamic content last, so only the tail breaks cache. Includes project identity, stack, tool commands, guardrails (including cache-specific rules), compaction survival instructions and `@import` references to deeper docs. A companion `CLAUDE.local.md` is generated for personal preferences (not git-tracked).

### Agents

Your tier and stack together determine which agents ship. quick gets 3. rigorous gets the full set, including an architect and security auditor on Opus with `effort: high` and a parallel worker that runs in isolated worktrees. Each agent gets its own system prompt, model assignment and tool restrictions in YAML frontmatter.

| Agent | Role | Model | Advanced fields |
|-------|------|-------|-----------------|
| `code-reviewer` | 6-aspect code review | Sonnet | `memory: project` |
| `architect` | System design, ADRs | Opus | `memory: project`, `effort: high` |
| `explorer` | Fast codebase scanning | Haiku | `permissionMode: plan`, `maxTurns: 15` |
| `security-auditor` | OWASP-aware security review | Opus | `memory: project`, `effort: high` |
| `parallel-worker` | Background work in isolated git worktrees | Sonnet | `background: true`, `isolation: worktree` |
| `python-reviewer` | Python-specific code review | Sonnet | auto-added for Python templates |

Plus `pr-reviewer`, `pm-spec`, `test-writer`, `refactorer`, `implementer`, `doc-writer`, `techdebt-hunter`, `db-reader`, `build-fixer`, `e2e-runner` and language-specific reviewers for Go, Rust and Java. [See all agents](docs/generated-output.md#agents).

### Slash Commands

Workflows you trigger with `/` in Claude Code. Your tier determines the set.

| Command | What It Does |
|---------|-------------|
| `/fix-issue` | Reproduce, diagnose, fix, test, commit |
| `/plan` | Architecture-first planning with checkpoints |
| `/review` | Multi-dimensional code review via agent |
| `/spec-create` | Create implementation spec from requirements |
| `/worktree` | Spawn a parallel worker in an isolated git worktree |
| `/remember` | Save learnings to persistent memory |

Plus `/test`, `/research`, `/assumptions`, `/learn`, `/refactor`, `/optimize`, `/techdebt`, `/spec-execute`, `/daily-plan`, `/gtd-capture`, `/gtd-process`, `/security`, `/document`. [See all commands](docs/generated-output.md#slash-commands).

### Hooks

Shell scripts on Claude Code lifecycle events, configured in `settings.json`.

| Event | What Fires | Why |
|-------|-----------|-----|
| **PostToolUse** (Write) | Auto-format (prettier/ruff/gofmt) | Instant cleanup, <1s |
| **PreToolUse** (Bash) | Lint + typecheck on git commit | Quality gate before commits |
| **PreToolUse** (Write/Bash) | Block `rm -rf /`, pushes to main, `.env` writes | Safety guards |
| **PreCompact** | Output project essentials before context compaction | Survive compaction (harness) |
| **Stop** | Save learnings to memory, show session cost + cache stats | Preserve context, cost awareness |

[See all hooks](docs/generated-output.md#hooks).

### Skills

cc-rig downloads skills from the original community repos at init time and does not bundle or redistribute them. Your tier determines the base skills (0 for quick, up to 14 for rigorous). Your stack adds framework-matched content: Django projects get Django ORM and testing patterns from [everything-claude-code](https://github.com/affaan-m/everything-claude-code), Go projects get static analysis, Rust projects get ownership and lifetime patterns.

**Starter set** (auto-installed at `init`):
- **Framework-matched**: Python projects get `modern-python` and `property-based-testing`, Next.js gets `vercel-react-best-practices` and `next-best-practices`, Go/Rust get `static-analysis`
- **Cross-cutting**: code review, security basics, TDD, debugging. Scaled by tier
- **`project-patterns`** stub for your team's custom conventions

**Optional skill packs** (select during wizard or add later):

| Pack | What it adds | Source repos |
|------|-------------|--------------|
| Security Deep Dive | supply chain auditing, variant analysis, dangerous API detection | trailofbits/skills |
| DevOps & IaC | Terraform, Kubernetes, monitoring, GitOps | hashicorp, ahmedasmar |
| Web Quality | Core Web Vitals, accessibility, SEO, performance | addyosmani |
| Code Quality | 20 quality dimensions, anti-gaming scoring, scan/plan/fix loop | peteromallet/desloppify |
| Database Pro | migration patterns, query optimization, multi-DB support | multiple |
| ECC SDLC | Python patterns, testing, Django/Spring/Laravel/Go/Rust best practices | affaan-m/everything-claude-code |

The 64-skill catalog spans 14 source repos. Browse the broader ecosystem: [skills.sh](https://skills.sh/) · [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) · [skillsmp.com](https://skillsmp.com/).

### Plugins

cc-rig curates 87 official Anthropic marketplace plugins and writes them into `settings.json` as `enabledPlugins`. Your language gets its LSP plugin, your template gets relevant integrations (Next.js gets Playwright + Stripe, Django gets Redis, Spring gets AWS), your tier gets workflow plugins. Plugins are self-contained: no manual MCP setup or binary downloads.

| Category | Count | Examples |
|----------|-------|---------|
| **LSP** | 15 | pyright-lsp, typescript-lsp, gopls-lsp, rust-analyzer-lsp, ruby-lsp, elixir-ls |
| **Integration** | 38 | github, vercel, supabase, stripe, aws, docker, redis, datadog, terraform |
| **Workflow** | 20 | commit-commands, code-review, test-runner, doc-generator, api-design, perf-profiler |
| **Style** | 5 | concise-output-style, mentor-output-style, explanatory-output-style |
| **Utility** | 8 | hookify, config-doctor, context-optimizer |
| **Autonomy** | 1 | ralph-loop (official Anthropic autonomous iteration loop) |

### Memory, permissions, MCP, agent docs

cc-rig generates a **team memory layer** (`memory/`): git-tracked files for decisions, patterns, gotchas, people and session logs. A Stop hook saves learnings before sessions end; a PreCompact hook does the same before context compaction. Memory loads on demand via the Read tool and stays out of CLAUDE.md, so the cached prefix stays stable across sessions.

**Permissions** are configured in `settings.json` with sensible allow/deny defaults. Safety hooks block `.env` edits, pushes to main and destructive `rm` commands.

**MCP servers** are configured in `.mcp.json` per template (PostgreSQL, Playwright). GitHub is an official plugin, so no MCP setup is needed.

**Agent docs** in `agent_docs/` provide framework-specific reference (architecture, conventions, testing, deployment, cache-friendly workflow) loaded via `@import` syntax.

**GitHub Actions**. The `github_actions` feature generates `.github/workflows/claude.yml` using [anthropics/claude-code-action@v1](https://github.com/anthropics/claude-code-action). Claude reviews every PR and responds to `@claude` mentions. The rigorous tier adds a second security-review job. Enabled by default for standard and rigorous tiers.

[Full details for all of the above](docs/generated-output.md#memory).

---

## Keep it aligned

`cc-rig tune` is the headline return surface. A few more subcommands keep a project aligned as you work and as Claude Code moves week to week.

```bash
cc-rig savings          # cache hit rate and spend over time (from your logs)
cc-rig audit            # discipline read of recent sessions vs your tier
cc-rig drift            # what diverged: edited files, config, CC version pin
cc-rig refresh <area>   # re-run one generator with a diff preview, write on confirm
cc-rig retro            # weekly view: savings + audit + drift, one suggestion
```

- `savings` reads your local Claude Code session logs and reports what the prompt cache saved versus uncached input, a 4-week trend and the top cache breakers. It is the longitudinal companion to `tune`'s point-in-time score. Nothing leaves your machine; state lives at `~/.cc-rig/baseline.json`.
- `audit` scores observable signals from your session logs (cache hygiene, model pinning, cache read ratio, session shape) and gives a tier-fit verdict.
- `drift` compares the project against a fresh generation and against the pinned Claude Code version. Read-only.
- `refresh <area>` regenerates one area (`agents`, `commands`, `skills`, `rules`, `settings` or `all`) and shows a unified diff before it writes. Overwritten files are backed up.
- `retro` rolls the week into one summary, with a footer in the generated CLAUDE.md and a session-start nudge pointing you back to it.

Project state for the loop lives at `.claude/cc-rig-state.json` (git-friendly, no raw paths or user content).

---

## Going Deeper

### Expert mode

Full control over agents, commands, hooks, skills, MCP servers, permissions, features and custom CLAUDE.md rules. Starts from your tier's defaults:

```bash
cc-rig init --expert
```

### Autonomous mode

Claude works through a task list while you're away.

<details>
<summary>Harness options: from scaffold to autonomous loops</summary>

<p align="center">
  <img src="https://raw.githubusercontent.com/runtimenoteslabs/cc-rig/main/assets/demo-3-harness.gif" alt="cc-rig harness demo" width="800">
</p>
</details>

```bash
cc-rig harness init --lite        # Task tracking + budget + context survival hook
cc-rig harness init               # + enforcement gates + session telemetry + init-sh.sh
cc-rig harness init --autonomy    # + loop script, 5-step PROMPT.md, progress ledger
```

Each level builds on the previous. The wizard's "Custom" option lets you enable any combination of task tracking, budget awareness, verification gates, context awareness, session telemetry and autonomy loop independently. A 6th option enables the **ralph-loop plugin**, Anthropic's official autonomous iteration loop.

The autonomy level generates `loop.sh` and `PROMPT.md`, a bash loop that feeds tasks to Claude one at a time with fresh context. Based on the [Ralph Wiggum technique](https://github.com/ghuntley/how-to-ralph-wiggum) by Geoffrey Huntley. Safety rails included: iteration limits, budget enforcement, checkpoint auto-commits, stuck detection and a cost summary on exit.

**Warning**: `loop.sh` uses `--dangerously-skip-permissions`. Run inside a Docker container or sandboxed environment. [Full autonomous mode details](docs/generated-output.md#autonomous-mode-details).

### For teams

Every `cc-rig init` saves a config file. Commit it and teammates get the same setup:

```bash
cc-rig init --config .cc-rig.json    # Same agents, hooks, permissions
```

Export portable configs, lock configs to prevent modification, compare configs across projects. [Team config commands](docs/generated-output.md#for-teams).

### Health check and cleanup

```bash
cc-rig doctor                 # Check project health (files, hooks, permissions, cache, manifest)
cc-rig doctor --fix           # Auto-fix safe issues
cc-rig clean                  # Remove generated files using the manifest
```

Run `cc-rig --help` or see the [full CLI reference](docs/generated-output.md#cli-reference).

### Saving tokens (the deep guide)

`cc-rig tune` flags what breaks your cache and `cc-rig savings` tracks your hit rate over time. Under the hood, the generated config is built to keep the prompt cache warm:

- **CLAUDE.md is static-first.** Project identity, commands and guardrails at the top (never change). Current context at the bottom (changes every session). Only the tail breaks cache.
- **Cache guardrails** tell Claude not to edit CLAUDE.md mid-session, not to toggle hooks/plugins, not to switch models (use subagents instead) and to load memory via the Read tool.
- **Compaction survival.** A dedicated CLAUDE.md section tells Claude what to preserve when the context window is compacted. The harness adds a PreCompact hook that outputs project essentials before the wipe.
- **JSONL deduplication.** Extended thinking can log duplicate PRELIM entries to your session JSONL. The telemetry hooks deduplicate before accounting, so cost estimates are accurate.

[Full guide: saving tokens with cc-rig](docs/saving-tokens.md)

---

## FAQ

<details>
<summary><strong>How is this different from writing CLAUDE.md by hand?</strong></summary>

You could write CLAUDE.md yourself. But a fully configured project also needs `settings.json` with hooks and permissions, agent markdown files with YAML frontmatter and tool restrictions, slash command files, skills, MCP config, memory files and agent docs, all with correct cross-references. cc-rig generates everything in seconds with content specific to your framework, and `cc-rig tune` keeps it correct over time as Claude Code ships weekly.
</details>

<details>
<summary><strong>What does `cc-rig tune` need to run?</strong></summary>

Just your project directory. It reads the on-disk config (CLAUDE.md, settings, hooks, memory). For the dollar figures it also reads your local Claude Code session logs at `~/.claude/projects/`. With no session history it still scores and ranks the structural findings; the dollar estimates are simply left out when there is nothing to measure. Nothing leaves your machine.
</details>

<details>
<summary><strong>Does this work with existing projects?</strong></summary>

Yes. `cc-rig init --migrate` scans your repo, detects your stack and proposes what to add. It only writes new files and won't touch anything that already exists.
</details>

<details>
<summary><strong>Can I edit the generated files?</strong></summary>

Yes. Everything is plain text. Edit whatever you want. cc-rig won't overwrite your changes. Generate once, own forever. To re-run the wizard with your existing choices pre-filled, use `cc-rig config update`. For personal preferences, use `CLAUDE.local.md` (not git-tracked).
</details>

<details>
<summary><strong>What about Claude Code plugins and skills?</strong></summary>

cc-rig handles both. For skills, it downloads from 14 community repos at init time, with optional packs for deeper coverage. For plugins, it curates 87 official marketplace plugins across 6 categories (LSP, integration, workflow, style, autonomy, utility) and writes <code>enabledPlugins</code> into <code>settings.json</code> with defaults resolved by language, template and tier. You can install any additional skill from <a href="https://skills.sh/">skills.sh</a>, <a href="https://github.com/ComposioHQ/awesome-claude-skills">awesome-claude-skills</a> or any GitHub repo.
</details>

<details>
<summary><strong>Does this cost anything?</strong></summary>

cc-rig is free and open source. Claude Code itself requires an <a href="https://www.anthropic.com/pricing">Anthropic plan</a>. cc-rig doesn't promise a lower bill: Claude Code caches prompts on its own (cached tokens cost 5-10% of uncached, depending on the model). What it does promise is a config that is lean, guarded and verified, and a score that tells you when that stops being true.
</details>

<details>
<summary><strong>Install fails with "no matching distribution found"</strong></summary>

cc-rig requires Python 3.9+. Some Linux distros (e.g. Ubuntu 20.04) ship Python 3.8. Check with <code>python3 --version</code>. If you're on 3.8, install a newer Python:

```bash
sudo apt install python3.9 python3.9-venv python3.9-distutils
python3.9 -m venv .venv && source .venv/bin/activate
pip install cc-rig
```
</details>

---

## Community & Ecosystem

cc-rig's skills are downloaded at `init` time from the original repos. cc-rig does not bundle or redistribute them. Key sources:

- [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) - Framework-specific skills: Python, Django, Spring Boot, Laravel, Go, Rust + SDLC (MIT)
- [obra/superpowers](https://github.com/obra/superpowers) - SDLC workflow skills (MIT)
- [trailofbits/skills](https://github.com/trailofbits/skills) - security + modern dev skills (CC-BY-SA-4.0)
- [anthropics/skills](https://github.com/anthropics/skills) - official Anthropic skills (Apache 2.0)

Plus more repos from HashiCorp, Vercel, Supabase, PlanetScale, Addy Osmani and others. [See all source repos](docs/generated-output.md#source-repos). The broader ecosystem: [skills.sh](https://skills.sh/) · [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) · [skillsmp.com](https://skillsmp.com/).

cc-rig's design is informed by [Boris Cherny's workflow principles](https://x.com/bcherny/status/2007179832300581177), prompt-caching lessons from the Claude Code team and the [Ralph Wiggum technique](https://github.com/ghuntley/how-to-ralph-wiggum) by Geoffrey Huntley. [Full research & inspiration list](docs/generated-output.md#research--inspiration).

---

## Contributing

PRs welcome, especially new templates, new tier presets, community skill integrations and bug fixes. Please open an issue first for large changes.

```bash
git clone https://github.com/runtimenoteslabs/cc-rig.git
cd cc-rig
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/
ruff check cc_rig/
```

`pytest` and `ruff` are dev-only.

---

<p align="center">
  <strong>Ready to try it?</strong><br>
  <code>uvx cc-rig init</code> &nbsp;then&nbsp; <code>cc-rig tune</code><br><br>
  If cc-rig helped, <a href="https://github.com/runtimenoteslabs/cc-rig">star the repo</a>.
</p>

---

## License

MIT
