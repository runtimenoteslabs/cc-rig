"""Harness file generation for B1-B3 runtime discipline levels.

B0 = scaffold only (no harness files).
B1 = Harness-Lite: task tracking + budget awareness.
B2 = Harness-Standard: + verification gates + review notes.
B3 = Autonomy Loop: + autonomous iteration with safety rails.

The B3 autonomy loop implements the Ralph Wiggum technique by Geoffrey Huntley.
See: https://github.com/ghuntley/how-to-ralph-wiggum
"""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.project import ProjectConfig

# Harness levels in order of capability.
_LEVELS = ("none", "lite", "standard", "autonomy")


def generate_harness(
    config: ProjectConfig,
    output_dir: Path,
) -> list[str]:
    """Generate harness files based on config.harness.level.

    Returns list of relative file paths written.
    """
    level = config.harness.level
    if level == "none":
        return []

    files: list[str] = []

    # B1+ (lite and above)
    if _at_least(level, "lite"):
        files.extend(_generate_b1(config, output_dir))

    # B2+ (standard and above)
    if _at_least(level, "standard"):
        files.extend(_generate_b2(config, output_dir))

    # B3 (autonomy)
    if level == "autonomy":
        files.extend(_generate_b3(config, output_dir))

    return files


def _at_least(current: str, minimum: str) -> bool:
    """Check if current level is at least minimum level."""
    try:
        return _LEVELS.index(current) >= _LEVELS.index(minimum)
    except ValueError:
        return False


# ── B1: Harness-Lite ──────────────────────────────────────────────


def _generate_b1(config: ProjectConfig, output_dir: Path) -> list[str]:
    """Generate B1 files: task tracking + budget awareness."""
    files: list[str] = []

    # tasks/todo.md
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
    )
    files.append("tasks/todo.md")

    # agent_docs/budget-guide.md
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
        agent_docs / "budget-guide.md",
        "# Budget Awareness Guide\n"
        "\n"
        "This project uses budget-aware operation. Be mindful of\n"
        "token usage and prioritize high-impact work.\n"
        "\n"
        "## Budget Settings\n"
        "\n"
        f"{budget_line}"
        f"- **Warning threshold**: {warn_pct}% of budget\n"
        "\n"
        "## Guidelines\n"
        "\n"
        "1. **Plan before acting.** Read task list and prioritize.\n"
        "2. **Use subagents** for parallel work to stay within budget.\n"
        "3. **Checkpoint often.** Commit working code before moving on.\n"
        "4. **Stop cleanly.** When approaching budget, save state and stop.\n"
        "5. **Log progress.** Update tasks/todo.md and session-log.\n",
    )
    files.append("agent_docs/budget-guide.md")

    return files


# ── B2: Harness-Standard ──────────────────────────────────────────


def _generate_b2(config: ProjectConfig, output_dir: Path) -> list[str]:
    """Generate B2 files: verification gates + review notes."""
    files: list[str] = []
    agent_docs = output_dir / "agent_docs"
    agent_docs.mkdir(parents=True, exist_ok=True)

    tests_gate = "REQUIRED" if config.harness.require_tests_pass else "optional"
    lint_gate = "REQUIRED" if config.harness.require_lint_pass else "optional"
    test_cmd = config.test_cmd or "echo 'No test command configured'"
    lint_cmd = config.lint_cmd or "echo 'No linter configured'"

    # agent_docs/verification-gates.md
    _write(
        agent_docs / "verification-gates.md",
        "# Verification Gates\n"
        "\n"
        "These gates must pass before advancing to the next task.\n"
        "\n"
        "## Gates\n"
        "\n"
        f"| Gate | Status | Command |\n"
        f"|------|--------|---------|\n"
        f"| Tests | {tests_gate} | `{test_cmd}` |\n"
        f"| Lint | {lint_gate} | `{lint_cmd}` |\n"
        "\n"
        "## When to Verify\n"
        "\n"
        "- Before committing changes\n"
        "- Before marking a task as complete\n"
        "- After refactoring or significant edits\n"
        "- Before stopping a session\n"
        "\n"
        "## On Failure\n"
        "\n"
        "1. Fix the issue immediately if straightforward.\n"
        "2. If the fix is complex, log it in tasks/todo.md.\n"
        "3. Never skip a REQUIRED gate.\n",
    )
    files.append("agent_docs/verification-gates.md")

    # agent_docs/review-notes.md
    _write(
        agent_docs / "review-notes.md",
        "# Review Notes\n"
        "\n"
        "Capture learnings from code review and verification.\n"
        "\n"
        "## Format\n"
        "\n"
        "`[YYYY-MM-DD] Review: <what was reviewed> — Learning: <insight>`\n"
        "\n"
        "<!-- Entries below -->\n",
    )
    files.append("agent_docs/review-notes.md")

    return files


# ── B3: Autonomy Loop ─────────────────────────────────────────────


def _generate_b3(config: ProjectConfig, output_dir: Path) -> list[str]:
    """Generate B3 files: autonomy loop + safety rails."""
    files: list[str] = []
    agent_docs = output_dir / "agent_docs"
    agent_docs.mkdir(parents=True, exist_ok=True)

    h = config.harness
    blocked_action = "Stop and save state" if h.if_blocked == "stop" else "Skip to next task"
    checkpoint_str = "Yes — commit after each task" if h.checkpoint_commits else "No"

    # agent_docs/autonomy-loop.md
    _write(
        agent_docs / "autonomy-loop.md",
        "# Autonomy Loop\n"
        "\n"
        "================================================\n"
        "  WARNING: AUTONOMOUS OPERATION MODE\n"
        "  Claude will iterate through tasks without\n"
        "  human intervention. Safety rails are active.\n"
        "================================================\n"
        "\n"
        "Based on the Ralph Wiggum technique by Geoffrey Huntley.\n"
        "See: https://github.com/ghuntley/how-to-ralph-wiggum\n"
        "\n"
        "## How It Works\n"
        "\n"
        "The autonomy loop uses an external bash script (`loop.sh`) that\n"
        "feeds `PROMPT.md` to Claude in a loop. Each iteration:\n"
        "\n"
        "1. Claude starts with fresh context (no leftover state).\n"
        "2. Reads `PROMPT.md` for instructions.\n"
        "3. Reads `tasks/todo.md` and picks the highest-priority incomplete task.\n"
        "4. Implements the task.\n"
        "5. Runs verification gates (tests + lint).\n"
        "6. If gates pass, checkpoint commit and mark task done.\n"
        "7. If gates fail, attempt fix (up to 3 retries).\n"
        "8. If blocked, " + blocked_action.lower() + ".\n"
        "9. Claude exits. The loop restarts with fresh context.\n"
        "\n"
        "The `tasks/todo.md` file persists between iterations — it is the\n"
        "sole mechanism for continuation. No state is carried between loops.\n"
        "\n"
        "## Running the Loop\n"
        "\n"
        "```bash\n"
        f"./loop.sh              # Run with default max ({h.max_iterations} iterations)\n"
        "./loop.sh 50           # Override max iterations\n"
        "```\n"
        "\n"
        "## Safety Rails\n"
        "\n"
        f"| Setting | Value |\n"
        f"|---------|-------|\n"
        f"| Max iterations | {h.max_iterations} |\n"
        f"| Checkpoint commits | {checkpoint_str} |\n"
        f"| If blocked | {blocked_action} |\n"
        f"| Tests required | {'Yes' if h.require_tests_pass else 'No'} |\n"
        f"| Lint required | {'Yes' if h.require_lint_pass else 'No'} |\n"
        "\n"
        "## Emergency Stop\n"
        "\n"
        "Press Ctrl+C at any time. The current Claude session will finish\n"
        "its current operation and the loop will stop.\n",
    )
    files.append("agent_docs/autonomy-loop.md")

    # PROMPT.md — the prompt file fed to Claude each iteration
    test_cmd = config.test_cmd or "echo 'No test command configured'"
    lint_cmd = config.lint_cmd or "echo 'No lint command configured'"

    verify_steps = ""
    if h.require_tests_pass:
        verify_steps += f"   - Run tests: `{test_cmd}`\n"
    if h.require_lint_pass:
        verify_steps += f"   - Run lint: `{lint_cmd}`\n"
    if not verify_steps:
        verify_steps = "   - No verification gates configured.\n"

    blocked_instruction = (
        "log the blocker in tasks/todo.md and EXIT"
        if h.if_blocked == "stop"
        else "log the blocker, skip to the next incomplete task"
    )

    _write(
        output_dir / "PROMPT.md",
        "# Autonomy Loop — Iteration Prompt\n"
        "\n"
        "You are operating in autonomous mode. Complete exactly ONE task\n"
        "per iteration, then exit so the loop restarts with fresh context.\n"
        "\n"
        "## Your workflow:\n"
        "\n"
        "1. Read `tasks/todo.md` — pick the highest-priority incomplete task.\n"
        "2. Read relevant code and context for that task.\n"
        "3. Implement the task.\n"
        "4. Verify your work:\n"
        f"{verify_steps}"
        "5. If verification passes:\n"
        "   - Commit with a clear message describing what you did and why.\n"
        "   - Mark the task `[x]` in `tasks/todo.md`.\n"
        "6. If verification fails:\n"
        "   - Fix the issue (up to 3 attempts).\n"
        "   - If you can't fix it, log the failure in `tasks/todo.md`.\n"
        "7. If blocked:\n"
        f"   - {blocked_instruction}.\n"
        "8. EXIT when done with this one task.\n"
        "\n"
        "## Rules\n"
        "\n"
        "- Complete exactly ONE task per iteration.\n"
        "- Always commit working code before exiting.\n"
        "- Always update `tasks/todo.md` to reflect current state.\n"
        "- If all tasks are done, exit with message: ALL TASKS COMPLETE.\n"
        "- Do NOT carry assumptions from previous iterations — read fresh.\n",
    )
    files.append("PROMPT.md")

    # loop.sh — the external bash loop that drives autonomous iteration
    _write(
        output_dir / "loop.sh",
        "#!/usr/bin/env bash\n"
        "# Autonomy loop — based on the Ralph Wiggum technique by Geoffrey Huntley.\n"
        "# https://github.com/ghuntley/how-to-ralph-wiggum\n"
        "#\n"
        "# Usage: ./loop.sh [max_iterations]\n"
        "#\n"
        "# WARNING: This runs Claude in autonomous mode without permission prompts.\n"
        "# Recommended: run inside a Docker container or sandboxed environment.\n"
        "# See: https://docs.anthropic.com/en/docs/claude-code/security\n"
        "\n"
        "set -euo pipefail\n"
        "\n"
        f'MAX_ITERATIONS="${{1:-{h.max_iterations}}}"\n'
        "ITERATION=0\n"
        "\n"
        'echo ""\n'
        'echo "================================================"\n'
        'echo "  AUTONOMY LOOP — STARTING"\n'
        'echo "  Max iterations: ${MAX_ITERATIONS}"\n'
        'echo "  Press Ctrl+C to stop at any time."\n'
        'echo "================================================"\n'
        'echo ""\n'
        "\n"
        "while [ $ITERATION -lt $MAX_ITERATIONS ]; do\n"
        "    ITERATION=$((ITERATION + 1))\n"
        '    echo ""\n'
        '    echo "--- Iteration ${ITERATION}/${MAX_ITERATIONS} ---"\n'
        '    echo ""\n'
        "\n"
        "    # Feed the prompt to Claude.\n"
        "    # --dangerously-skip-permissions is required for unattended operation.\n"
        "    cat PROMPT.md | claude --dangerously-skip-permissions || true\n"
        "\n"
        "    # Check if all tasks are done.\n"
        "    if [ -f tasks/todo.md ]; then\n"
        "        if ! grep -q '\\- \\[ \\]' tasks/todo.md; then\n"
        '            echo ""\n'
        '            echo "================================================"\n'
        '            echo "  ALL TASKS COMPLETE"\n'
        '            echo "  Finished after ${ITERATION} iterations."\n'
        '            echo "================================================"\n'
        "            exit 0\n"
        "        fi\n"
        "    fi\n"
        "done\n"
        "\n"
        'echo ""\n'
        'echo "================================================"\n'
        'echo "  MAX ITERATIONS REACHED (${MAX_ITERATIONS})"\n'
        'echo "  Check tasks/todo.md for remaining work."\n'
        'echo "================================================"\n',
    )
    # Make loop.sh executable
    (output_dir / "loop.sh").chmod(0o755)
    files.append("loop.sh")

    # .claude/harness-config.json — machine-readable safety config
    claude_dir = output_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    import json

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
    config_path = claude_dir / "harness-config.json"
    config_path.write_text(json.dumps(safety_config, indent=2) + "\n")
    files.append(".claude/harness-config.json")

    return files


# ── Helpers ────────────────────────────────────────────────────────


def _write(path: Path, content: str) -> None:
    """Write content to a file."""
    path.write_text(content)
