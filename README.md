<p align="center">
  <img alt="cc-rig" src="https://raw.githubusercontent.com/runtimenoteslabs/cc-rig/main/assets/cc-rig-logo.png" width="200">
</p>

<h3 align="center">Set up Claude Code the right way - in under a minute.</h3>

<p align="center">
  <a href="#getting-started">Getting Started</a> ·
  <a href="#what-gets-generated">What Gets Generated</a> ·
  <a href="#define-your-stack-and-process">Stack & Process</a> ·
  <a href="#for-teams">For Teams</a> ·
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

## What Gets Generated

cc-rig generates **native Claude Code files**, the same formats from the [official docs](https://docs.anthropic.com/en/docs/claude-code). Nothing proprietary. Delete cc-rig tomorrow and everything keeps working.

```
your-project/
├── CLAUDE.md                       # Project rules Claude follows
├── CLAUDE.local.md                 # Personal preferences (not git-tracked)
├── .mcp.json                       # MCP server integrations
├── .claude/
│   ├── settings.json               # Permissions, hooks, safety guards
│   ├── cc-rig-init.log             # Generation log (what was created + validation)
│   ├── agents/                     # Specialized agents for different tasks
│   ├── commands/                   # Slash commands you trigger with /
│   ├── hooks/                      # Auto-format, lint, safety blocks
│   └── skills/                     # Community skills auto-installed from 17 repos
├── agent_docs/                     # Framework-specific guides for Claude
└── memory/                         # Git-tracked team knowledge across sessions
```

Everything is tracked in a manifest, so `cc-rig clean` removes exactly what was generated. Nothing more.

### CLAUDE.md

Targets under 100 lines. Static content first, dynamic content last. Claude Code's prompt cache is prefix-matched, so every wasted token costs money on every API call.

Includes project identity, stack, tool commands, guardrails, framework-specific rules and `@import` references to deeper docs (auto-loaded by Claude Code). Not a wall of text. A tight brief that Claude actually reads.

A companion `CLAUDE.local.md` is generated for personal preferences (not git-tracked). Use it for per-developer customization without affecting the shared config.

### Agents

Isolated Claude instances in `.claude/agents/`, each with its own system prompt, model assignment and tool restrictions in YAML frontmatter. cc-rig emits up to 12 of Claude Code's 14 supported frontmatter fields. Beyond the basics (name, description, model, tools), agents get optional fields like `effort`, `skills`, `background`, `isolation`, `permissionMode`, `maxTurns` and `memory` where appropriate. This means generated agents work out of the box with Claude Code's parallel execution features like `/simplify` and `/batch`.

| Agent | Role | Model | Advanced fields |
|-------|------|-------|-----------------|
| `code-reviewer` | 6-aspect code review | Sonnet | `memory: project` |
| `architect` | System design, ADRs | Opus* | `memory: project`, `effort: high` |
| `test-writer` | Test generation with coverage awareness | Sonnet | - |
| `explorer` | Fast codebase scanning | Haiku | `permissionMode: plan`, `maxTurns: 15` |
| `refactorer` | Safe refactoring with test verification | Sonnet | - |
| `pr-reviewer` | Pull request review | Opus* | `effort: high` |
| `security-auditor` | OWASP-aware security review | Opus* | `memory: project`, `effort: high` |
| `implementer` | Feature implementation from specs | Sonnet | - |
| `doc-writer` | Documentation generation | Sonnet | - |
| `pm-spec` | Specification creation from requirements | Opus* | `effort: high` |
| `techdebt-hunter` | Technical debt identification | Sonnet | - |
| `db-reader` | Database schema and query analysis | Sonnet | - |
| `parallel-worker` | Background work in isolated git worktrees | Sonnet | `background: true`, `isolation: worktree` |
| `python-reviewer` | Python-specific code review | Sonnet | auto-added for Python templates |
| `go-reviewer` | Go-specific code review | Sonnet | auto-added for Go templates |
| `rust-reviewer` | Rust-specific code review | Sonnet | auto-added for Rust templates |
| `java-reviewer` | Java-specific code review | Sonnet | auto-added for Spring template |
| `build-fixer` | Diagnose and fix build failures | Sonnet | auto-added for all workflows |
| `e2e-runner` | End-to-end test execution | Sonnet | auto-added for web projects |

*\*Opus on Max/Enterprise plans, Sonnet on Pro/Team. cc-rig auto-resolves model assignments based on your Claude plan tier. No manual config needed.*

Your workflow preset determines which agents are included, from 3 for quick prototyping to 19 for full production rigor. Language-specific reviewers are added automatically based on your stack.

### Slash Commands

Workflows you trigger with `/` in Claude Code. Each is a markdown file in `.claude/commands/`.

| Command | What It Does |
|---------|-------------|
| `/fix-issue` | Reproduce → diagnose → fix → test → commit |
| `/plan` | Architecture-first planning with checkpoints |
| `/research` | Explore codebase before implementing changes |
| `/review` | Multi-dimensional code review via agent |
| `/test` | Generate tests with coverage awareness |
| `/assumptions` | Surface Claude's hidden assumptions (with confidence levels) |
| `/remember` | Save learnings to persistent memory |
| `/learn` | Extract patterns from code for future sessions |
| `/refactor` | Safe refactoring with test verification |
| `/optimize` | Performance analysis and optimization |
| `/techdebt` | Identify and address technical debt |
| `/spec-create` | Create implementation spec from requirements |
| `/spec-execute` | Execute a spec with built-in validation |
| `/daily-plan` | Morning planning from active tasks |
| `/worktree` | Spawn a parallel worker in an isolated git worktree |
| `/gtd-capture` | Capture tasks into GTD inbox |
| `/gtd-process` | Process and prioritize captured tasks |
| `/security` | Security review via auditor agent |
| `/document` | Generate documentation |

Up to 19 commands depending on your workflow preset.

### Hooks

Shell scripts on Claude Code lifecycle events, configured in `settings.json`.

| Event | What Fires | Why |
|-------|-----------|-----|
| **PostToolUse** (Write) | Auto-format (prettier/ruff/gofmt) | Instant cleanup, <1s |
| **PreToolUse** (Bash) | Lint + typecheck on git commit | Quality gate before commits |
| **PreToolUse** (Write/Bash) | Block `rm -rf /`, pushes to main, `.env` writes | Safety guards |
| **Stop** | Save learnings to memory, remind about tests, show session cost | Preserve context, cost awareness |
| **PreCompact** | Save context before compaction | Survive context loss |
| **SessionStart** | Load project context and active tasks | Continuity |
| **SessionStart** | Print open/done task counts (harness B1+) | Quick orientation |
| **PreToolUse** (Bash) | Lint gate on `git commit` (harness B2+) | Structural enforcement |

Up to 14 hooks from your workflow preset, plus up to 3 more from the harness level.

### Skills

Auto-invoked behaviors in `.claude/skills/`. Claude loads them when the task matches. No manual trigger needed.

The Claude Code skill ecosystem is huge. [skills.sh](https://skills.sh/) indexes 73K+, repos like [obra/superpowers](https://github.com/obra/superpowers), [trailofbits/skills](https://github.com/trailofbits/skills) and [anthropics/skills](https://github.com/anthropics/skills) offer high-quality options across every SDLC phase. cc-rig gives you a smart starting set and makes it easy to add more.

**Process skills** (installed per workflow):
- Community workflows install their original skills with full attribution. gstack installs 6 skills from garrytan/gstack, aihero installs 7 from mattpocock/skills, superpowers installs 11 from obra/superpowers, gtd installs planning-with-files from OthmanAdi.
- 78 skills in the catalog from 17 repos.

**Starter set** (auto-installed at `init`):
- **Framework-matched**: Python projects get `modern-python` and `property-based-testing`, Next.js gets `vercel-react-best-practices` and `next-best-practices`, Go/Rust get `static-analysis`
- **Cross-cutting**: code review, security basics, TDD, debugging. Scaled by workflow level (0 for speedrun, up to 14 for superpowers)
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

Add skills anytime, from cc-rig or any source:

```bash
cc-rig skills list                    # Show what's installed
cc-rig skills catalog                 # Browse available packs and skills
cc-rig skills add <name>              # Install from catalog
cc-rig skills remove <name>           # Remove a skill
npx skills add <repo> --skill <name>  # Install any skill from any repo
```

Browse the full ecosystem: [skills.sh](https://skills.sh/) · [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) · [skillsmp.com](https://skillsmp.com/)

### Plugins

cc-rig also curates 47 official Anthropic marketplace plugins and writes them into `settings.json` as `enabledPlugins`. Plugins are self-contained extensions that Claude Code installs and manages natively. No manual MCP setup or binary downloads.

Six categories:

| Category | Count | Examples |
|----------|-------|---------|
| **LSP** | 12 | pyright-lsp, typescript-lsp, gopls-lsp, rust-analyzer-lsp, jdtls-lsp, ruby-lsp, kotlin-lsp, swift-lsp |
| **Integration** | 18 | github, vercel, supabase, sentry, slack, linear, notion, firebase, playwright, greptile |
| **Workflow** | 13 | commit-commands, code-review, code-simplifier, frontend-design, agent-sdk-dev, mcp-server-dev |
| **Style** | 2 | explanatory-output-style, learning-output-style |
| **Autonomy** | 1 | ralph-loop (official Anthropic autonomous iteration loop) |
| **Utility** | 1 | hookify (visual hook builder) |

Smart defaults resolve plugins by language (LSP), template (integrations) and workflow (workflow plugins). The github plugin replaces the GitHub MCP server: self-contained, auto-start, no token config needed. Expert mode offers a multi-select from the full catalog.

### Memory

Two complementary memory systems:

- **Auto-memory** (`~/.claude/projects/`): personal, per-machine notes managed automatically by Claude Code. Always on. Use for personal preferences and local context.
- **Team memory** (`memory/`): git-tracked shared knowledge that travels with the repo. Use for decisions, patterns, gotchas and conventions that every contributor should know.

cc-rig generates the team memory layer:

| File | Purpose |
|------|---------|
| `decisions.md` | Architectural decisions with rationale |
| `patterns.md` | Discovered code patterns and conventions |
| `gotchas.md` | Known issues, things that didn't work |
| `people.md` | Team ownership and responsibilities |
| `session-log.md` | Brief per-session progress log |

A `Stop` hook prompts Claude to save team-relevant learnings before ending. A `PreCompact` hook does the same before context compaction wipes working memory. The `/remember` command routes personal notes to auto-memory and team knowledge to `memory/` files.

Team memory files are **not** baked into CLAUDE.md. They load via Read tool on demand. This keeps the cached prompt prefix stable across sessions.

### Permissions & Safety

`settings.json` with sensible defaults:

```json
{
  "permissions": {
    "allow": [
      "Read", "Glob", "Grep", "Edit", "Write",
      "NotebookEdit", "Bash", "WebSearch", "WebFetch", "Task"
    ],
    "deny": [
      "Bash(rm -rf /)",
      "Bash(rm -rf ~)"
    ]
  }
}
```

Safety hooks handle the rest by blocking `.env` edits, pushes to main and destructive `rm` commands with `exit 2`.

### MCP Servers

`.mcp.json` at the project root, configured for your stack. Available integrations:

**Auto-configured** (selected by template): PostgreSQL · Playwright

**Available** (add via expert mode): Slack · Linear · Sentry · Filesystem

> **Note**: GitHub is now an official plugin (self-contained, auto-start) rather than an MCP server. It is enabled by default via `enabledPlugins` in `settings.json` and no longer requires manual token configuration in `.mcp.json`.

### Agent Docs

Framework-specific reference in `agent_docs/`. Real content, not placeholder text:

- **architecture.md** - e.g., Next.js App Router with RSC/Client component boundaries
- **conventions.md** - naming, file structure, import ordering and error handling
- **testing.md** - test strategy, fixtures, mocking and coverage expectations
- **deployment.md** - deployment workflow and infrastructure patterns for your stack
- **cache-friendly-workflow.md** - practices for maximizing prompt cache hit rates

CLAUDE.md references these via `@import` syntax, so Claude Code auto-loads them without Read tool calls. They're still outside the cached prefix to keep token costs low.

---

## Define Your Stack and Process

cc-rig is **workflow-first**. You pick how you like to work, then optionally pick your stack. Any combination works.

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

Stack is secondary enrichment. It adds framework-specific tool commands, agent docs, and rules. The default is Generic (no stack-specific content).

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

## For Teams

### Save and share your config

Every `cc-rig init` saves a config file to your project. Commit it and teammates get the same setup:

```bash
# Teammate clones the repo, then:
cc-rig init --config .cc-rig.json
```

Same agents, same hooks, same permissions. Only project name and output directory change.

### Export a portable config

Strip machine-specific paths for clean sharing:

```bash
cc-rig config save --export team.json --portable
```

### Lock a config

Prevent modifications via expert mode. Teammates can still add custom CLAUDE.md rules (always additive), but can't change agents, hooks or commands:

```bash
cc-rig config lock my-app
```

### Browse and compare

```bash
cc-rig config list              # See all saved configs
cc-rig config inspect my-setup  # View config details
cc-rig config diff my-setup     # Diff against current project
```

---

## Going Deeper

### Expert mode

Full control over everything: agents, commands, hooks, skills, MCP servers, permissions, features and custom CLAUDE.md rules. Starts from your workflow's defaults:

```bash
cc-rig init --expert
```

### Autonomous mode

Claude works through a task list while you're away. Add a harness to any cc-rig project:

<details>
<summary>Harness options: from scaffold to autonomous loops</summary>

<p align="center">
  <img src="https://raw.githubusercontent.com/runtimenoteslabs/cc-rig/main/assets/demo-3-harness.gif" alt="cc-rig harness showdown demo" width="800">
</p>
</details>

```bash
cc-rig harness init --lite        # Task tracking + session-start summary
cc-rig harness init               # + enforcement gates (lint blocks commits) + init-sh.sh
cc-rig harness init --autonomy    # + loop script, 5-step PROMPT.md, progress ledger
```

Each level builds on the previous. Or pick individual features: the wizard's "Custom" option lets you enable any combination of task tracking, budget awareness, verification gates and autonomy loop independently. A 6th option enables the **ralph-loop plugin**, Anthropic's official autonomous iteration loop plugin, as an alternative to cc-rig's generated `loop.sh`.

The standard level generates `init-sh.sh` (wraps your test/lint/format commands) and a commit-gate hook that structurally blocks commits when lint fails. The autonomy level generates `loop.sh` and `PROMPT.md` (5-step workflow: assess, advance, tidy, verify, record), an external bash loop that feeds tasks to Claude one at a time, each with fresh context. Based on the [Ralph Wiggum technique](https://github.com/ghuntley/how-to-ralph-wiggum) by Geoffrey Huntley.

```bash
./loop.sh           # Run the autonomy loop (default: 20 iterations max)
./loop.sh 50        # Override max iterations
```

**Warning**: `loop.sh` uses `--dangerously-skip-permissions`. Run inside a Docker container or sandboxed environment. See [Claude Code security docs](https://docs.anthropic.com/en/docs/claude-code/security).

Safety rails included: iteration limits, budget enforcement (stops the loop when token budget exceeded, warns at configurable threshold), checkpoint auto-commits (when Claude doesn't commit, the loop does), stuck detection, entropy management (tidy between iterations), per-iteration cost tracking in the progress ledger and a cost summary on exit (Ctrl+C, budget exceeded or completion).

The `budget-reminder` Stop hook shows actual session token usage and estimated cost (parsed from Claude Code's JSONL session logs) every time a session ends. Works at all harness levels (B1+), degrades gracefully when python3 is unavailable.

### Health check and cleanup

Validate your configuration after use. Checks file integrity, hook permissions, memory files and manifest consistency:

```bash
cc-rig doctor                 # Check project health
cc-rig doctor --fix           # Auto-fix safe issues (permissions, missing files)
```

Remove everything cc-rig generated, using the manifest. Only touches what cc-rig created:

```bash
cc-rig clean
```

---

## CLI Reference

```
cc-rig init [options]              Set up a new project
  --template <name>                Template preset (fastapi, nextjs, etc.)
  --workflow <name>                Workflow preset (standard, speedrun, etc.)
  --name <name>                    Project name
  -o, --output <dir>               Output directory
  --in-place                       Write to current directory
  --quick                          Quick picker (numbered lists)
  --expert                         Expert mode (full control)
  --migrate                        Detect and set up existing project
  --config <path>                  Load a saved config

cc-rig preset list [--templates|--workflows]
cc-rig preset inspect <name>       View preset details
cc-rig preset create <name>        Create preset from project config
cc-rig preset install <path>       Install a local preset file

cc-rig config save|load|list|inspect|diff|lock|unlock
cc-rig config update [-d DIR] [--quick|--expert]  Re-run wizard on existing config

cc-rig harness init [--lite|--standard|--autonomy] [-d DIR]
cc-rig harness status [--dir DIR]  Show current harness level and progress

cc-rig skills list [-d DIR]        Show installed skills
cc-rig skills catalog              Browse all available skills
cc-rig skills add <name> [-d DIR]  Install a skill from the catalog
cc-rig skills remove <name> [-d DIR] Remove an installed skill
cc-rig skills install [-d DIR]     Retry failed downloads from init

cc-rig worktree spawn "task1" "task2" ...  Launch Claude in parallel worktrees
cc-rig worktree list [-d DIR]      Show all worktrees and status
cc-rig worktree status <name>      Detailed status of one worktree
cc-rig worktree pr <name>          Push branch and create PR from worktree
cc-rig worktree cleanup [name] [--all] [--merged] [--force]

cc-rig doctor [--fix] [--check-compat] [-d DIR]  Validate project health
cc-rig clean [--force] [-d DIR]    Remove generated files
```

---

## Workflow Philosophy

cc-rig's defaults encode seven workflow principles distilled from how the Claude Code team builds software, inspired by [Boris Cherny's workflow](https://x.com/bcherny/status/2007179832300581177) (creator of Claude Code):

| Principle | cc-rig Implementation |
|-----------|----------------------|
| **Plan before coding** | `/plan` and `/assumptions` commands, `/research` for codebase exploration, CLAUDE.md workflow guidance |
| **Use subagents for research** | `/research` command, `explorer` agent (Haiku), `parallel-worker` for worktree isolation |
| **Self-improvement loop** | Auto-memory (personal), team memory (`/remember`, `memory-precompact` hook), persistent `memory/` files |
| **Verify before done** | Hooks (format, lint, typecheck), B2+ enforcement gates (lint blocks commits), guardrails in CLAUDE.md |
| **Demand elegance** | `/refactor` command, `refactorer` agent, workflow principles in CLAUDE.md |
| **Fix failures immediately** | B1+ session-start task summary, B2+ commit-gate hook, B3 autonomy loop (stuck detection) |
| **Track work with tasks** | `tasks/todo.md` (B1+), GTD system (inbox/todo/someday), `/daily-plan` |

Each workflow preset dials these principles up or down:

- **speedrun**: Minimal. Just code fast. Verification hooks present but no process enforcement.
- **standard**: Core principles active. Plan, verify, remember, refactor.
- **gstack**: Garry Tan's cognitive gears. Structured plan/review/ship cycle with 6 process skills.
- **aihero**: Matt Pocock's PRD-driven flow. Requirements interview, TDD, architecture.
- **spec-driven**: Plan-first emphasis. Specs before implementation.
- **superpowers**: Full SDLC coverage. 11 process skills from obra/superpowers. Every quality gate active.
- **gtd**: Task management emphasis. Persistent tracking with planning-with-files.

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

cc-rig handles both community skills and official Anthropic plugins. For skills, cc-rig installs a starter set of community skills matched to your framework from 17 repos, with 6 optional packs for deeper coverage. For plugins, cc-rig curates a 47-plugin official marketplace catalog across 6 categories (LSP, integration, workflow, style, autonomy, utility) and writes <code>enabledPlugins</code> into <code>settings.json</code> with smart defaults resolved by language, template and workflow. You can install any additional skill from <a href="https://skills.sh/">skills.sh</a> (73K+), <a href="https://github.com/ComposioHQ/awesome-claude-skills">awesome-claude-skills</a> or any GitHub repo.
</details>

<details>
<summary><strong>What's the autonomous mode?</strong></summary>

A harness that lets Claude work through a task list unattended. It uses structural enforcement: hooks that block commits when lint fails, a utility script (`init-sh.sh`) wrapping your test/lint/format commands, iteration limits, budget enforcement with cost tracking, checkpoint auto-commits, stuck detection and an emergency stop. On exit you get a cost summary showing total tokens and estimated spend. Set it up, walk away, review the results.
</details>

<details>
<summary><strong>Does this cost anything?</strong></summary>

cc-rig is free and open source. Claude Code itself requires an <a href="https://www.anthropic.com/pricing">Anthropic plan</a>. cc-rig keeps CLAUDE.md lean and prompt cache hit rates high to minimize your token costs.
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

## Community & Inspiration

### Skill Ecosystem

cc-rig's starter set and optional packs draw from these repos. Skills are downloaded at `init` time from the original repos. cc-rig does not bundle or redistribute them.

- [obra/superpowers](https://github.com/obra/superpowers) - 14 SDLC workflow skills (MIT)
- [trailofbits/skills](https://github.com/trailofbits/skills) - 30+ security + modern dev skills (CC-BY-SA-4.0)
- [anthropics/skills](https://github.com/anthropics/skills) - 16 official Anthropic skills (Apache 2.0)
- [addyosmani/web-quality-skills](https://github.com/addyosmani/web-quality-skills) - Core Web Vitals, accessibility, SEO (MIT)
- [hashicorp/agent-skills](https://github.com/hashicorp/agent-skills) - Official Terraform and Packer
- [vercel-labs](https://github.com/vercel-labs/agent-skills) - React, Next.js and design guideline skills (MIT)
- [supabase/agent-skills](https://github.com/supabase/agent-skills) - PostgreSQL best practices (MIT)
- [planetscale/database-skills](https://github.com/planetscale/database-skills) - MySQL, PostgreSQL, Vitess (MIT)
- [akin-ozer/cc-devops-skills](https://github.com/akin-ozer/cc-devops-skills) - 31 CI/CD, IaC and monitoring skills (Apache 2.0)
- [ahmedasmar/devops-claude-skills](https://github.com/ahmedasmar/devops-claude-skills) - Kubernetes, Terraform, monitoring, GitOps (MIT)
- [agamm/claude-code-owasp](https://github.com/agamm/claude-code-owasp) - OWASP Top 10:2025 security (MIT)
- [wshobson/agents](https://github.com/wshobson/agents) - Tailwind CSS design system (MIT)
- [peteromallet/desloppify](https://github.com/peteromallet/desloppify) - Code quality scoring and remediation (MIT)

The broader ecosystem has thousands more. Discover skills at [skills.sh](https://skills.sh/) (73K+), [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills), [skillsmp.com](https://skillsmp.com/) or install from any GitHub repo with `npx skills add`.

### Research & Inspiration

cc-rig's defaults draw from community research on what makes Claude Code work well:

- [Thariq on prompt caching](https://www.techtwitter.com/articles/lessons-from-building-claude-code-prompt-caching-is-everything) - how Claude Code's team optimizes caching (informed cc-rig's cache-aware architecture)
- [Boris Cherny's workflow principles](https://x.com/bcherny/status/2007179832300581177) - seven principles for effective Claude Code usage (creator of Claude Code)
- [What great CLAUDE.md files have in common](https://blog.devgenius.io/what-great-claude-md-files-have-in-common-db482172ad2c) - content patterns
- [HumanLayer's CLAUDE.md guide](https://www.humanlayer.dev/blog/writing-a-good-claude-md) - structure principles
- [Spec workflow](https://github.com/Pimzino/claude-code-spec-workflow) by Pimzino - plan-first development
- [cc-gtd](https://github.com/adagradschool/cc-gtd) by adagradschool - GTD for Claude Code
- [SuperClaude](https://github.com/superclaude/superclaude) - runtime framework, different approach
- [QMD](https://github.com/tobi/qmd) by Tobi Lütke - local doc search
- [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) - community directory
- [Ralph Wiggum technique](https://github.com/ghuntley/how-to-ralph-wiggum) by Geoffrey Huntley - autonomous loop pattern

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
  <a href="https://github.com/runtimenoteslabs/cc-rig">Star the repo</a> if cc-rig saves you setup time.
</p>

---

## License

MIT
