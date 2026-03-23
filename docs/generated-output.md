# Generated Output Reference

> For a quick overview, see the [README](../README.md#what-gets-generated).

cc-rig generates **native Claude Code files**, the same formats from the [official docs](https://docs.anthropic.com/en/docs/claude-code). Nothing proprietary. Delete cc-rig tomorrow and everything keeps working.

```
your-project/
├── CLAUDE.md                       # Project rules Claude follows
├── CLAUDE.local.md                 # Personal preferences (not git-tracked)
├── .mcp.json                       # MCP server integrations
├── .claude/
│   ├── settings.json               # Permissions, hooks, plugins, safety guards
│   ├── cc-rig-init.log             # Generation log (what was created + validation)
│   ├── agents/                     # Specialized agents for different tasks
│   ├── commands/                   # Slash commands you trigger with /
│   ├── hooks/                      # Auto-format, lint, safety blocks
│   └── skills/                     # Community skills from 17 repos
├── agent_docs/                     # Framework-specific guides for Claude
└── memory/                         # Git-tracked team knowledge across sessions
```

Everything is tracked in a manifest, so `cc-rig clean` removes exactly what was generated. Nothing more.

---

## CLAUDE.md

Targets under 100 lines. Static content first, dynamic content last. Claude Code's prompt cache is prefix-matched, so every wasted token costs money on every API call.

Includes project identity, stack, tool commands, guardrails, framework-specific rules and `@import` references to deeper docs (auto-loaded by Claude Code). Not a wall of text. A tight brief that Claude actually reads.

A companion `CLAUDE.local.md` is generated for personal preferences (not git-tracked). Use it for per-developer customization without affecting the shared config.

---

## Agents

Your workflow and stack together determine which agents ship. Speedrun gets 3. Superpowers gets the full set, including an architect and security auditor on Opus with `effort: high`, and a parallel worker that runs in isolated worktrees. Python, Go, Rust, and Java templates add language-specific code reviewers drawn from framework patterns in [everything-claude-code](https://github.com/affaan-m/everything-claude-code).

Each agent gets its own system prompt, model assignment, and tool restrictions in YAML frontmatter. cc-rig emits up to 12 of Claude Code's 14 supported frontmatter fields, including `effort`, `skills`, `background`, `isolation`, `permissionMode`, `maxTurns` and `memory`.

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

---

## Slash Commands

Workflows you trigger with `/` in Claude Code. Each is a markdown file in `.claude/commands/`. Your workflow preset determines the set.

| Command | What It Does |
|---------|-------------|
| `/fix-issue` | Reproduce, diagnose, fix, test, commit |
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

---

## Hooks

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

---

## Skills

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

**Manage skills anytime:**

```bash
cc-rig skills list                    # Show what's installed
cc-rig skills catalog                 # Browse available packs and skills
cc-rig skills add <name>              # Install from catalog
cc-rig skills remove <name>           # Remove a skill
npx skills add <repo> --skill <name>  # Install any skill from any repo
```

Browse the full ecosystem: [skills.sh](https://skills.sh/) · [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) · [skillsmp.com](https://skillsmp.com/)

---

## Plugins

cc-rig curates official Anthropic marketplace plugins and writes them into `settings.json` as `enabledPlugins`. Your language gets its LSP plugin, your template gets relevant integrations (Next.js gets Playwright, Laravel gets Laravel Boost), your workflow gets workflow plugins (spec-driven and superpowers get code-simplifier). Plugins are self-contained extensions that Claude Code installs and manages natively. No manual MCP setup or binary downloads.

| Category | Count | Examples |
|----------|-------|---------|
| **LSP** | 12 | pyright-lsp, typescript-lsp, gopls-lsp, rust-analyzer-lsp, jdtls-lsp, ruby-lsp, kotlin-lsp, swift-lsp |
| **Integration** | 18 | github, vercel, supabase, sentry, slack, linear, notion, firebase, playwright, greptile |
| **Workflow** | 13 | commit-commands, code-review, code-simplifier, frontend-design, agent-sdk-dev, mcp-server-dev |
| **Style** | 2 | explanatory-output-style, learning-output-style |
| **Autonomy** | 1 | ralph-loop (official Anthropic autonomous iteration loop) |
| **Utility** | 1 | hookify (visual hook builder) |

The github plugin replaces the GitHub MCP server: self-contained, auto-start, no token config needed. Expert mode offers a multi-select from the full catalog.

---

## Memory

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

---

## Permissions & Safety

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

---

## MCP Servers

`.mcp.json` at the project root, configured for your stack. Available integrations:

**Auto-configured** (selected by template): PostgreSQL · Playwright

**Available** (add via expert mode): Slack · Linear · Sentry · Filesystem

> **Note**: GitHub is now an official plugin (self-contained, auto-start) rather than an MCP server. It is enabled by default via `enabledPlugins` in `settings.json` and no longer requires manual token configuration in `.mcp.json`.

---

## Agent Docs

Framework-specific reference in `agent_docs/`. Real content, not placeholder text:

- **architecture.md** - e.g., Next.js App Router with RSC/Client component boundaries
- **conventions.md** - naming, file structure, import ordering and error handling
- **testing.md** - test strategy, fixtures, mocking and coverage expectations
- **deployment.md** - deployment workflow and infrastructure patterns for your stack
- **cache-friendly-workflow.md** - practices for maximizing prompt cache hit rates

CLAUDE.md references these via `@import` syntax, so Claude Code auto-loads them without Read tool calls. They're still outside the cached prefix to keep token costs low.

---

## Autonomous Mode (details)

Claude works through a task list while you're away. Add a harness to any cc-rig project:

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

**Safety rails**: iteration limits, budget enforcement (stops the loop when token budget exceeded, warns at configurable threshold), checkpoint auto-commits (when Claude doesn't commit, the loop does), stuck detection, entropy management (tidy between iterations), per-iteration cost tracking in the progress ledger and a cost summary on exit (Ctrl+C, budget exceeded or completion).

The `budget-reminder` Stop hook shows actual session token usage and estimated cost (parsed from Claude Code's JSONL session logs) every time a session ends. Works at all harness levels (B1+), degrades gracefully when python3 is unavailable.

---

## For Teams

Every `cc-rig init` saves a config file to your project. Commit it and teammates get the same setup:

```bash
# Teammate clones the repo, then:
cc-rig init --config .cc-rig.json
```

Same agents, same hooks, same permissions. Only project name and output directory change.

```bash
cc-rig config save --export team.json --portable    # Strip machine-specific paths
cc-rig config lock my-app                           # Prevent wizard modifications
cc-rig config list                                  # See all saved configs
cc-rig config inspect my-setup                      # View config details
cc-rig config diff my-setup                         # Diff against current project
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

## Community & Ecosystem

cc-rig's starter set, process skills, and optional packs draw from these repos. Skills are downloaded at `init` time from the original repos. cc-rig does not bundle or redistribute them.

### Source repos

- [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) - Framework-specific skills: Python, Django, Spring Boot, Laravel, Go, Rust + cross-cutting SDLC (MIT)
- [obra/superpowers](https://github.com/obra/superpowers) - 14 SDLC workflow skills (MIT)
- [garrytan/gstack](https://github.com/garrytan/gstack) - 6 cognitive gear skills: plan, review, ship, document (MIT)
- [mattpocock/skills](https://github.com/mattpocock/skills) - 7 PRD-driven flow skills: grill-me, TDD, architecture (MIT)
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) - Persistent task tracking with file-based plans
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

The broader ecosystem has thousands more. Discover skills at [skills.sh](https://skills.sh/), [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills), [skillsmp.com](https://skillsmp.com/) or install from any GitHub repo with `npx skills add`.

### Research & inspiration

- [Boris Cherny's workflow principles](https://x.com/bcherny/status/2007179832300581177) - seven principles for effective Claude Code usage (informed cc-rig's workflow model)
- [Thariq on prompt caching](https://www.techtwitter.com/articles/lessons-from-building-claude-code-prompt-caching-is-everything) - how Claude Code's team optimizes caching (informed cc-rig's cache-aware architecture)
- [What great CLAUDE.md files have in common](https://blog.devgenius.io/what-great-claude-md-files-have-in-common-db482172ad2c) - content patterns
- [HumanLayer's CLAUDE.md guide](https://www.humanlayer.dev/blog/writing-a-good-claude-md) - structure principles
- [Spec workflow](https://github.com/Pimzino/claude-code-spec-workflow) by Pimzino - plan-first development
- [cc-gtd](https://github.com/adagradschool/cc-gtd) by adagradschool - GTD for Claude Code
- [SuperClaude](https://github.com/superclaude/superclaude) - runtime framework, different approach
- [QMD](https://github.com/tobi/qmd) by Tobi Lütke - local doc search
- [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) - community directory
- [Ralph Wiggum technique](https://github.com/ghuntley/how-to-ralph-wiggum) by Geoffrey Huntley - autonomous loop pattern
