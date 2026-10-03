"""Generate .claude/commands/cc-rig.md playbook command.

The /cc-rig command is a single entry point for understanding what cc-rig
configured and how to use it. Content is built dynamically from ProjectConfig
so it reflects the actual workflow, agents, plugins, hooks, and harness.

Subcommands via $ARGUMENTS: (default=dashboard), detail, recipes, savings,
hooks, autonomous.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Optional

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.commands import _WORKFLOW_EFFORT
from cc_rig.generators.fileops import FileTracker
from cc_rig.pricing import MODEL_PRICING

_DATA_DIR = Path(__file__).parent.parent / "data"

# Workflow chains: the recommended task flow per workflow.
# Only canonical workflow names (aliases like gtd-lite/verify-heavy are
# resolved before ProjectConfig is created, so they never reach here).
WORKFLOW_CHAINS: dict[str, str] = {
    # Tiers
    "quick": "/fix-issue or /plan -> implement -> /test -> commit",
    "standard": "/plan -> implement -> /review -> /test -> commit",
    "rigorous": "/plan -> /spec-create -> implement -> /review -> /security -> /test -> commit",
    # Legacy workflow names (for backward compat in playbook display)
    "speedrun": "/fix-issue or /plan -> implement -> /test -> commit",
    "gstack": "/plan-ceo-review -> implement -> /gstack-review -> /ship",
    "aihero": "/plan -> /spec-create -> implement -> /review -> /test -> commit",
    "spec-driven": "/spec-create -> /spec-execute -> /review -> /test -> commit",
    "superpowers": "/plan -> /spec-create -> implement -> /review -> /security -> /test -> commit",
    "gtd": "/daily-plan -> /gtd-capture -> /gtd-process -> implement -> /test -> commit",
}

# Hook categories for the hooks section.
_HOOK_CATEGORIES: dict[str, tuple[str, str]] = {
    "format": ("Auto-format", "Every file Write"),
    "lint": ("Lint gate", "Only on git commit"),
    "typecheck": ("Typecheck gate", "Only on git commit"),
    "block-rm-rf": ("Block rm -rf", "Bash rm commands"),
    "block-env": ("Block .env writes", "Write to .env files"),
    "block-main": ("Block main push", "Bash git push to main"),
    "session-context": ("Session context", "Session start"),
    "stop-validator": ("Stop validator", "Session end"),
    "memory-precompact": ("Memory save", "Before compaction"),
    "push-review": ("Push review", "Before git push"),
    "subagent-review": ("Subagent review", "After subagent stops"),
    "commit-message": ("Commit message", "On git commit"),
    "doc-review": ("Doc review", "Session end"),
    "budget-reminder": ("Budget reminder", "Session end"),
    "session-tasks": ("Session tasks", "Session start"),
    "commit-gate": ("Commit gate", "On git commit"),
    "context-survival": ("Context survival", "Before compaction"),
    "session-telemetry": ("Session telemetry", "Session end"),
    "compress-output": ("Output compression", "After Bash"),
    "session-warmup": ("Session warm-up", "Session start"),
}


def _cache_price_table() -> list:
    """Uncached vs cached input prices, from cc_rig/pricing.py."""
    rows = [("Opus 5.5", "claude-opus-5-5"), ("Sonnet 5.5", "claude-sonnet-5")]
    lines = ["  Model       Uncached    Cached     Savings"]
    for name, key in rows:
        p_in, _, p_read = MODEL_PRICING[key]
        uncached = f"${p_in:g}/M"
        cached = f"${p_read:.2f}/M"
        lines.append(f"  {name:<11} {uncached:<11} {cached:<10} {1 - p_read / p_in:.0%}")
    return lines


@functools.lru_cache(maxsize=1)
def _load_agent_defs() -> dict[str, dict[str, str]]:
    """Load agent definitions for model/description info."""
    return json.loads((_DATA_DIR / "agents.json").read_text())


def generate_playbook(
    config: ProjectConfig,
    output_dir: Path,
    tracker: Optional[FileTracker] = None,
) -> list[str]:
    """Generate /cc-rig command + PLAYBOOK.md at project root.

    Returns list of relative file paths written.
    """
    files: list[str] = []

    # 1. The /cc-rig slash command (used inside Claude sessions)
    command_content = _build_command(config)
    rel_cmd = ".claude/commands/cc-rig.md"
    if tracker is not None:
        tracker.write_text(rel_cmd, command_content)
    else:
        dest = output_dir / ".claude" / "commands"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "cc-rig.md").write_text(command_content)
    files.append(rel_cmd)

    # 2. PLAYBOOK.md at project root (readable without a Claude session)
    playbook_content = _build_playbook_md(config)
    rel_pb = "PLAYBOOK.md"
    if tracker is not None:
        tracker.write_text(rel_pb, playbook_content)
    else:
        (output_dir / "PLAYBOOK.md").write_text(playbook_content)
    files.append(rel_pb)

    return files


def _build_command(config: ProjectConfig) -> str:
    """Build the /cc-rig slash command file (.claude/commands/cc-rig.md)."""
    effort = _WORKFLOW_EFFORT.get(config.workflow)
    effort_line = f"effort: {effort}\n" if effort else ""

    parts = [
        "---\n"
        'description: "cc-rig dashboard: your workflow, recipes, savings, configuration"\n'
        "allowed-tools: Read, Glob, Grep, Bash\n"
        f"{effort_line}"
        "---\n",
        _dispatch_instruction(),
        _section_dashboard(config),
        _section_detail(config),
        _section_recipes(config),
        _section_savings(config),
        _section_tune(config),
        _section_hooks(config),
        _section_audit(config),
        _section_drift(config),
        _section_refresh(config),
        _section_retro(config),
    ]

    # Autonomous section only when harness supports it
    if config.harness.autonomy_loop:
        parts.append(_section_autonomous(config))

    return "\n".join(parts) + "\n"


def _build_playbook_md(config: ProjectConfig) -> str:
    """Build PLAYBOOK.md for project root (readable without a Claude session).

    Same content as the /cc-rig command sections, but formatted as a
    standalone markdown file with a header and /cc-rig cross-references.
    """
    parts = [
        f"# cc-rig Playbook: {config.workflow} + {config.framework}\n",
        "This file was generated by [cc-rig](https://github.com/runtimenoteslabs/cc-rig).",
        "For the interactive version, run `/cc-rig` in any Claude Code session.\n",
        "| Command | What it shows |",
        "|---------|-------------|",
        "| `/cc-rig` | Your dashboard: workflow, recipes, what's active |",
        "| `/cc-rig recipes` | Step-by-step guides for bugs, features, refactors |",
        "| `/cc-rig detail` | Full agent, plugin, and hook breakdown |",
        "| `/cc-rig savings` | Token economics and cache stats |",
        "| `/cc-rig tune` | Score the config, rank what to fix, apply safe fixes |",
        "| `/cc-rig hooks` | What fires when and why |",
        "| `/cc-rig audit` | Discipline read of recent sessions |",
        "| `/cc-rig drift` | What diverged from current config |",
        "| `/cc-rig refresh` | Re-run a generator to realign files |",
        "| `/cc-rig retro` | Weekly savings + audit + drift summary |",
    ]
    if config.harness.autonomy_loop:
        parts.append("| `/cc-rig autonomous` | Loop.sh, worktrees, safety rails |")
    parts.append("")

    # Reuse the same section builders
    parts.append(_section_dashboard(config))
    parts.append(_section_detail(config))
    parts.append(_section_recipes(config))
    parts.append(_section_savings(config))
    parts.append(_section_tune(config))
    parts.append(_section_hooks(config))
    parts.append(_section_audit(config))
    parts.append(_section_drift(config))
    parts.append(_section_refresh(config))
    parts.append(_section_retro(config))

    if config.harness.autonomy_loop:
        parts.append(_section_autonomous(config))

    parts.extend(
        [
            "",
            "---",
            "",
            "*Generated by cc-rig. Run `/cc-rig` inside Claude Code for the interactive version.*",
        ]
    )

    return "\n".join(parts) + "\n"


def _dispatch_instruction() -> str:
    """Instruction block telling Claude how to dispatch subcommands."""
    return (
        "The user ran `/cc-rig $ARGUMENTS`.\n"
        "\n"
        'If $ARGUMENTS is empty or "dashboard", show the **Dashboard** section below.\n'
        'If $ARGUMENTS is "detail", show the **Detail** section.\n'
        'If $ARGUMENTS is "recipes", show the **Recipes** section.\n'
        'If $ARGUMENTS is "savings", show the **Savings** section.\n'
        'If $ARGUMENTS is "tune", show the **Tune** section.\n'
        'If $ARGUMENTS is "hooks", show the **Hooks** section.\n'
        'If $ARGUMENTS is "audit", show the **Audit** section.\n'
        'If $ARGUMENTS is "drift", show the **Drift** section.\n'
        'If $ARGUMENTS is "refresh", show the **Refresh** section.\n'
        'If $ARGUMENTS is "retro", show the **Retro** section.\n'
        'If $ARGUMENTS is "autonomous", show the **Autonomous** section.\n'
        "If $ARGUMENTS is anything else, show the Dashboard and mention available subcommands.\n"
        "\n"
        "Show ONLY the requested section. Do not show all sections at once.\n"
    )


# ── Section builders ──────────────────────────────────────────────


def _section_dashboard(config: ProjectConfig) -> str:
    """Dashboard: compact overview of the user's setup."""
    workflow = config.workflow
    framework = config.framework
    chain = WORKFLOW_CHAINS.get(workflow, "/plan -> implement -> /review -> commit")

    agent_count = len(config.agents)
    plugin_count = len(config.recommended_plugins)
    hook_count = len(config.hooks)
    command_count = len(config.commands)

    lines = [
        "---",
        "",
        "## Dashboard",
        "",
        f"**cc-rig | {workflow} + {framework}**",
        "",
        "### Your Workflow",
        f"  {chain}",
        "",
        "### Quick Recipes",
        '  Bug fix:     `/fix-issue "description"`',
        "  New feature: `/plan` -> implement -> `/review` -> `/test`",
        "  Understand:  `/research` -> `/learn`",
        "  Refactor:    `/test` (coverage) -> `/refactor` -> `/review`",
    ]

    if config.features.spec_workflow:
        lines.append("  Spec-first:  `/spec-create` -> `/spec-execute` -> `/review`")
    if config.features.gtd:
        lines.append("  Daily plan:  `/daily-plan` -> `/gtd-capture` -> `/gtd-process`")

    lines.extend(
        [
            "",
            "### Token Economics",
            "  CLAUDE.md: cache-optimized (static-first layout)",
            "  Cache guardrails: 4 active (no mid-session CLAUDE.md edits,",
            "    no hook/plugin toggles, no model switching, memory via Read)",
            "",
            "### What's Active",
            f"  Agents: {agent_count}  |  Plugins: {plugin_count}"
            f"  |  Hooks: {hook_count}  |  Commands: {command_count}",
            "  Run `/cc-rig detail` for full breakdown",
        ]
    )

    return "\n".join(lines)


def _section_detail(config: ProjectConfig) -> str:
    """Detail: full breakdown of agents, plugins, hooks, security."""
    agent_defs = _load_agent_defs()

    lines = [
        "",
        "---",
        "",
        "## Detail",
        "",
        f"### Agents ({len(config.agents)})",
    ]

    for agent_name in config.agents:
        defn = agent_defs.get(agent_name, {})
        model = defn.get("model", "sonnet")
        desc = defn.get("description", agent_name)
        # Pad name to 20 chars for alignment
        padded = agent_name.ljust(20)
        lines.append(f"  {padded}{model.capitalize():<8}  {desc}")

    lines.extend(
        [
            "",
            f"### Plugins ({len(config.recommended_plugins)})",
        ]
    )

    for plugin in config.recommended_plugins:
        padded = plugin.name.ljust(20)
        lines.append(f"  {padded}{plugin.description}")

    lines.extend(
        [
            "",
            f"### Hooks ({len(config.hooks)})",
        ]
    )

    for hook_name in config.hooks:
        info = _HOOK_CATEGORIES.get(hook_name)
        if info:
            label, trigger = info
            padded = label.ljust(20)
            lines.append(f"  {padded}{trigger}")
        else:
            lines.append(f"  {hook_name}")

    # Security section — deny rules are unconditional for all workflows
    lines.extend(
        [
            "",
            "### Security",
            "  denyRead:  ~/.ssh/**, ~/.aws/**, ~/.gnupg/**, .env, credentials, secrets",
            "  denyWrite: ~/.ssh/**, ~/.aws/**, ~/.gnupg/**",
        ]
    )

    return "\n".join(lines)


def _section_recipes(config: ProjectConfig) -> str:
    """Recipes: workflow-specific task recipes."""
    lines = [
        "",
        "---",
        "",
        "## Recipes",
        "",
        "### Fix a Bug",
        '  `/fix-issue "users can\'t login after password reset"`',
        "  One command. Reproduces, diagnoses, fixes, tests, commits.",
        "",
        "### Build a Feature",
    ]

    if config.features.spec_workflow:
        lines.extend(
            [
                '  1. `/spec-create "add OAuth2 login with Google"`',
                "     Claude writes a spec. You review before any code.",
                "  2. `/spec-execute`",
                "     Claude implements exactly what the spec says.",
                "  3. `/review` -> `/test` -> commit",
            ]
        )
    else:
        lines.extend(
            [
                '  1. `/plan "add OAuth2 login with Google"`',
                "     Claude creates a checkpoint plan. Review it.",
                "  2. Implement. Claude has your stack context via agent_docs.",
                "  3. `/review`",
                "     Spawns code-reviewer agent. Multi-dimension review.",
                "  4. `/test`",
                "     Generates missing tests for your changes.",
                "  5. Commit.",
            ]
        )

    lines.extend(
        [
            "",
            "### Understand Unfamiliar Code",
            '  `/research "how does the auth middleware work?"`',
            "  Spawns explorer agent (Haiku, fast). Maps the code.",
            '  Then: `/learn "explain the token refresh flow"`',
            "",
            "### Refactor Safely",
            "  1. `/test` (ensure coverage on the area you're changing)",
            '  2. `/refactor "extract user validation into a service layer"`',
            "  3. `/review` (verify no behavior change)",
        ]
    )

    # Spec-driven recipes
    if config.features.spec_workflow:
        lines.extend(
            [
                "",
                "### Architecture Decision",
                "  Spawn the architect agent (Opus, effort: high):",
                '  "Design the data model for multi-tenant support"',
                "  Gets an ADR (Architecture Decision Record) back.",
            ]
        )

    # Security recipe
    if "security" in config.commands:
        lines.extend(
            [
                "",
                "### Security Review",
                '  `/security "review the authentication flow"`',
                "  Spawns security-auditor (Opus). OWASP-aware.",
            ]
        )

    # GTD recipes
    if config.features.gtd:
        lines.extend(
            [
                "",
                "### Daily Planning (GTD)",
                "  `/daily-plan`  Review tasks, set today's priorities.",
                "  `/gtd-capture` Quick-capture an idea to inbox.",
                "  `/gtd-process` Process inbox: action, defer, or delete.",
            ]
        )

    # Assumptions recipe
    if "assumptions" in config.commands:
        lines.extend(
            [
                "",
                "### Check Your Assumptions",
                '  `/assumptions "I think we should add Redis caching here"`',
                "  Surfaces hidden assumptions with confidence levels.",
            ]
        )

    return "\n".join(lines)


def _section_savings(config: ProjectConfig) -> str:
    """Savings: token economics explained."""
    lines = [
        "",
        "---",
        "",
        "## Savings",
        "",
        "### Your numbers (last 30 days)",
        "Run the CLI to see real session data for this project:",
        "",
        "```bash",
        "cc-rig savings              # last 30 days + 4-week trend + cache breakers",
        "cc-rig savings --weeks 8    # extend the trend window",
        "cc-rig savings --json       # machine-readable for tooling",
        "```",
        "",
        "The first run seeds `~/.cc-rig/baseline.json` so cross-project rank",
        "shows up once you have at least two projects tracked. Pass",
        "`--no-baseline` to skip the user-scoped baseline entirely.",
        "",
        "### How the prompt cache works",
        "Claude Code's prompt cache is prefix-matched. If the system prompt",
        "and CLAUDE.md are byte-identical to the previous request, cached",
        "tokens cost a small fraction of uncached ones. Claude Code caches on",
        "its own; cc-rig's job is to keep your config from breaking it.",
        "",
        *_cache_price_table(),
        "",
        "### What cc-rig does",
        "1. **Static-first CLAUDE.md.** Project identity, commands, guardrails at",
        "   top (never change). Current context at bottom (changes each session).",
        "   Only the tail breaks cache.",
        "",
        "2. **4 cache guardrails** (in your CLAUDE.md):",
        "   - Don't edit CLAUDE.md mid-session",
        "   - Don't toggle hooks/plugins",
        "   - Don't switch models (use subagents)",
        "   - Load memory via Read tool, not inline",
    ]

    step = 3
    if config.harness.context_awareness:
        lines.extend(
            [
                "",
                f"{step}. **Compaction survival** (context_awareness harness).",
                "   PreCompact hook outputs project essentials before context wipe.",
                "   You don't lose critical state when the window fills up.",
            ]
        )
        step += 1

    if config.harness.session_telemetry:
        lines.extend(
            [
                "",
                f"{step}. **Session telemetry** (session_telemetry harness).",
                "   Tracks cache hit rate, token usage, cost per session.",
                "   Written to .claude/telemetry.jsonl.",
            ]
        )

    lines.extend(
        [
            "",
            "### 14 cache-break vectors (things that invalidate cache)",
            "  Editing CLAUDE.md, toggling hooks, switching models,",
            "  connecting/disconnecting MCP, changing settings.json,",
            "  modifying agent docs, enabling/disabling web search...",
            "  (Full list in agent_docs/cache-friendly-workflow.md)",
        ]
    )

    return "\n".join(lines)


_QUALITY_GATE_HOOKS = frozenset(
    {"lint", "typecheck", "commit-gate", "commit-message", "push-review", "subagent-review"}
)
_SAFETY_HOOKS = frozenset({"block-rm-rf", "block-env", "block-main"})


def _section_hooks(config: ProjectConfig) -> str:
    """Hooks: categorized hook list with explanations."""
    automatic: list[tuple[str, str]] = []
    quality_gates: list[tuple[str, str]] = []
    safety: list[tuple[str, str]] = []

    for hook_name in config.hooks:
        info = _HOOK_CATEGORIES.get(hook_name)
        label = info[0] if info else hook_name
        trigger = info[1] if info else ""

        if hook_name in _QUALITY_GATE_HOOKS:
            quality_gates.append((label, trigger))
        elif hook_name in _SAFETY_HOOKS:
            safety.append((label, trigger))
        else:
            automatic.append((label, trigger))

    lines = [
        "",
        "---",
        "",
        "## Hooks",
        "",
        "### Automatic (fires without you doing anything)",
    ]
    for label, trigger in automatic:
        lines.append(f"  {label.ljust(20)}{trigger}")

    if quality_gates:
        lines.extend(
            [
                "",
                "### Quality gates (fires on specific actions only)",
            ]
        )
        for label, trigger in quality_gates:
            lines.append(f"  {label.ljust(20)}{trigger}")
        lines.extend(
            [
                "  These only fire on specific commands, not on every Bash call.",
                "  (Conditional hooks, CC v2.1.85+)",
            ]
        )

    if safety:
        lines.extend(
            [
                "",
                "### Safety (fires on dangerous commands only)",
            ]
        )
        for label, trigger in safety:
            lines.append(f"  {label.ljust(20)}{trigger}")

    lines.extend(
        [
            "",
            "### Why conditional?",
            "  Old-style hooks fired on every Bash command. Lint running on",
            '  "ls" wastes time and tokens. cc-rig uses conditional hooks so',
            "  quality gates fire only when relevant.",
        ]
    )

    return "\n".join(lines)


def _section_tune(config: ProjectConfig) -> str:
    """Tune: score the config and apply safe fixes (points at the CLI)."""
    return "\n".join(
        [
            "",
            "---",
            "",
            "## Tune",
            "",
            "Score this project's Claude Code config and rank what to fix. Run the CLI:",
            "",
            "```bash",
            "cc-rig tune                  # 0-100 score, ranked opportunities",
            "cc-rig tune --fix            # apply safe fixes, show the diff, re-score",
            "cc-rig tune --ci             # exit non-zero below --min-score (default 60)",
            "cc-rig tune --json           # machine-readable",
            "```",
            "",
            "Dollar figures come from this project's session logs; with no history",
            "they are left out rather than guessed. Inside a session, Claude Code's",
            "`/cost` names the likely cause of each cache miss, and `/doctor` and",
            "`/skill-doctor` trim CLAUDE.md and unused skills.",
        ]
    )


def _section_audit(config: ProjectConfig) -> str:
    """Audit: tier-fit discipline read of recent sessions (points at the CLI)."""
    return "\n".join(
        [
            "",
            "---",
            "",
            "## Audit",
            "",
            "How closely your recent sessions match your tier's discipline. Run the CLI:",
            "",
            "```bash",
            "cc-rig audit            # discipline read of the last 10 sessions",
            "cc-rig audit --last 20  # widen the window",
            "cc-rig audit --json     # machine-readable",
            "```",
            "",
            "It scores observable signals from your session logs (cache hygiene, model",
            "pinning, cache read ratio, session shape) against your tier and gives a",
            "tier-fit verdict. Slash-command chains are not in the logs, so it reads",
            "discipline, not command-by-command compliance.",
        ]
    )


def _section_drift(config: ProjectConfig) -> str:
    """Drift: what diverged from a fresh regen (points at the CLI)."""
    return "\n".join(
        [
            "",
            "---",
            "",
            "## Drift",
            "",
            "What has diverged from what cc-rig would generate today:",
            "",
            "```bash",
            "cc-rig drift            # file, config, and CC-version drift",
            "cc-rig drift --json",
            "```",
            "",
            "Three signals: generated files edited by hand, `.cc-rig.json` changed",
            "since init, and the installed Claude Code drifting from cc-rig's pinned",
            "version. Run `cc-rig refresh <area>` to realign.",
        ]
    )


def _section_refresh(config: ProjectConfig) -> str:
    """Refresh: re-run a generator with a diff preview (points at the CLI)."""
    return "\n".join(
        [
            "",
            "---",
            "",
            "## Refresh",
            "",
            "Re-run a single generator with a diff preview, then write on confirm:",
            "",
            "```bash",
            "cc-rig refresh all              # preview + realign everything",
            "cc-rig refresh agents          # one area: agents, commands, skills,",
            "                               #   rules, settings, plugins, hooks",
            "cc-rig refresh settings --yes  # apply without prompting",
            "cc-rig refresh agents --dry-run  # preview only",
            "```",
            "",
            "Backs up any file it overwrites, same as `cc-rig init`.",
        ]
    )


def _section_retro(config: ProjectConfig) -> str:
    """Retro: weekly savings + audit + drift in one view (points at the CLI)."""
    return "\n".join(
        [
            "",
            "---",
            "",
            "## Retro",
            "",
            "Your weekly review: savings, discipline, and drift in one view:",
            "",
            "```bash",
            "cc-rig retro            # week-of summary + one suggestion",
            "cc-rig retro --json",
            "```",
            "",
            "Run it weekly. The session-start nudge and the CLAUDE.md footer both",
            "point here. It folds the week into your cross-project baseline so trends",
            "accrue over time.",
        ]
    )


def _section_autonomous(config: ProjectConfig) -> str:
    """Autonomous: only generated when harness supports autonomy."""
    lines = [
        "",
        "---",
        "",
        "## Autonomous",
        "",
        "### When to use",
        "- You have 3+ independent tasks",
        "- Each takes 5-30 minutes for Claude",
        "- You'll be away or doing something else",
        "",
        "### How",
        "1. List tasks in .claude/todo.md (one per line, be specific)",
        "2. Run:  `bash .claude/harness/loop.sh`",
        "3. Watch: `tail -f .claude/harness/claude-progress.txt`",
        "4. It auto-stops at budget limit ($5 default)",
        "",
        "### Safety rails",
        "- Iteration limit (default: 10)",
        "- Budget enforcement with cost tracking",
        "- Checkpoint auto-commit after each task",
        "- Stuck detection (3 consecutive failures = stop)",
        "- Cost summary on exit",
        "",
        "### Warning",
        "`loop.sh` uses `--dangerously-skip-permissions`.",
        "Run inside Docker or a sandboxed environment.",
        "Never run on a repo with uncommitted work you care about.",
    ]

    if config.features.worktrees:
        lines.extend(
            [
                "",
                "### Parallel work (worktrees)",
                '  `cc-rig worktree spawn "Add OAuth" "Fix pagination" "Write docs"`',
                "",
                "Each task: own git branch, isolated checkout, independent.",
                "  `cc-rig worktree list`       Check progress",
                "  `cc-rig worktree pr --all`   Create PRs for all",
                "  `cc-rig worktree cleanup`    Clean up merged branches",
            ]
        )

    return "\n".join(lines)
