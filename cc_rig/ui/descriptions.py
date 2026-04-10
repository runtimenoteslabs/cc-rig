"""Centralized descriptions for TUI wizard screens.

Extracts human-readable descriptions from generator definitions and provides
educational content for workflows, templates, and hooks.
"""

from __future__ import annotations


def get_agent_descriptions() -> dict[str, str]:
    """Extract {name: description} from agent definitions."""
    from cc_rig.generators.agents import _AGENT_DEFS

    return {name: defn.description for name, defn in _AGENT_DEFS.items()}


def get_command_descriptions() -> dict[str, str]:
    """Extract {name: description} from command definitions."""
    from cc_rig.generators.commands import _COMMAND_DEFS

    return {name: tup[0] for name, tup in _COMMAND_DEFS.items()}


def get_plugin_descriptions() -> dict[str, str]:
    """Extract {name: description} from plugin catalog."""
    from cc_rig.plugins.registry import PLUGIN_CATALOG

    return {name: spec.description for name, spec in PLUGIN_CATALOG.items()}


def get_hook_descriptions() -> dict[str, str]:
    """User-facing descriptions for all hooks.

    The hook registry stores (event, matcher, type) but has no user-facing
    text, so these are authored here.
    """
    return {
        "format": "Auto-format files after Write/Edit",
        "lint": "Run linter before git commit",
        "typecheck": "Run type checker before git commit",
        "block-rm-rf": "Block dangerous rm -rf commands",
        "block-env": "Block writing to .env and secret files",
        "block-main": "Block direct push to main/master",
        "session-context": "Load project context at session start",
        "stop-validator": "Check uncommitted changes and run tests before stop",
        "memory-precompact": "Persist team context before compaction",
        "push-review": "Review changes before git push",
        "subagent-review": "Review subagent output for quality",
        "commit-message": "Enforce descriptive commit messages",
        "doc-review": "Check if docs need updating before stop",
        "autonomy-loop": "Enable autonomous iteration with safety rails",
        "session-tasks": "Print task summary at session start (B1+)",
        "commit-gate": "Lint enforcement + test reminder on git commit (B2+)",
        "context-survival": "Preserve project context before compaction (B1+)",
        "session-telemetry": "Save session metrics to telemetry.jsonl on stop (B2+)",
    }


# ── Educational workflow details ─────────────────────────────────────

WORKFLOW_DETAILS: dict[str, str] = {
    "speedrun": (
        "Best for: Quick prototypes, hackathons, solo experiments\n"
        "Philosophy: Move fast, minimal guardrails. Get something working first.\n"
        "Includes:\n"
        "  Agents:   explorer, implementer\n"
        "  Commands: fix-issue, test, plan\n"
        "  Hooks:    format, block-rm-rf, block-env\n"
        "  Plugins:  commit-commands + LSP for your language\n"
        "  Features: none enabled by default"
    ),
    "standard": (
        "Best for: Most projects, teams, day-to-day development\n"
        "Philosophy: Balanced productivity with quality checks.\n"
        "Includes:\n"
        "  Agents:   code-reviewer, test-writer, explorer, refactorer\n"
        "  Commands: fix-issue, review, test, plan, learn, assumptions, refactor\n"
        "  Hooks:    format, lint, block-rm-rf, block-env, block-main, stop-validator\n"
        "  Plugins:  commit-commands, code-review + LSP for your language\n"
        "  Features: none enabled by default"
    ),
    "gstack": (
        "Best for: Startup teams, product-focused development\n"
        "Philosophy: Garry Tan's cognitive gears. Plan, Review, Ship.\n"
        "Source: garrytan/gstack (github.com/garrytan/gstack)\n"
        "Process skills:\n"
        "  /plan-ceo-review, /plan-eng-review, /plan-design-review,\n"
        "  /gstack-review, /ship, /document-release\n"
        "Includes:\n"
        "  Agents:   code-reviewer, test-writer, explorer, architect, pr-reviewer\n"
        "  Commands: fix-issue, review, test, plan, research, remember, refactor\n"
        "  Hooks:    format, lint, typecheck, block-rm-rf, block-env, block-main,\n"
        "            stop-validator, memory-precompact, push-review\n"
        "  Plugins:  commit-commands, code-review, pr-review-toolkit + LSP\n"
        "  Features: memory, worktrees enabled"
    ),
    "aihero": (
        "Best for: PRD-driven development, greenfield projects, TDD workflows\n"
        "Philosophy: Matt Pocock's skill-driven development. PRD first, then code.\n"
        "Source: mattpocock/skills (github.com/mattpocock/skills)\n"
        "Process skills:\n"
        "  /grill-me, /write-a-prd, /prd-to-issues, /mp-tdd,\n"
        "  /improve-codebase-architecture, /triage-issue, /design-an-interface\n"
        "Includes:\n"
        "  Agents:   code-reviewer, test-writer, explorer, architect, implementer, pm-spec\n"
        "  Commands: fix-issue, review, test, plan, spec-create, spec-execute, remember\n"
        "  Hooks:    format, lint, typecheck, block-rm-rf, block-env, block-main,\n"
        "            stop-validator, memory-precompact, push-review\n"
        "  Plugins:  commit-commands, code-review, feature-dev, pr-review-toolkit + LSP\n"
        "  Features: memory, spec-workflow, worktrees enabled"
    ),
    "spec-driven": (
        "Best for: Complex features, team handoffs, regulated environments\n"
        "Philosophy: Plan thoroughly before coding. Specs drive implementation.\n"
        "Source: cc-rig + mattpocock/skills + obra/superpowers\n"
        "Process skills:\n"
        "  /write-a-prd, /prd-to-issues, /writing-plans, /executing-plans\n"
        "Includes:\n"
        "  Agents:   code-reviewer, test-writer, explorer, architect, pm-spec,\n"
        "            implementer, parallel-worker (worktree isolation)\n"
        "  Commands: fix-issue, review, test, plan, spec-create, spec-execute,\n"
        "            assumptions, worktree\n"
        "  Hooks:    format, lint, typecheck, block-rm-rf, block-env, block-main,\n"
        "            stop-validator, push-review, commit-message\n"
        "  Plugins:  commit-commands, code-review, feature-dev, pr-review-toolkit + LSP\n"
        "  Features: spec-workflow, worktrees enabled"
    ),
    "superpowers": (
        "Best for: Production systems, security-critical code, maximum rigor\n"
        "Philosophy: Full SDLC skill suite. Every phase covered by community skills.\n"
        "Source: obra/superpowers (github.com/obra/superpowers)\n"
        "Process skills:\n"
        "  /brainstorming, /writing-plans, /executing-plans,\n"
        "  /test-driven-development, /systematic-debugging,\n"
        "  /requesting-code-review, /receiving-code-review,\n"
        "  /verification-before-completion, /subagent-driven-development\n"
        "Includes:\n"
        "  Agents:   all 12 core agents + parallel-worker\n"
        "  Commands: all 19 commands\n"
        "  Hooks:    format, lint, typecheck, block-rm-rf, block-env, block-main,\n"
        "            stop-validator, push-review, subagent-review, commit-message,\n"
        "            doc-review\n"
        "  Plugins:  commit-commands, code-review, pr-review-toolkit,\n"
        "            security-guidance + LSP for your language\n"
        "  Features: spec-workflow, worktrees enabled"
    ),
    "gtd": (
        "Best for: Solo devs managing multiple projects, personal productivity\n"
        "Philosophy: Capture everything, process later. Persistent tracking files.\n"
        "Source: OthmanAdi/planning-with-files + obra/superpowers\n"
        "Process skills:\n"
        "  /planning-with-files, /writing-plans, /executing-plans\n"
        "Includes:\n"
        "  Agents:   code-reviewer, test-writer, explorer, architect,\n"
        "            parallel-worker (worktree isolation)\n"
        "  Commands: fix-issue, review, test, plan, gtd-capture, gtd-process,\n"
        "            daily-plan, worktree\n"
        "  Hooks:    format, lint, typecheck, block-rm-rf, block-env, block-main,\n"
        "            stop-validator, memory-precompact, push-review\n"
        "  Plugins:  commit-commands, code-review + LSP for your language\n"
        "  Features: memory, gtd, worktrees enabled"
    ),
}


# ── Harness level details ────────────────────────────────────────────

HARNESS_DETAILS: dict[str, str] = {
    "none": (
        "B0 - No harness\n"
        "\n"
        "Your workflow's hooks, agents and commands work as configured.\n"
        "No additional files are generated. You decide what to work on\n"
        "and when to stop.\n"
        "\n"
        "Generates: Nothing beyond your workflow scaffold.\n"
        "\n"
        "Best for: Learning Claude Code, quick experiments, full manual control."
    ),
    "lite": (
        "B1 - Task tracking + budget awareness + context awareness\n"
        "\n"
        "Adds a task file and session-tasks hook so Claude sees open/done\n"
        "counts at startup. Budget-reminder hook fires on stop. Context\n"
        "survival hook preserves project context during compaction.\n"
        "\n"
        "Adds to your scaffold:\n"
        "  tasks/todo.md          - Task list Claude reads for priorities\n"
        "  agent_docs/harness.md  - Budget rules, context awareness docs\n"
        "  session-tasks hook     - Prints task summary at SessionStart\n"
        "  budget-reminder hook   - Prints budget status on Stop\n"
        "  context-survival hook  - Preserves project context on PreCompact\n"
        "\n"
        "Best for: Solo work where you want cost visibility and task structure."
    ),
    "standard": (
        "B2 - Enforcement gates + session telemetry\n"
        "\n"
        "Adds a commit-gate hook that runs lint on every git commit (blocks\n"
        "on failure) and prompts about tests. Session telemetry tracks metrics\n"
        "locally. An init-sh.sh utility wraps your test/lint/format commands.\n"
        "\n"
        "Adds to B1:\n"
        "  commit-gate hook           - Lint enforcement + test reminder on commit\n"
        "  session-telemetry hook     - Saves session metrics to telemetry.jsonl\n"
        "  .claude/commands/health.md - /health command for aggregated metrics\n"
        "  .claude/hooks/init-sh.sh   - Utility: verify, tidy, setup, test, lint\n"
        "  agent_docs/harness.md      - Enhanced with gate + telemetry docs\n"
        "\n"
        "Best for: Teams, production code, CI-like discipline in the editor."
    ),
    "autonomy": (
        "B3 - Autonomous iteration\n"
        "\n"
        "Generates a loop.sh script that restarts Claude in a loop. Each\n"
        "iteration follows a 5-step workflow: assess, advance, tidy, verify,\n"
        "record. Progress is tracked in claude-progress.txt. The loop reads\n"
        "harness-config.json for settings and detects stuck state.\n"
        "\n"
        "Adds to B2:\n"
        "  loop.sh                     - Bash loop with config reading + stuck detection\n"
        "  PROMPT.md                   - 5-step iteration instructions\n"
        "  claude-progress.txt         - Resumption ledger\n"
        "  .claude/harness-config.json - Machine-readable safety config\n"
        "\n"
        "Safety rails:\n"
        "  - Defaults to 20 iterations, configurable in harness-config.json\n"
        "  - Runs init-sh.sh tidy between iterations (entropy management)\n"
        "  - Detects stuck state (same task failing 2+ consecutive iterations)\n"
        "  - Warns on uncommitted changes if checkpoint_commits enabled\n"
        "\n"
        "WARNING: loop.sh uses --dangerously-skip-permissions to run\n"
        "without human approval prompts. Run inside a Docker container\n"
        "or sandboxed environment.\n"
        "\n"
        "Best for: Experienced users with well-tested codebases and clear tasks."
    ),
    "custom": (
        "Custom - À la carte feature selection\n"
        "\n"
        "Pick individual harness features without the B0→B1→B2→B3 tier\n"
        "progression. Mix and match what you need:\n"
        "\n"
        "  Task tracking       - todo.md + session-tasks hook\n"
        "  Budget awareness    - budget-reminder hook + budget docs\n"
        "  Verification gates  - commit-gate hook + init-sh.sh\n"
        "  Context awareness   - compaction survival hook + context docs\n"
        "  Session telemetry   - session metrics + /health command\n"
        "  Autonomy loop       - PROMPT.md + loop.sh + progress tracking\n"
        "\n"
        "Best for: Users who want specific features without the full tier."
    ),
    "ralph-loop": (
        "Ralph Loop - Official Anthropic autonomous loop plugin\n"
        "\n"
        "Uses the ralph-loop plugin from the Claude Code marketplace\n"
        "instead of cc-rig's loop.sh script. The plugin runs autonomously\n"
        "via Anthropic's official plugin system.\n"
        "\n"
        "You can still pick B1/B2 harness features alongside the plugin:\n"
        "  Task tracking       - todo.md + session-tasks hook\n"
        "  Budget awareness    - budget-reminder hook + budget docs\n"
        "  Verification gates  - commit-gate hook + init-sh.sh\n"
        "  Context awareness   - compaction survival hook + context docs\n"
        "  Session telemetry   - session metrics + /health command\n"
        "\n"
        "The plugin replaces: PROMPT.md, loop.sh, claude-progress.txt,\n"
        "  harness-config.json (cc-rig's autonomy files are not generated).\n"
        "\n"
        "Best for: Users who prefer the official Anthropic autonomy system."
    ),
}


# ── Template descriptions ────────────────────────────────────────────

TEMPLATE_DESCRIPTIONS: dict[str, str] = {
    "generic": "No specific stack, just the workflow",
    "fastapi": "Python / FastAPI - Modern async API framework",
    "django": "Python / Django - Batteries-included web framework",
    "flask": "Python / Flask - Lightweight WSGI micro-framework",
    "nextjs": "TypeScript / Next.js - Full-stack React framework",
    "express": "TypeScript / Express - Minimal Node.js web framework",
    "gin": "Go / Gin - High-performance HTTP web framework",
    "echo": "Go / Echo - Minimalist web framework",
    "go-std": "Go / stdlib - HTTP server using net/http",
    "rust-cli": "Rust / Clap - Command-line application toolkit",
    "rust-web": "Rust / Axum - Async web framework with tower middleware",
    "rails": "Ruby / Rails - Full-stack MVC web framework",
    "spring": "Java / Spring Boot - Enterprise web framework",
    "dotnet": ".NET / ASP.NET Core - Cross-platform web framework",
    "laravel": "PHP / Laravel - Full-stack web framework with Eloquent ORM",
    "phoenix": "Elixir / Phoenix - Real-time web framework with LiveView",
}


# ── Feature details for Review screen ─────────────────────────────────

FEATURE_DETAILS: list[dict[str, str]] = [
    {
        "key": "memory",
        "widget_id": "feat-memory",
        "label": "Memory - Claude remembers across sessions",
        "description": (
            "Claude saves decisions, conventions and project context at the\n"
            "end of each session. Next time, it picks up where you left off.\n"
            "No re-explaining your codebase or past choices. Use /remember to\n"
            "save specific notes."
        ),
        "adds": "/remember command and auto-save at session end",
    },
    {
        "key": "spec_workflow",
        "widget_id": "feat-spec",
        "label": "Spec workflow - plan before code",
        "description": (
            "Two-phase development: Claude writes a spec first, you review it,\n"
            "then Claude implements exactly what the spec says. Prevents scope\n"
            "creep and gives you a checkpoint between planning and coding."
        ),
        "adds": "Spec agents + /spec-create and /spec-execute commands",
    },
    {
        "key": "gtd",
        "widget_id": "feat-gtd",
        "label": "GTD - capture ideas, process later, daily plans",
        "description": (
            "Quick-capture ideas and bugs mid-flow without losing focus. Process\n"
            "them into prioritized tasks later. Start each day with a focused\n"
            "plan so Claude knows what to work on first."
        ),
        "adds": "/gtd-capture, /gtd-process and /daily-plan commands",
    },
    {
        "key": "worktrees",
        "widget_id": "feat-worktrees",
        "label": "Worktrees - parallel branches",
        "description": (
            "Run multiple tasks at the same time without conflicts. Each task\n"
            "gets its own isolated checkout — no stashing, no branch-switching,\n"
            "no stepping on each other's changes.\n"
            "\n"
            "Inside a session, use /worktree to delegate a task to a background\n"
            "agent. From the terminal, spawn several at once:\n"
            '  cc-rig worktree spawn "Add OAuth login" "Write API docs"\n'
            "Then check on them (list), create PRs (pr), and clean up when\n"
            "merged (cleanup --merged). Great for splitting a large feature\n"
            "into independent pieces that Claude works on in parallel."
        ),
        "adds": "Parallel worker agent + /worktree command + cc-rig worktree CLI",
    },
    {
        "key": "github_actions",
        "widget_id": "feat-github-actions",
        "label": "GitHub Actions - Claude reviews your PRs",
        "description": (
            "Generates a GitHub Actions workflow that runs Claude Code on\n"
            "every pull request using anthropics/claude-code-action@v1.\n"
            "Claude reviews changes, responds to @claude mentions in PR\n"
            "comments, and flags issues before human reviewers look at it.\n"
            "\n"
            "High-rigor workflows (verify-heavy, superpowers) add a\n"
            "separate security-review job that checks for auth issues,\n"
            "injection risks, and credentials in code."
        ),
        "adds": ".github/workflows/claude.yml with PR review + @claude triggers",
    },
]

# Which features each workflow enables by default
WORKFLOW_FEATURE_DEFAULTS: dict[str, set[str]] = {
    "speedrun": set(),
    "standard": {"memory", "github_actions"},
    "gstack": {"memory", "worktrees", "github_actions"},
    "aihero": {"memory", "spec_workflow", "worktrees", "github_actions"},
    "spec-driven": {"memory", "spec_workflow", "worktrees", "github_actions"},
    "superpowers": {"memory", "spec_workflow", "worktrees", "github_actions"},
    "gtd": {"memory", "gtd", "worktrees", "github_actions"},
    # Backward compat aliases
    "gtd-lite": {"memory", "gtd", "worktrees", "github_actions"},
    "verify-heavy": {"memory", "spec_workflow", "worktrees", "github_actions"},
}

# Features incompatible with specific workflows.
# Workflows with process_skills that cover planning/review should not
# allow adding conflicting features on top.
WORKFLOW_FEATURE_CONFLICTS: dict[str, set[str]] = {
    "speedrun": set(),
    "standard": set(),
    "gstack": {"spec_workflow", "gtd"},  # own plan/review/ship process
    "aihero": {"gtd"},  # PRD-driven process, gtd conflicts
    "spec-driven": {"gtd"},  # uses spec_workflow, gtd conflicts
    "superpowers": {"gtd"},  # full SDLC coverage, gtd conflicts
    "gtd": {"spec_workflow"},  # uses gtd, spec conflicts
    # Backward compat aliases
    "gtd-lite": {"spec_workflow"},
    "verify-heavy": {"gtd"},
}
