"""Harness file generation for B1-B3 runtime discipline levels.

B0 = scaffold only (no harness files).
B1 = Harness-Lite: task tracking + budget awareness.
B2 = Harness-Standard: + verification gates + review notes.
B3 = Autonomy Loop: + autonomous iteration with safety rails.

The B3 autonomy loop implements the Ralph Wiggum technique by Geoffrey Huntley.
See: https://github.com/ghuntley/how-to-ralph-wiggum
"""

from __future__ import annotations

import json
from pathlib import Path

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker
from cc_rig.generators.settings import _safe_cmd

# Harness levels in order of capability.
_LEVELS = ("none", "lite", "standard", "autonomy")


def generate_harness(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate harness files based on config.harness feature flags.

    Returns list of relative file paths written.
    """
    h = config.harness
    if not any(
        [
            h.task_tracking,
            h.budget_awareness,
            h.verification_gates,
            h.autonomy_loop,
            h.context_awareness,
            h.session_telemetry,
        ]
    ):
        return []

    files: list[str] = []

    # Task tracking and/or budget awareness: generate todo.md + harness.md
    if h.task_tracking or h.budget_awareness:
        files.extend(_generate_b1(config, output_dir, tracker))

    # Verification gates or autonomy loop: generate init-sh.sh
    if h.verification_gates or h.autonomy_loop:
        files.extend(_generate_init_sh(config, output_dir, tracker))

    # Verification gates: append gates section to harness.md
    if h.verification_gates:
        files.extend(_generate_b2(config, output_dir, tracker))

    # Autonomy loop: generate PROMPT.md, loop.sh, progress, config
    # Skip when ralph_loop_plugin is True — plugin handles autonomy
    if h.autonomy_loop and not h.ralph_loop_plugin:
        files.extend(_generate_b3(config, output_dir, tracker))

    # Context awareness: append context section to harness.md
    if h.context_awareness:
        files.extend(_generate_context_awareness(config, output_dir, tracker))

    # Session telemetry: append telemetry section to harness.md + /health command
    if h.session_telemetry:
        files.extend(_generate_session_telemetry(config, output_dir, tracker))

    return files


def _at_least(current: str, minimum: str) -> bool:
    """Check if current level is at least minimum level."""
    try:
        return _LEVELS.index(current) >= _LEVELS.index(minimum)
    except ValueError:
        return False


# ── B1: Harness-Lite ──────────────────────────────────────────────


def _generate_b1(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate B1 files: task tracking + budget awareness."""
    files: list[str] = []

    # tasks/todo.md — machine-parseable task list
    tasks_dir = output_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    _write(
        tasks_dir / "todo.md",
        "# Task List\n"
        "\n"
        "Track current tasks here. Claude reads this at session start.\n"
        "\n"
        "## Format\n"
        "\n"
        "```\n"
        "- [ ] Task description (priority: high/medium/low)\n"
        "- [x] Completed task\n"
        "```\n"
        "\n"
        "## Active Tasks\n"
        "\n"
        "<!-- Add tasks below -->\n",
        tracker=tracker,
        rel_path="tasks/todo.md",
    )
    files.append("tasks/todo.md")

    # agent_docs/harness.md — consolidated harness documentation
    agent_docs = output_dir / "agent_docs"
    agent_docs.mkdir(parents=True, exist_ok=True)

    budget_tokens = config.harness.budget_per_run_tokens
    budget_line = (
        f"- **Per-run token budget**: {budget_tokens:,} tokens\n"
        if budget_tokens
        else "- **Per-run token budget**: unlimited\n"
    )
    warn_pct = config.harness.budget_warn_at_percent

    _write(
        agent_docs / "harness.md",
        "# Harness — Budget & Task Tracking\n"
        "\n"
        "## Budget\n"
        "\n"
        f"{budget_line}"
        f"- **Warning threshold**: {warn_pct}% of budget\n"
        "\n"
        "## Rules\n"
        "\n"
        "1. Plan before acting. Read tasks/todo.md and prioritize.\n"
        "2. Use subagents for parallel work to stay within budget.\n"
        "3. Checkpoint often. Commit working code before moving on.\n"
        "4. Stop cleanly. When approaching budget, save state and stop.\n"
        "5. Log progress. Update tasks/todo.md.\n"
        "6. Fix failures immediately. Up to 2 attempts, then log in tasks/todo.md.\n"
        "\n"
        "## Task Format\n"
        "\n"
        "```\n"
        "- [ ] Task description (priority: high/medium/low)\n"
        "- [x] Completed task\n"
        "```\n",
        tracker=tracker,
        rel_path="agent_docs/harness.md",
    )
    files.append("agent_docs/harness.md")

    return files


# ── B2: Harness-Standard ──────────────────────────────────────────


def _generate_b2(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate B2 additions: enhance harness.md with gate documentation."""
    # Append gate section to harness.md (may or may not exist from B1).
    agent_docs = output_dir / "agent_docs"
    agent_docs.mkdir(parents=True, exist_ok=True)
    harness_path = agent_docs / "harness.md"
    rel = "agent_docs/harness.md"

    tests_gate = "REQUIRED" if config.harness.require_tests_pass else "optional"
    lint_gate = "REQUIRED" if config.harness.require_lint_pass else "optional"
    test_cmd = config.test_cmd or "echo 'No test command configured'"
    lint_cmd = config.lint_cmd or "echo 'No linter configured'"

    gate_section = (
        "\n"
        "## Verification Gates\n"
        "\n"
        "| Gate | Status | Command |\n"
        "|------|--------|---------|\n"
        f"| Tests | {tests_gate} | `{test_cmd}` |\n"
        f"| Lint | {lint_gate} | `{lint_cmd}` |\n"
        "\n"
        "Lint is enforced by the commit-gate hook (blocks on failure).\n"
        "Tests are prompted — run `./init-sh.sh verify` before committing.\n"
        "\n"
        "## init-sh.sh Reference\n"
        "\n"
        "```\n"
        "./init-sh.sh verify  — run tests + lint\n"
        "./init-sh.sh tidy    — format + verify\n"
        "./init-sh.sh test    — run tests only\n"
        "./init-sh.sh lint    — run lint only\n"
        "./init-sh.sh setup   — install/build\n"
        "```\n"
    )

    # Append to existing harness.md
    existing = ""
    if tracker is not None:
        # When using tracker, read via the tracker's output_dir
        if harness_path.exists():
            existing = harness_path.read_text()
    else:
        if harness_path.exists():
            existing = harness_path.read_text()

    _write(
        harness_path,
        existing + gate_section,
        tracker=tracker,
        rel_path=rel,
    )

    # Only add to file list if B1 didn't already add harness.md
    if not existing:
        return [rel]
    return []


# ── init-sh.sh (B2+) ─────────────────────────────────────────────


def _generate_init_sh(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate .claude/hooks/init-sh.sh utility script at B2+."""
    test_cmd = _safe_cmd(config.test_cmd or "", "echo 'No test command configured'")
    lint_cmd = _safe_cmd(config.lint_cmd or "", "echo 'No linter configured'")
    format_cmd = _safe_cmd(config.format_cmd or "", "echo 'No formatter configured'")
    build_cmd = _safe_cmd(config.build_cmd or "", "echo 'No build command configured'")

    content = (
        "#!/usr/bin/env bash\n"
        "# cc-rig utility: init-sh — project verification and maintenance\n"
        "# Generated by cc-rig. Commands are substituted from project config.\n"
        "#\n"
        "# Usage:\n"
        "#   ./init-sh.sh verify  — run tests + lint\n"
        "#   ./init-sh.sh tidy    — format + verify\n"
        "#   ./init-sh.sh setup   — install dependencies\n"
        "#   ./init-sh.sh test    — run tests only\n"
        "#   ./init-sh.sh lint    — run lint only\n"
        "\n"
        "set -euo pipefail\n"
        "\n"
        'CMD="${1:-verify}"\n'
        "\n"
        'case "$CMD" in\n'
        "  test)\n"
        f"    {test_cmd}\n"
        "    ;;\n"
        "  lint)\n"
        f"    {lint_cmd}\n"
        "    ;;\n"
        "  verify)\n"
        f"    {test_cmd}\n"
        f"    {lint_cmd}\n"
        "    ;;\n"
        "  tidy)\n"
        f"    {format_cmd}\n"
        f"    {test_cmd}\n"
        f"    {lint_cmd}\n"
        "    ;;\n"
        "  setup)\n"
        f"    {build_cmd}\n"
        "    ;;\n"
        "  *)\n"
        '    echo "Usage: $0 {verify|tidy|setup|test|lint}" >&2\n'
        "    exit 1\n"
        "    ;;\n"
        "esac\n"
    )

    rel = ".claude/hooks/init-sh.sh"
    hooks_dir = output_dir / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    if tracker is not None:
        tracker.write_text(rel, content)
        tracker.chmod(rel, 0o755)
    else:
        path = hooks_dir / "init-sh.sh"
        path.write_text(content)
        path.chmod(0o755)

    return [rel]


# ── B3: Autonomy Loop ─────────────────────────────────────────────


def _generate_b3(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate B3 files: autonomy loop + safety rails."""
    files: list[str] = []
    h = config.harness

    # ── Enhance harness.md with autonomy section ──────────────────
    agent_docs = output_dir / "agent_docs"
    agent_docs.mkdir(parents=True, exist_ok=True)
    harness_path = agent_docs / "harness.md"

    blocked_action = "Stop and save state" if h.if_blocked == "stop" else "Skip to next task"
    checkpoint_str = "Yes - commit after each task" if h.checkpoint_commits else "No"

    autonomy_section = (
        "\n"
        "## Autonomy Loop\n"
        "\n"
        "Based on the Ralph Wiggum technique by Geoffrey Huntley.\n"
        "See: https://github.com/ghuntley/how-to-ralph-wiggum\n"
        "\n"
        "| Setting | Value |\n"
        "|---------|-------|\n"
        f"| Max iterations | {h.max_iterations} |\n"
        f"| Checkpoint commits | {checkpoint_str} |\n"
        f"| If blocked | {blocked_action} |\n"
        "\n"
        "Run: `./loop.sh` (default) or `./loop.sh 50` (override max).\n"
        "Press Ctrl+C to stop. See PROMPT.md for iteration instructions.\n"
        "\n"
        "**WARNING**: loop.sh uses `--dangerously-skip-permissions`.\n"
        "Run inside a Docker container or sandboxed environment.\n"
        "See: https://docs.anthropic.com/en/docs/claude-code/security\n"
    )

    existing = ""
    if harness_path.exists():
        existing = harness_path.read_text()
    _write(
        harness_path,
        existing + autonomy_section,
        tracker=tracker,
        rel_path="agent_docs/harness.md",
    )

    # ── PROMPT.md — 5-step work loop ──────────────────────────────
    blocked_instruction = (
        "log the blocker in tasks/todo.md and EXIT"
        if h.if_blocked == "stop"
        else "log the blocker, skip to the next incomplete task"
    )

    prompt_lines = [
        "# Autonomy Loop - Iteration Prompt",
        "",
        "You are operating in autonomous mode. Complete exactly ONE task",
        "per iteration, then exit so the loop restarts with fresh context.",
        "",
        "## Workflow (5 steps)",
        "",
        "1. **Assess**: Read `claude-progress.txt` for prior iteration state.",
        "   Read `tasks/todo.md` and pick the highest-priority `[ ]` task.",
    ]
    if config.features.memory:
        prompt_lines.append("   Read `memory/session-log.md` for context.")
    if config.features.spec_workflow:
        prompt_lines.append(
            "   If the task is a spec, use `/spec-create`."
            " If implementing, verify against spec criteria."
        )
    if config.features.gtd:
        prompt_lines.append("   If `tasks/inbox.md` has unprocessed items, triage them first.")

    prompt_lines += [
        "2. **Advance**: Implement the task.",
        "3. **Tidy**: Run `./init-sh.sh tidy` to format and verify.",
        "4. **Verify**: Run `./init-sh.sh verify` to confirm tests + lint pass.",
        "   If verification fails, fix the issue (up to 3 attempts).",
        "   If you can't fix it, log the failure in `tasks/todo.md`.",
        "5. **Record**: Update `claude-progress.txt` with iteration result.",
        "   Mark the task `[x]` in `tasks/todo.md`.",
        "   Commit with a clear message describing what you did and why.",
    ]
    if config.features.memory:
        prompt_lines.append("   Update `memory/` files before exiting.")
    if config.features.worktrees:
        prompt_lines.append("   Work on a worktree branch per iteration. Do not merge to main.")

    prompt_lines += [
        "",
        "## If blocked",
        "",
        f"- {blocked_instruction}.",
        "",
        "## Rules",
        "",
        "- Complete exactly ONE task per iteration.",
        "- Always commit working code before exiting.",
        "- Always update `tasks/todo.md` to reflect current state.",
        "- If all tasks are done, exit with message: ALL TASKS COMPLETE.",
        "- Do NOT carry assumptions from previous iterations - read fresh.",
    ]

    _write(
        output_dir / "PROMPT.md",
        "\n".join(prompt_lines) + "\n",
        tracker=tracker,
        rel_path="PROMPT.md",
    )
    files.append("PROMPT.md")

    # ── claude-progress.txt — resumption ledger ──────────────────
    _write(
        output_dir / "claude-progress.txt",
        "# Autonomy Progress Ledger\n"
        "# Format: iteration | status | task | timestamp\n"
        "# Written by Claude at the end of each iteration.\n",
        tracker=tracker,
        rel_path="claude-progress.txt",
    )
    files.append("claude-progress.txt")

    # ── loop.sh — enhanced with config reading + budget + cost ───
    loop_header = (
        "#!/usr/bin/env bash\n"
        "# Autonomy loop - based on the Ralph Wiggum technique by Geoffrey Huntley.\n"
        "# https://github.com/ghuntley/how-to-ralph-wiggum\n"
        "#\n"
        "# Usage: ./loop.sh [max_iterations]\n"
        "#\n"
        "# WARNING: This runs Claude in autonomous mode without permission prompts.\n"
        "# Recommended: run inside a Docker container or sandboxed environment.\n"
        "# See: https://docs.anthropic.com/en/docs/claude-code/security\n"
        "\n"
        "set -euo pipefail\n"
    )

    loop_config = (
        "\n"
        "# Read config from harness-config.json if available\n"
        "CONFIG_FILE=.claude/harness-config.json\n"
        'if [ -f "$CONFIG_FILE" ]; then\n'
        '    DEFAULT_MAX=$(grep -o \'"max_iterations": *[0-9]*\' "$CONFIG_FILE" '
        "| grep -o '[0-9]*' || echo " + str(h.max_iterations) + ")\n"
        '    CHECKPOINT=$(grep -o \'"checkpoint_commits": *[a-z]*\' "$CONFIG_FILE" '
        "| grep -oE 'true|false' || echo true)\n"
        '    BUDGET_TOKENS=$(grep -o \'"per_run_tokens": *[0-9]*\' "$CONFIG_FILE" '
        "| grep -o '[0-9]*' || echo 0)\n"
        '    WARN_PERCENT=$(grep -o \'"warn_at_percent": *[0-9]*\' "$CONFIG_FILE" '
        "| grep -o '[0-9]*' || echo 80)\n"
        "else\n"
        f"    DEFAULT_MAX={h.max_iterations}\n"
        "    CHECKPOINT=true\n"
        "    BUDGET_TOKENS=0\n"
        "    WARN_PERCENT=80\n"
        "fi\n"
        "\n"
        'MAX_ITERATIONS="${1:-$DEFAULT_MAX}"\n'
        "ITERATION=0\n"
        'PREV_TASK=""\n'
        "STUCK_COUNT=0\n"
        "\n"
        "# Budget tracking accumulators\n"
        "CUMULATIVE_INPUT=0\n"
        "CUMULATIVE_OUTPUT=0\n"
        "CUMULATIVE_CACHE=0\n"
        "CUMULATIVE_COST_USD=0\n"
        "TOTAL_TOKENS=0\n"
        'if [ "$BUDGET_TOKENS" -gt 0 ] 2>/dev/null; then\n'
        "    WARN_THRESHOLD=$(( BUDGET_TOKENS * WARN_PERCENT / 100 ))\n"
        "else\n"
        "    BUDGET_TOKENS=0\n"
        "    WARN_THRESHOLD=0\n"
        "fi\n"
    )

    loop_trap = (
        "\n"
        "# Cost summary on exit\n"
        "cleanup() {\n"
        '    echo ""\n'
        '    echo "================================================"\n'
        '    echo "  Cost Summary"\n'
        '    echo "  Iterations: ${ITERATION}"\n'
        '    echo "  Total tokens in: ${CUMULATIVE_INPUT}"\n'
        '    echo "  Total tokens out: ${CUMULATIVE_OUTPUT}"\n'
        '    echo "  Total cache tokens: ${CUMULATIVE_CACHE}"\n'
        '    if [ "$CUMULATIVE_COST_USD" = "0" ] && [ "$TOTAL_TOKENS" -gt 0 ]; then\n'
        '        echo "  Est. cost: unavailable (python3 required)"\n'
        "    else\n"
        '        echo "  Est. cost: ~\\$${CUMULATIVE_COST_USD}"\n'
        "    fi\n"
        '    echo "================================================"\n'
        "}\n"
        "trap cleanup INT TERM\n"
    )

    loop_banner = (
        "\n"
        'echo ""\n'
        'echo "================================================"\n'
        'echo "  AUTONOMY LOOP - STARTING"\n'
        'echo "  Max iterations: ${MAX_ITERATIONS}"\n'
    )
    if h.budget_per_run_tokens is not None:
        loop_banner += 'echo "  Budget: ${BUDGET_TOKENS} tokens"\n'
    loop_banner += (
        'echo "  Press Ctrl+C to stop at any time."\n'
        'echo "================================================"\n'
        'echo ""\n'
    )

    loop_body_start = (
        "\n"
        "while [ $ITERATION -lt $MAX_ITERATIONS ]; do\n"
        "    ITERATION=$((ITERATION + 1))\n"
        '    echo ""\n'
        '    echo "--- Iteration ${ITERATION}/${MAX_ITERATIONS} ---"\n'
        '    echo ""\n'
        "\n"
        "    # Run tidy between iterations (entropy management)\n"
        "    if [ $ITERATION -gt 1 ] && [ -f .claude/hooks/init-sh.sh ]; then\n"
        "        bash .claude/hooks/init-sh.sh tidy 2>/dev/null"
        ' || echo "Tidy failed, continuing..."\n'
        "    fi\n"
    )

    loop_body_claude = (
        "\n"
        "    # Feed the prompt to Claude with JSON output for cost tracking.\n"
        "    # --dangerously-skip-permissions is required for unattended operation.\n"
        "    RESULT_FILE=$(mktemp)\n"
        '    BEFORE_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "none")\n'
        "    cat PROMPT.md | claude --dangerously-skip-permissions"
        ' --output-format json > "$RESULT_FILE" 2>/dev/null || true\n'
        "\n"
        "    # Parse cost from JSON result (requires python3)\n"
        "    ITER_INPUT=0\n"
        "    ITER_OUTPUT=0\n"
        "    ITER_CACHE=0\n"
        "    ITER_COST=0\n"
        "    HAS_PYTHON3=false\n"
        "    if command -v python3 >/dev/null 2>&1; then\n"
        "        HAS_PYTHON3=true\n"
        '        COST_DATA=$(python3 -c "\n'
        "import json, sys\n"
        "PRICING = {\n"
        "    'opus': (15.0, 75.0, 18.75, 1.50),\n"
        "    'sonnet': (3.0, 15.0, 3.75, 0.30),\n"
        "    'haiku': (0.80, 4.0, 1.0, 0.08),\n"
        "}\n"
        "try:\n"
        "    data = json.load(open(sys.argv[1]))\n"
        "    # Try top-level usage first, then nested message.usage\n"
        "    u = data.get('usage') or data.get('message', {}).get('usage', {})\n"
        "    t_in = u.get('input_tokens', 0)\n"
        "    t_out = u.get('output_tokens', 0)\n"
        "    t_cc = u.get('cache_creation_input_tokens', 0)\n"
        "    t_cr = u.get('cache_read_input_tokens', 0)\n"
        "    model_id = data.get('model') or data.get('message', {}).get('model', '')\n"
        "    family = 'opus' if 'opus' in model_id "
        "else 'haiku' if 'haiku' in model_id else 'sonnet'\n"
        "    p_in, p_out, p_cc, p_cr = PRICING[family]\n"
        "    cost = (t_in * p_in + t_out * p_out + t_cc * p_cc + t_cr * p_cr) / 1_000_000\n"
        "    print(f'{t_in} {t_out} {t_cc + t_cr} {cost:.4f}')\n"
        "except Exception:\n"
        "    print('0 0 0 0')\n"
        '" "$RESULT_FILE" 2>/dev/null) || COST_DATA="0 0 0 0"\n'
        "        ITER_INPUT=$(echo \"$COST_DATA\" | awk '{print $1}')\n"
        "        ITER_OUTPUT=$(echo \"$COST_DATA\" | awk '{print $2}')\n"
        "        ITER_CACHE=$(echo \"$COST_DATA\" | awk '{print $3}')\n"
        "        ITER_COST=$(echo \"$COST_DATA\" | awk '{print $4}')\n"
        "    fi\n"
        '    rm -f "$RESULT_FILE"\n'
        "\n"
        "    # Accumulate totals (all integer arithmetic except cost)\n"
        "    CUMULATIVE_INPUT=$((CUMULATIVE_INPUT + ITER_INPUT))\n"
        "    CUMULATIVE_OUTPUT=$((CUMULATIVE_OUTPUT + ITER_OUTPUT))\n"
        "    CUMULATIVE_CACHE=$((CUMULATIVE_CACHE + ITER_CACHE))\n"
        "    TOTAL_TOKENS=$((CUMULATIVE_INPUT + CUMULATIVE_OUTPUT + CUMULATIVE_CACHE))\n"
        '    if [ "$HAS_PYTHON3" = "true" ]; then\n'
        "        CUMULATIVE_COST_USD=$(python3 -c"
        " \"import sys; print(f'{float(sys.argv[1]) + float(sys.argv[2]):.4f}')\""
        ' "$CUMULATIVE_COST_USD" "$ITER_COST" 2>/dev/null) || true\n'
        "    fi\n"
    )

    loop_body_budget = (
        "\n"
        "    # Budget enforcement\n"
        '    if [ "$BUDGET_TOKENS" -gt 0 ] 2>/dev/null; then\n'
        '        if [ "$TOTAL_TOKENS" -ge "$BUDGET_TOKENS" ]; then\n'
        '            echo ""\n'
        '            echo "BUDGET EXCEEDED: ${TOTAL_TOKENS} / ${BUDGET_TOKENS} tokens used."\n'
        "            cleanup\n"
        "            break\n"
        "        fi\n"
        '        if [ "$WARN_THRESHOLD" -gt 0 ] && [ "$TOTAL_TOKENS" -ge "$WARN_THRESHOLD" ]'
        "; then\n"
        '            echo "WARNING: ${TOTAL_TOKENS} / ${BUDGET_TOKENS}'
        ' tokens used (${WARN_PERCENT}% threshold)."\n'
        "        fi\n"
        "    fi\n"
    )

    loop_body_stuck = (
        "\n"
        "    # Detect stuck state (same first open task 2+ consecutive iterations)\n"
        "    if [ -f tasks/todo.md ]; then\n"
        '        CURRENT_TASK=$(grep -m1 "^- \\[ \\]" tasks/todo.md 2>/dev/null || echo "")\n'
        '        if [ -n "$CURRENT_TASK" ] && [ "$CURRENT_TASK" = "$PREV_TASK" ]; then\n'
        "            STUCK_COUNT=$((STUCK_COUNT + 1))\n"
        "            if [ $STUCK_COUNT -ge 2 ]; then\n"
        '                echo ""\n'
        '                echo "WARNING: Same task failing'
        ' ${STUCK_COUNT} consecutive iterations."\n'
        '                echo "Task: ${CURRENT_TASK}"\n'
        '                echo "Consider manual intervention."\n'
        "            fi\n"
        "        else\n"
        "            STUCK_COUNT=0\n"
        "        fi\n"
        '        PREV_TASK="$CURRENT_TASK"\n'
        "    fi\n"
    )

    loop_body_checkpoint = (
        "\n"
        "    # Checkpoint enforcement: auto-commit if Claude didn't\n"
        '    if [ "$CHECKPOINT" = "true" ]; then\n'
        '        AFTER_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "none")\n'
        '        if [ "$BEFORE_HEAD" = "$AFTER_HEAD" ]; then\n'
        "            if ! git diff --quiet 2>/dev/null ||"
        " ! git diff --cached --quiet 2>/dev/null; then\n"
        "                git add -A && git commit -m"
        ' "checkpoint: auto-commit after iteration ${ITERATION}" 2>/dev/null || true\n'
        "            fi\n"
        "        fi\n"
        "    fi\n"
    )

    loop_body_progress = (
        "\n"
        "    # Progress ledger with cost\n"
        '    echo "iter=${ITERATION} | tokens_in=${ITER_INPUT} tokens_out=${ITER_OUTPUT}'
        ' | cost=\\$${ITER_COST} | cumulative=\\$${CUMULATIVE_COST_USD}"'
        " >> claude-progress.txt\n"
    )

    loop_body_tasks_done = (
        "\n"
        "    # Check if all tasks are done.\n"
        "    if [ -f tasks/todo.md ]; then\n"
        "        if ! grep -q '\\- \\[ \\]' tasks/todo.md; then\n"
        '            echo ""\n'
        '            echo "================================================"\n'
        '            echo "  ALL TASKS COMPLETE"\n'
        '            echo "  Finished after ${ITERATION} iterations."\n'
        '            echo "================================================"\n'
        "            cleanup\n"
        "            exit 0\n"
        "        fi\n"
        "    fi\n"
        "done\n"
    )

    loop_footer = (
        "\n"
        'echo ""\n'
        'echo "================================================"\n'
        'echo "  MAX ITERATIONS REACHED (${MAX_ITERATIONS})"\n'
        'echo "  Check tasks/todo.md for remaining work."\n'
        'echo "================================================"\n'
        "cleanup\n"
    )

    loop_content = (
        loop_header
        + loop_config
        + loop_trap
        + loop_banner
        + loop_body_start
        + loop_body_claude
        + loop_body_budget
        + loop_body_stuck
        + loop_body_checkpoint
        + loop_body_progress
        + loop_body_tasks_done
        + loop_footer
    )
    _write(
        output_dir / "loop.sh",
        loop_content,
        tracker=tracker,
        rel_path="loop.sh",
    )
    # Make loop.sh executable
    if tracker is not None:
        tracker.chmod("loop.sh", 0o755)
    else:
        (output_dir / "loop.sh").chmod(0o755)
    files.append("loop.sh")

    # ── .claude/harness-config.json — machine-readable safety config ──
    claude_dir = output_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    safety_config = {
        "harness_level": "autonomy",
        "max_iterations": h.max_iterations,
        "checkpoint_commits": h.checkpoint_commits,
        "if_blocked": h.if_blocked,
        "verification": {
            "require_tests_pass": h.require_tests_pass,
            "require_lint_pass": h.require_lint_pass,
        },
        "budget": {
            "per_run_tokens": h.budget_per_run_tokens,
            "warn_at_percent": h.budget_warn_at_percent,
        },
    }
    harness_json = json.dumps(safety_config, indent=2) + "\n"
    _write(
        claude_dir / "harness-config.json",
        harness_json,
        tracker=tracker,
        rel_path=".claude/harness-config.json",
    )
    files.append(".claude/harness-config.json")

    return files


# ── Helpers ────────────────────────────────────────────────────────


# ── Context Awareness ─────────────────────────────────────────────


def _generate_context_awareness(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Append context awareness section to agent_docs/harness.md."""
    files: list[str] = []
    harness_md = output_dir / "agent_docs" / "harness.md"
    rel = "agent_docs/harness.md"

    content = (
        "\n\n## Context Awareness\n"
        "\n"
        "### Cache-Break Vectors\n"
        "\n"
        "The following actions invalidate Claude Code's prompt cache. "
        "Avoid these mid-session:\n"
        "\n"
        "1. Editing CLAUDE.md (especially top sections)\n"
        "2. Adding or removing hooks in settings.json\n"
        "3. Connecting or disconnecting MCP servers\n"
        "4. Switching models mid-session\n"
        "5. Toggling plugins mid-session\n"
        "6. Editing settings.json permissions\n"
        "7. Large file writes that change system prompt composition\n"
        "8. Agent doc edits (if @imported in CLAUDE.md)\n"
        "9. Memory file changes (if inlined, not loaded via Read)\n"
        "10. Multiple concurrent sessions on the same project\n"
        "\n"
        "### Compaction Survival\n"
        "\n"
        "A PreCompact hook (`context-survival.sh`) fires before compaction. "
        "It outputs project-specific preservation instructions that Claude "
        "sees in the compaction summary prompt. This ensures critical project "
        "context survives automatic compaction at ~85-98% capacity.\n"
        "\n"
        "### Best Practices\n"
        "\n"
        "- Use subagents for exploratory work (keeps main context clean)\n"
        "- Checkpoint decisions to `memory/` or `tasks/todo.md`\n"
        "- Run `/compact` proactively at ~70% rather than waiting for auto-compact\n"
        "- After compaction, re-read `agent_docs/` to reload project context\n"
        "- Keep CLAUDE.md stable during a session to maximize cache hits\n"
    )

    if harness_md.exists():
        existing = harness_md.read_text()
        _write(harness_md, existing + content, tracker, rel)
    else:
        harness_md.parent.mkdir(parents=True, exist_ok=True)
        _write(harness_md, content.lstrip("\n"), tracker, rel)
        files.append(rel)

    return files


# ── Session Telemetry ─────────────────────────────────────────────


def _generate_session_telemetry(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Append telemetry section to harness.md and generate /health command."""
    files: list[str] = []
    harness_md = output_dir / "agent_docs" / "harness.md"
    rel = "agent_docs/harness.md"

    section = (
        "\n\n## Session Telemetry\n"
        "\n"
        "Metrics are appended to `.claude/telemetry.jsonl` after each session.\n"
        "\n"
        "### Tracked Metrics\n"
        "\n"
        "| Metric | Source |\n"
        "|--------|--------|\n"
        "| Session duration | First/last message timestamps |\n"
        "| Turn count | Human messages in JSONL |\n"
        "| Tool call count | Tool use blocks in assistant messages |\n"
        "| Model | Detected from assistant message model field |\n"
        "| Token usage | input_tokens, output_tokens from usage |\n"
        "| Estimated cost | Per-million pricing by model family |\n"
        "| Compaction count | System messages indicating compaction |\n"
        "\n"
        "### /health Command\n"
        "\n"
        "Run `/health` to see aggregated telemetry:\n"
        "- Total sessions and cumulative cost\n"
        "- Average session length\n"
        "- Most common model\n"
        "- Compaction frequency\n"
    )

    if harness_md.exists():
        existing = harness_md.read_text()
        _write(harness_md, existing + section, tracker, rel)
    else:
        harness_md.parent.mkdir(parents=True, exist_ok=True)
        _write(harness_md, section.lstrip("\n"), tracker, rel)
        files.append(rel)

    # Generate /health command
    health_rel = ".claude/commands/health.md"
    health_path = output_dir / ".claude" / "commands" / "health.md"
    health_path.parent.mkdir(parents=True, exist_ok=True)

    health_content = (
        "---\n"
        "description: Show session telemetry and project health metrics\n"
        "allowed-tools: Bash, Read\n"
        "---\n"
        "\n"
        "Read `.claude/telemetry.jsonl` and display aggregated metrics:\n"
        "\n"
        "1. Total sessions recorded\n"
        "2. Total estimated cost (sum of estimated_cost_usd)\n"
        "3. Average session duration (minutes)\n"
        "4. Average turns per session\n"
        "5. Most common model used\n"
        "6. Total compactions across all sessions\n"
        "7. Last 5 session summaries (date, duration, cost, compactions)\n"
        "\n"
        "Format as a clear summary table. If the file does not exist or is empty,\n"
        'report "No telemetry data yet. Complete a session to start collecting '
        'metrics."\n'
    )
    _write(health_path, health_content, tracker, health_rel)
    files.append(health_rel)

    return files


def _write(
    path: Path,
    content: str,
    tracker: FileTracker | None = None,
    rel_path: str | None = None,
) -> None:
    """Write content to a file, using tracker when available."""
    if tracker is not None and rel_path is not None:
        tracker.write_text(rel_path, content)
    else:
        path.write_text(content)
