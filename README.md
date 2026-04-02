<p align="center">
  <img alt="cc-rig" src="https://raw.githubusercontent.com/runtimenoteslabs/cc-rig/main/assets/cc-rig-logo.png" width="200">
</p>

<h3 align="center">Set up Claude Code the right way, in under a minute.</h3>

<p align="center">
  <a href="#getting-started">Getting Started</a> ·
  <a href="#how-it-works">How It Works</a> ·
  <a href="#what-gets-generated">What Gets Generated</a> ·
  <a href="#going-deeper">Going Deeper</a> ·
  <a href="#faq">FAQ</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-MIT-f59e0b?style=flat-square" alt="MIT License">
  <a href="https://pypi.org/project/cc-rig/"><img src="https://img.shields.io/pypi/v/cc-rig?style=flat-square&color=22c55e" alt="PyPI"></a>
</p>

---

Most Claude Code projects run on a CLAUDE.md and not much else. The rest of the configuration surface (agents, hooks, skills, plugins, memory, permissions) goes unused because the knowledge to set it up is scattered across docs, blog posts and community repos. The community has built ways to discover what's available. The gap is resolution: figuring out which options matter for your stack and how they should work together.

**cc-rig resolves it.** Tell it what you're building and how you like to work. It writes 30-65 native Claude Code files tuned to your framework. No lock-in. Just files that Claude Code reads on startup.

<p align="center">
  <img src="https://raw.githubusercontent.com/runtimenoteslabs/cc-rig/main/assets/demo-2-guided.gif" alt="cc-rig guided setup demo" width="800">
</p>

### Before and after

A typical Claude Code project:

```
CLAUDE.md
```

After `cc-rig init` (one command, two questions, ~30 seconds):

```
CLAUDE.md                    # Cache-aware, framework-tuned, under 100 lines
CLAUDE.local.md              # Personal preferences (gitignored)
.claude/settings.json        # Permissions, hooks, 47 curated plugins
.claude/agents/              # 3-19 specialized agents with YAML frontmatter
.claude/commands/            # 6-19 slash commands matched to your workflow
.claude/hooks/               # Auto-format, lint gates, safety blocks
.claude/skills/              # Community skills from 17 repos
agent_docs/                  # Framework-specific guides (auto-loaded via @import)
memory/                      # Git-tracked team knowledge across sessions
```

Nothing proprietary. Delete cc-rig tomorrow and everything keeps working.

---

## Install

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

- Works best with Claude Code v2.1.50+. Older versions or missing installs get a warning, but cc-rig generates everything anyway.

---

## Getting Started

### Start a new project

The interactive wizard walks you through it. You get a full-screen TUI with arrow-key navigation, radio buttons and checkboxes.

```bash
cc-rig init
```

Or skip the wizard and specify everything directly:

```bash
cc-rig init --workflow gstack --template fastapi --name my-api
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

## How It Works

cc-rig is **workflow-first**. You pick how you like to work, then optionally pick your stack. The two axes compose independently: any workflow works with any template.

<details>
<summary>Full showcase: 16 templates x 7 workflows x harness levels</summary>

<p align="center">
  <img src="https://raw.githubusercontent.com/runtimenoteslabs/cc-rig/main/assets/demo-4-showcase.gif" alt="cc-rig full showcase demo" width="800">
</p>
</details>

### How you like to work: Workflows

Workflow is the primary axis. It determines your agents, commands, hooks, process skills, and features.

| Workflow | Source | Best for |
|----------|--------|----------|
| **speedrun** | cc-rig | Side projects, prototypes. 3 agents, 6 commands. No memory. Just code fast. |
| **standard** | cc-rig | Most projects. 5 agents, 9 commands. Memory, safety hooks, code review. |
| **gstack** | [garrytan/gstack](https://github.com/garrytan/gstack) | Garry Tan's cognitive gears. Plan, review, ship. 6 process skills installed. |
| **aihero** | [mattpocock/skills](https://github.com/mattpocock/skills) | Matt Pocock's PRD-driven flow. Grill-me, TDD, architecture. 7 process skills. |
| **spec-driven** | cc-rig + community | Teams that plan first. Spec create/execute, PM and implementer agents. |
| **superpowers** | [obra/superpowers](https://github.com/obra/superpowers) | Full SDLC suite. 11 process skills covering planning through branch cleanup. |
| **gtd** | [OthmanAdi](https://github.com/OthmanAdi/planning-with-files) + cc-rig | Persistent task tracking. planning-with-files, daily plans, worktrees. |

Community workflows install their original process skills with full attribution. For example, gstack installs `/plan-ceo-review`, `/plan-eng-review`, `/gstack-review`, `/ship`, `/document-release` directly from garrytan/gstack.

Backward-compatible aliases: `verify-heavy` resolves to `superpowers`, `gtd-lite` resolves to `gtd`.

### What you're building: Stack (optional)

Stack is secondary enrichment. It adds framework-specific tool commands, agent docs, rules, and language-specific reviewer agents. The default is Generic (no stack-specific content).

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

Some workflows include compound features that span multiple Claude Code primitives:

**Spec Workflow** (spec-driven, aihero, superpowers). Plan-first development: `/spec-create` and `/spec-execute` commands, `pm-spec` and `implementer` agents, `specs/TEMPLATE.md` starter file. Based on [Pimzino's spec workflow](https://github.com/Pimzino/claude-code-spec-workflow).

**GTD System** (gtd). Getting Things Done for Claude Code: `/gtd-capture`, `/gtd-process`, `/daily-plan` commands, pre-created `tasks/inbox.md`, `tasks/todo.md` and `tasks/someday.md`. Based on [adagradschool's cc-gtd](https://github.com/adagradschool/cc-gtd).

**Worktrees** (gstack, aihero, spec-driven, superpowers, gtd). Parallel development using Claude Code's native git worktree support: `parallel-worker` agent and `/worktree` command. For batch orchestration, `cc-rig worktree spawn` launches multiple Claude sessions in isolated worktrees simultaneously. Each gets its own branch, runs independently, and can be merged via PR when done.

### Mix and match

```bash
# Just the gstack workflow, no specific stack
cc-rig init --workflow gstack

# FastAPI with superpowers - maximum rigor
cc-rig init --template fastapi --workflow superpowers

# Go microservice with GTD task tracking
cc-rig init --template gin --workflow gtd
```

---

## What Gets Generated

cc-rig generates **native Claude Code files**, the same formats from the [official docs](https://docs.anthropic.com/en/docs/claude-code). Everything is editable, nothing is proprietary. For the complete reference with all tables, see [docs/generated-output.md](docs/generated-output.md).

### CLAUDE.md

Targets under 100 lines. Static content first, dynamic content last. Claude Code's prompt cache is prefix-matched, so every wasted token costs money on every API call. Includes project identity, stack, tool commands, guardrails (including 4 cache-specific rules), compaction survival instructions, framework-specific rules and `@import` references to deeper docs. A companion `CLAUDE.local.md` is generated for personal preferences (not git-tracked).

### Agents

Your workflow and stack together determine which agents ship. Speedrun gets 3. Superpowers gets the full set, including an architect and security auditor on Opus with `effort: high`, and a parallel worker that runs in isolated worktrees. Each agent gets its own system prompt, model assignment, and tool restrictions in YAML frontmatter (up to 12 of 14 supported fields).

| Agent | Role | Model | Advanced fields |
|-------|------|-------|-----------------|
| `code-reviewer` | 6-aspect code review | Sonnet | `memory: project` |
| `architect` | System design, ADRs | Opus* | `memory: project`, `effort: high` |
| `explorer` | Fast codebase scanning | Haiku | `permissionMode: plan`, `maxTurns: 15` |
| `security-auditor` | OWASP-aware security review | Opus* | `memory: project`, `effort: high` |
| `parallel-worker` | Background work in isolated git worktrees | Sonnet | `background: true`, `isolation: worktree` |
| `python-reviewer` | Python-specific code review | Sonnet | auto-added for Python templates |

Plus `pr-reviewer`, `pm-spec`, `test-writer`, `refactorer`, `implementer`, `doc-writer`, `techdebt-hunter`, `db-reader`, `build-fixer`, `e2e-runner` and language-specific reviewers for Go, Rust, and Java. [See all 19 agents](docs/generated-output.md#agents).

### Slash Commands

Workflows you trigger with `/` in Claude Code. Your workflow preset determines the set.

| Command | What It Does |
|---------|-------------|
| `/fix-issue` | Reproduce, diagnose, fix, test, commit |
| `/plan` | Architecture-first planning with checkpoints |
| `/review` | Multi-dimensional code review via agent |
| `/spec-create` | Create implementation spec from requirements |
| `/worktree` | Spawn a parallel worker in an isolated git worktree |
| `/remember` | Save learnings to persistent memory |

Plus `/test`, `/research`, `/assumptions`, `/learn`, `/refactor`, `/optimize`, `/techdebt`, `/spec-execute`, `/daily-plan`, `/gtd-capture`, `/gtd-process`, `/security`, `/document`. [See all 19 commands](docs/generated-output.md#slash-commands).

### Hooks

Shell scripts on Claude Code lifecycle events, configured in `settings.json`.

| Event | What Fires | Why |
|-------|-----------|-----|
| **PostToolUse** (Write) | Auto-format (prettier/ruff/gofmt) | Instant cleanup, <1s |
| **PreToolUse** (Bash) | Lint + typecheck on git commit | Quality gate before commits |
| **PreToolUse** (Write/Bash) | Block `rm -rf /`, pushes to main, `.env` writes | Safety guards |
| **PreCompact** | Output project essentials before context compaction | Survive compaction (B1+ harness) |
| **Stop** | Save learnings to memory, show session cost + cache stats | Preserve context, cost awareness |

Up to 14 hooks from your workflow preset, plus up to 5 more from the harness level. [See all hooks](docs/generated-output.md#hooks).

### Skills

cc-rig downloads skills from the original community repos at init time and does not bundle or redistribute them. Your workflow determines the process skills: gstack installs Garry Tan's 6 skills from [garrytan/gstack](https://github.com/garrytan/gstack), superpowers installs obra's 11 from [obra/superpowers](https://github.com/obra/superpowers). Your stack adds framework-matched content: Django projects get Django ORM and testing patterns from [everything-claude-code](https://github.com/affaan-m/everything-claude-code), Go projects get static analysis, Rust projects get ownership and lifetime patterns.

**Starter set** (auto-installed at `init`):
- **Framework-matched**: Python projects get `modern-python` and `property-based-testing`, Next.js gets `vercel-react-best-practices` and `next-best-practices`, Go/Rust get `static-analysis`
- **Cross-cutting**: code review, security basics, TDD, debugging. Scaled by workflow (0 for speedrun, up to 14 for superpowers)
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

Browse the full ecosystem: [skills.sh](https://skills.sh/) · [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) · [skillsmp.com](https://skillsmp.com/). [Skill CLI commands](docs/generated-output.md#skills).

### Plugins

cc-rig curates 47 official Anthropic marketplace plugins and writes them into `settings.json` as `enabledPlugins`. Your language gets its LSP plugin, your template gets relevant integrations (Next.js gets Playwright, Laravel gets Laravel Boost), your workflow gets workflow plugins. Plugins are self-contained: no manual MCP setup or binary downloads.

| Category | Count | Examples |
|----------|-------|---------|
| **LSP** | 12 | pyright-lsp, typescript-lsp, gopls-lsp, rust-analyzer-lsp, jdtls-lsp, ruby-lsp |
| **Integration** | 18 | github, vercel, supabase, sentry, slack, linear, notion, firebase, playwright |
| **Workflow** | 13 | commit-commands, code-review, code-simplifier, frontend-design, agent-sdk-dev |
| **Style** | 2 | explanatory-output-style, learning-output-style |
| **Autonomy** | 1 | ralph-loop (official Anthropic autonomous iteration loop) |
| **Utility** | 1 | hookify (visual hook builder) |

### Memory, permissions, MCP, agent docs

cc-rig generates a **team memory layer** (`memory/`): 5 git-tracked files for decisions, patterns, gotchas, people and session logs. A Stop hook saves learnings before sessions end, a PreCompact hook does the same before context compaction. Memory loads on demand via Read tool, not baked into CLAUDE.md, keeping the cached prefix stable.

**Context intelligence** (v2.2): Every generated CLAUDE.md includes compaction survival instructions and cache guardrails. The B1+ harness adds a PreCompact hook that outputs project essentials before context compaction and documents 14 cache-break vectors. The B2+ harness adds session telemetry (token usage, cost tracking, cache hit stats) written to `.claude/telemetry.jsonl` on every session end. `cc-rig doctor` checks your CLAUDE.md for cache anti-patterns and parses session JSONL to warn when cache hit ratios drop below 40%.

**Permissions** are configured in `settings.json` with sensible allow/deny defaults. Safety hooks block `.env` edits, pushes to main and destructive `rm` commands.

**MCP servers** are configured in `.mcp.json` per template (PostgreSQL, Playwright). GitHub is now an official plugin, no MCP setup needed.

**Agent docs** in `agent_docs/` provide framework-specific reference (architecture, conventions, testing, deployment, cache-friendly workflow) loaded via `@import` syntax.

[Full details for all of the above](docs/generated-output.md#memory).

---

## Going Deeper

### Expert mode

Full control over agents, commands, hooks, skills, MCP servers, permissions, features and custom CLAUDE.md rules. Starts from your workflow's defaults:

```bash
cc-rig init --expert
```

### Autonomous mode

Claude works through a task list while you're away.

<details>
<summary>Harness options: from scaffold to autonomous loops</summary>

<p align="center">
  <img src="https://raw.githubusercontent.com/runtimenoteslabs/cc-rig/main/assets/demo-3-harness.gif" alt="cc-rig harness showdown demo" width="800">
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

---

## FAQ

<details>
<summary><strong>How is this different from writing CLAUDE.md by hand?</strong></summary>

You could write CLAUDE.md yourself. But a fully configured project also needs `settings.json` with hooks and permissions, agent markdown files with YAML frontmatter and tool restrictions, slash command files, skills, MCP config, memory files and agent docs, all with correct cross-references. cc-rig generates everything in seconds with content specific to your framework.
</details>

<details>
<summary><strong>Does this work with existing projects?</strong></summary>

Yes. `cc-rig init --migrate` scans your repo, detects your stack and proposes what to add. It only writes new files and won't touch anything that already exists.
</details>

<details>
<summary><strong>Can I edit the generated files?</strong></summary>

Yes. Everything is plain text. Edit whatever you want. cc-rig won't overwrite your changes. Generate once, own forever. To re-run the wizard with your existing choices pre-filled, use `cc-rig config update`. It shows what changed and regenerates on confirmation. For personal preferences, use `CLAUDE.local.md` (not git-tracked) to avoid conflicts with team config.
</details>

<details>
<summary><strong>What about Claude Code plugins and skills?</strong></summary>

cc-rig handles both community skills and official Anthropic plugins. For skills, cc-rig downloads from 17 community repos at init time, with 6 optional packs for deeper coverage. For plugins, cc-rig curates 47 official marketplace plugins across 6 categories (LSP, integration, workflow, style, autonomy, utility) and writes <code>enabledPlugins</code> into <code>settings.json</code> with defaults resolved by language, template and workflow. You can install any additional skill from <a href="https://skills.sh/">skills.sh</a>, <a href="https://github.com/ComposioHQ/awesome-claude-skills">awesome-claude-skills</a> or any GitHub repo.
</details>

<details>
<summary><strong>What's the autonomous mode?</strong></summary>

A harness that lets Claude work through a task list unattended. It uses structural enforcement: hooks that block commits when lint fails, a utility script (`init-sh.sh`) wrapping your test/lint/format commands, iteration limits, budget enforcement with cost tracking, checkpoint auto-commits, stuck detection and an emergency stop. On exit you get a cost summary showing total tokens and estimated spend. Set it up, walk away, review the results.
</details>

<details>
<summary><strong>Does this cost anything?</strong></summary>

cc-rig is free and open source. Claude Code itself requires an <a href="https://www.anthropic.com/pricing">Anthropic plan</a>. cc-rig keeps CLAUDE.md lean, generates cache guardrails, and tracks cache hit rates via session telemetry to minimize your token costs. Cached prompt tokens cost 10% of uncached tokens.
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
- [obra/superpowers](https://github.com/obra/superpowers) - 14 SDLC workflow skills (MIT)
- [garrytan/gstack](https://github.com/garrytan/gstack) - 6 cognitive gear skills: plan, review, ship, document (MIT)
- [mattpocock/skills](https://github.com/mattpocock/skills) - 7 PRD-driven flow skills: grill-me, TDD, architecture (MIT)
- [trailofbits/skills](https://github.com/trailofbits/skills) - 30+ security + modern dev skills (CC-BY-SA-4.0)
- [anthropics/skills](https://github.com/anthropics/skills) - 16 official Anthropic skills (Apache 2.0)

Plus 11 more repos from HashiCorp, Vercel, Supabase, PlanetScale, Addy Osmani and others. [See all 17 source repos](docs/generated-output.md#source-repos). The broader ecosystem: [skills.sh](https://skills.sh/) · [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) · [skillsmp.com](https://skillsmp.com/).

cc-rig's design is informed by [Boris Cherny's workflow principles](https://x.com/bcherny/status/2007179832300581177), [Thariq's prompt caching insights](https://www.techtwitter.com/articles/lessons-from-building-claude-code-prompt-caching-is-everything), and the [Ralph Wiggum technique](https://github.com/ghuntley/how-to-ralph-wiggum) by Geoffrey Huntley. [Full research & inspiration list](docs/generated-output.md#research--inspiration).

---

## Contributing

PRs welcome, especially new templates, new workflow presets, community skill integrations and bug fixes. Please open an issue first for large changes.

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
  <code>pip install cc-rig && cc-rig init</code><br><br>
  If cc-rig saves you setup time, <a href="https://github.com/runtimenoteslabs/cc-rig">star the repo</a>.
</p>

---

## License

MIT
