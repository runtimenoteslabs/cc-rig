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
        "memory-stop": "Save team decisions and learnings before stop",
        "memory-precompact": "Persist team context before compaction",
        "push-review": "Review changes before git push",
        "subagent-review": "Review subagent output for quality",
        "commit-message": "Enforce descriptive commit messages",
        "doc-review": "Check if docs need updating before stop",
        "autonomy-loop": "Enable autonomous iteration with safety rails",
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
        "  Features: none enabled by default"
    ),
    "standard": (
        "Best for: Most projects, teams, day-to-day development\n"
        "Philosophy: Balanced productivity with quality checks.\n"
        "Includes:\n"
        "  Agents:   code-reviewer, test-writer, explorer, refactorer\n"
        "  Commands: fix-issue, review, test, plan, learn, assumptions, refactor\n"
        "  Hooks:    format, lint, block-rm-rf, block-env, block-main, stop-validator\n"
        "  Features: none enabled by default"
    ),
    "spec-driven": (
        "Best for: Complex features, team handoffs, regulated environments\n"
        "Philosophy: Plan thoroughly before coding. Specs drive implementation.\n"
        "Includes:\n"
        "  Agents:   code-reviewer, test-writer, explorer, architect, pm-spec, implementer\n"
        "  Commands: fix-issue, review, test, plan, spec-create, spec-execute, assumptions\n"
        "  Hooks:    format, lint, typecheck, block-rm-rf, block-env, block-main,\n"
        "            stop-validator, push-review, commit-message\n"
        "  Features: spec-workflow enabled"
    ),
    "gtd-lite": (
        "Best for: Solo devs managing multiple projects, personal productivity\n"
        "Philosophy: Capture everything, process later. Never lose an idea.\n"
        "Includes:\n"
        "  Agents:   code-reviewer, test-writer, explorer\n"
        "  Commands: fix-issue, review, test, plan, gtd-capture, gtd-process, daily-plan\n"
        "  Hooks:    format, lint, block-rm-rf, block-env, stop-validator, memory-stop\n"
        "  Features: memory, gtd enabled"
    ),
    "verify-heavy": (
        "Best for: Production systems, security-critical code, compliance\n"
        "Philosophy: Trust nothing. Verify everything. Every change is reviewed.\n"
        "Includes:\n"
        "  Agents:   code-reviewer, test-writer, explorer, architect, pr-reviewer,\n"
        "            security-auditor, doc-writer\n"
        "  Commands: fix-issue, review, test, plan, security, document, assumptions\n"
        "  Hooks:    format, lint, typecheck, block-rm-rf, block-env, block-main,\n"
        "            stop-validator, push-review, subagent-review, commit-message, doc-review\n"
        "  Features: none enabled by default"
    ),
}


# ── Harness level details ────────────────────────────────────────────

HARNESS_DETAILS: dict[str, str] = {
    "none": (
        "B0 — No harness\n"
        "\n"
        "Your workflow's hooks, agents, and commands work as configured.\n"
        "No additional files are generated. You decide what to work on\n"
        "and when to stop.\n"
        "\n"
        "Generates: Nothing beyond your workflow scaffold.\n"
        "\n"
        "Best for: Learning Claude Code, quick experiments, full manual control."
    ),
    "lite": (
        "B1 — Task tracking + budget awareness\n"
        "\n"
        "Generates a task file and budget guide that Claude reads at session\n"
        "start. Claude will check tasks/todo.md for priorities and be mindful\n"
        "of token usage. Also adds a budget-reminder hook that prints budget\n"
        "status when Claude stops.\n"
        "\n"
        "Adds to your scaffold:\n"
        "  tasks/todo.md              — Task list Claude reads for priorities\n"
        "  agent_docs/budget-guide.md — Budget rules and usage guidelines\n"
        "  budget-reminder hook       — Prints budget status on Stop\n"
        "\n"
        "Best for: Solo work where you want cost visibility and task structure."
    ),
    "standard": (
        "B2 — Verification gates\n"
        "\n"
        "Adds written instructions that tell Claude it must run tests and lint\n"
        "before considering a task done or ending a session. Your hooks still\n"
        "fire on their events as usual — this adds explicit rules Claude follows\n"
        "about when to verify and what to do on failure.\n"
        "\n"
        "Adds to B1:\n"
        "  agent_docs/verification-gates.md — Rules: run tests + lint before\n"
        "                                     committing, completing, or stopping\n"
        "  agent_docs/review-notes.md       — Captures review learnings per session\n"
        "\n"
        "Best for: Teams, production code, CI-like discipline in the editor."
    ),
    "autonomy": (
        "B3 — Autonomous iteration\n"
        "\n"
        "Generates a loop.sh script that restarts Claude in a loop. Each\n"
        "iteration, Claude reads PROMPT.md, picks a task from tasks/todo.md,\n"
        "implements it, verifies, commits, and exits. The script then restarts\n"
        "Claude with fresh context for the next task.\n"
        "\n"
        "Adds to B2:\n"
        "  loop.sh                      — Bash loop that drives iteration\n"
        "  PROMPT.md                    — Instructions Claude reads each cycle\n"
        "  agent_docs/autonomy-loop.md  — Safety rails documentation\n"
        "\n"
        "Safety rails:\n"
        "  • Defaults to 20 iterations — adjustable in loop.sh\n"
        "  • Commit after each task — every change is a rollback point\n"
        "  • Halt when stuck — stops if tests fail twice in a row\n"
        "  • autonomy-loop hook — auto-enabled to enforce the above\n"
        "\n"
        "Best for: Experienced users with well-tested codebases and clear tasks."
    ),
}


# ── Template descriptions ────────────────────────────────────────────

TEMPLATE_DESCRIPTIONS: dict[str, str] = {
    "fastapi": "Python / FastAPI — Modern async API framework",
    "django": "Python / Django — Batteries-included web framework",
    "flask": "Python / Flask — Lightweight WSGI micro-framework",
    "nextjs": "TypeScript / Next.js — Full-stack React framework",
    "gin": "Go / Gin — High-performance HTTP web framework",
    "echo": "Go / Echo — Minimalist web framework",
    "rust-cli": "Rust / Clap — Command-line application toolkit",
}


# ── Feature details for Review screen ─────────────────────────────────

FEATURE_DETAILS: list[dict[str, str]] = [
    {
        "key": "memory",
        "widget_id": "feat-memory",
        "label": "Memory — Claude remembers across sessions",
        "description": (
            "Claude saves decisions, conventions, and project context at the\n"
            "end of each session. Next time, it picks up where you left off —\n"
            "no re-explaining your codebase or past choices. Use /remember to\n"
            "save specific notes."
        ),
        "adds": "/remember command and auto-save at session end",
    },
    {
        "key": "spec_workflow",
        "widget_id": "feat-spec",
        "label": "Spec workflow — plan before code",
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
        "label": "GTD — capture ideas, process later, daily plans",
        "description": (
            "Quick-capture ideas and bugs mid-flow without losing focus. Process\n"
            "them into prioritized tasks later. Start each day with a focused\n"
            "plan so Claude knows what to work on first."
        ),
        "adds": "/gtd-capture, /gtd-process, and /daily-plan commands",
    },
    {
        "key": "worktrees",
        "widget_id": "feat-worktrees",
        "label": "Worktrees — parallel branches",
        "description": (
            "Work on multiple branches simultaneously. Claude spins up isolated\n"
            "checkouts for independent tasks — no stashing or branch-switching.\n"
            "Each worktree has its own working directory."
        ),
        "adds": "Parallel worker agent + /worktree command",
    },
]

# Which features each workflow enables by default
WORKFLOW_FEATURE_DEFAULTS: dict[str, set[str]] = {
    "speedrun": set(),
    "standard": {"memory"},
    "spec-driven": {"memory", "spec_workflow", "worktrees"},
    "gtd-lite": {"memory", "gtd", "worktrees"},
    "verify-heavy": {"memory", "spec_workflow", "worktrees"},
}
