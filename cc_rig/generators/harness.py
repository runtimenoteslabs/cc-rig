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
    if not any([h.task_tracking, h.budget_awareness, h.verification_gates, h.autonomy_loop]):
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
    if h.autonomy_loop:
        files.extend(_generate_b3(config, output_dir, tracker))

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

    # ── loop.sh — enhanced with config reading + progress ────────
    loop_content = (
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
        "\n"
        "# Read config from harness-config.json if available\n"
        "CONFIG_FILE=.claude/harness-config.json\n"
        'if [ -f "$CONFIG_FILE" ]; then\n'
        '    DEFAULT_MAX=$(grep -o \'"max_iterations": *[0-9]*\' "$CONFIG_FILE" '
        "| grep -o '[0-9]*' || echo " + str(h.max_iterations) + ")\n"
        '    CHECKPOINT=$(grep -o \'"checkpoint_commits": *[a-z]*\' "$CONFIG_FILE" '
        "| grep -oE 'true|false' || echo true)\n"
        "else\n"
        f"    DEFAULT_MAX={h.max_iterations}\n"
        "    CHECKPOINT=true\n"
        "fi\n"
        "\n"
        'MAX_ITERATIONS="${1:-$DEFAULT_MAX}"\n'
        "ITERATION=0\n"
        'PREV_TASK=""\n'
        "STUCK_COUNT=0\n"
        "\n"
        'echo ""\n'
        'echo "================================================"\n'
        'echo "  AUTONOMY LOOP - STARTING"\n'
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
        "    # Run tidy between iterations (entropy management)\n"
        "    if [ $ITERATION -gt 1 ] && [ -f .claude/hooks/init-sh.sh ]; then\n"
        "        bash .claude/hooks/init-sh.sh tidy 2>/dev/null"
        ' || echo "Tidy failed, continuing..."\n'
        "    fi\n"
        "\n"
        "    # Feed the prompt to Claude.\n"
        "    # --dangerously-skip-permissions is required for unattended operation.\n"
        "    cat PROMPT.md | claude --dangerously-skip-permissions || true\n"
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
        "\n"
        "    # Check for uncommitted changes if checkpoint_commits enabled\n"
        '    if [ "$CHECKPOINT" = "true" ]; then\n'
        "        if ! git diff --quiet 2>/dev/null ||"
        " ! git diff --cached --quiet 2>/dev/null; then\n"
        '            echo "WARNING: Uncommitted changes after iteration ${ITERATION}." >&2\n'
        "        fi\n"
        "    fi\n"
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
        'echo "================================================"\n'
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
