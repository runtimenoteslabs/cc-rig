"""Generate .claude/settings.json and hook scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker

# Shell metacharacters that indicate injection risk in tool commands.
# Legitimate commands (e.g. "ruff check", "npx prettier --write") never need these.
_SHELL_INJECTION_RE = re.compile(r"[;|&`$><]|\.\./")


# ── Hook metadata registry ─────────────────────────────────────────
# Maps hook name -> (event, matcher, hook_type)
# hook_type is "command", "prompt", or "agent".


_HOOK_REGISTRY: dict[str, tuple[str, str, str]] = {
    "format": ("PostToolUse", "Write|Edit", "command"),
    "lint": ("PreToolUse", "Bash", "command"),
    "typecheck": ("PreToolUse", "Bash", "command"),
    "block-rm-rf": ("PreToolUse", "Bash", "command"),
    "block-env": ("PreToolUse", "Write|Edit", "command"),
    "block-main": ("PreToolUse", "Bash", "command"),
    "session-context": ("SessionStart", "", "command"),
    "stop-validator": ("Stop", "", "command"),
    "memory-stop": ("Stop", "", "prompt"),
    "memory-precompact": ("PreCompact", "", "command"),
    "push-review": ("PreToolUse", "Bash", "prompt"),
    "subagent-review": ("SubagentStop", "", "agent"),
    "commit-message": ("PreToolUse", "Bash", "prompt"),
    "doc-review": ("Stop", "", "agent"),
    "budget-reminder": ("Stop", "", "command"),
    "session-tasks": ("SessionStart", "", "command"),
    "commit-gate": ("PreToolUse", "Bash", "command"),
}


# ── Prompt texts for prompt-type hooks ─────────────────────────────


_PROMPT_TEXTS: dict[str, str] = {
    "session-context": (
        "Read agent_docs/architecture.md, agent_docs/conventions.md, "
        "and agent_docs/testing.md to load project context. "
        "Auto-memory is loaded automatically. "
        "If memory/ exists, read memory/decisions.md and "
        "memory/session-log.md for recent team context."
    ),
    "memory-stop": (
        "Review the conversation for team-relevant decisions, patterns, "
        "gotchas, or learnings worth saving to memory/ files. "
        "If Claude has ALREADY written these learnings to memory/ files "
        "(auto-memory MEMORY.md or team memory files) during this "
        "conversation, respond with {\"ok\": true}. Only respond with "
        "{\"ok\": false, \"reason\": \"Save to memory/ before stopping: "
        "<brief list>\"} if there are notable items that have NOT yet "
        "been saved. Personal notes go in auto-memory, not here."
    ),
    "memory-precompact": (
        "Context is about to be compacted. Save any key decisions, "
        "patterns, or learnings to the appropriate team memory files "
        "(memory/) before context is lost. Use one-line entries."
    ),
    "push-review": (
        "Before pushing, review the changes being pushed. "
        "Summarize what is included in this push and confirm "
        "all tests pass and no sensitive files are included."
    ),
    "subagent-review": (
        "Review the subagent's output for quality. Check that "
        "the work is complete, tests pass, and the code follows "
        "project conventions. Flag any concerns."
    ),
    "commit-message": (
        "Ensure the commit message is descriptive and follows "
        "conventional commit format. The message should explain "
        "WHY the change was made, not just WHAT changed."
    ),
    "doc-review": (
        "Before stopping, check if documentation needs updating. "
        "Review README, API docs, and agent_docs/ for accuracy "
        "against the changes made this session. Flag any outdated "
        "sections."
    ),
}


# ── Default permission rules ───────────────────────────────────────

_DEFAULT_PERMISSIONS = {
    "allow": [
        "Read",
        "Glob",
        "Grep",
        "Edit",
        "Write",
        "NotebookEdit",
    ],
    "deny": [
        "Bash(rm -rf /)",
        "Bash(rm -rf ~)",
    ],
}

_PERMISSIVE_ADDITIONS = [
    "Bash",
    "WebSearch",
    "WebFetch",
    "Task",
]


# ── Public API ─────────────────────────────────────────────────────


def generate_settings(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate .claude/settings.json with hooks, and hook shell scripts.

    Returns list of relative file paths written.
    """
    files_written: list[str] = []

    claude_dir = output_dir / ".claude"
    hooks_dir = claude_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Build the settings structure
    settings: dict[str, Any] = {}

    # Permissions
    settings["permissions"] = _build_permissions(config)

    # Hooks
    hooks_by_event: dict[str, list[dict[str, Any]]] = {}

    # Auto-add harness hooks based on level
    active_hooks = list(config.hooks)
    harness_level = config.harness.level
    if harness_level != "none":
        # B1+: budget-reminder + session-tasks
        if "budget-reminder" not in active_hooks:
            active_hooks.append("budget-reminder")
        if "session-tasks" not in active_hooks:
            active_hooks.append("session-tasks")
    if harness_level in ("standard", "autonomy"):
        # B2+: commit-gate
        if "commit-gate" not in active_hooks:
            active_hooks.append("commit-gate")

    for hook_name in active_hooks:
        meta = _HOOK_REGISTRY.get(hook_name)
        if meta is None:
            continue

        event, matcher, hook_type = meta

        if hook_type == "command":
            # Generate the shell script
            script = _generate_hook_script(hook_name, config)
            rel = f".claude/hooks/{hook_name}.sh"
            if tracker is not None:
                tracker.write_text(rel, script)
                tracker.chmod(rel, 0o755)
            else:
                script_path = hooks_dir / f"{hook_name}.sh"
                script_path.write_text(script)
                script_path.chmod(0o755)
            files_written.append(rel)

            hook_entry: dict[str, Any] = {
                "type": "command",
                "command": f"bash .claude/hooks/{hook_name}.sh",
            }
        elif hook_type == "agent":
            prompt_text = _PROMPT_TEXTS.get(hook_name, "")
            hook_entry = {
                "type": "agent",
                "prompt": prompt_text,
            }
        else:
            prompt_text = _PROMPT_TEXTS.get(hook_name, "")
            hook_entry = {
                "type": "prompt",
                "prompt": prompt_text,
            }

        event_entry: dict[str, Any] = {
            "hooks": [hook_entry],
        }
        if matcher:
            event_entry["matcher"] = matcher

        hooks_by_event.setdefault(event, []).append(event_entry)

    if hooks_by_event:
        settings["hooks"] = hooks_by_event

    # Write settings.json
    settings_content = json.dumps(settings, indent=2) + "\n"
    if tracker is not None:
        tracker.write_text(".claude/settings.json", settings_content)
    else:
        settings_path = claude_dir / "settings.json"
        settings_path.write_text(settings_content)
    files_written.append(".claude/settings.json")

    return files_written


# ── Internal helpers ───────────────────────────────────────────────


def _build_permissions(config: ProjectConfig) -> dict[str, list[str]]:
    """Build permission rules based on config.permission_mode."""
    perms: dict[str, list[str]] = {
        "allow": list(_DEFAULT_PERMISSIONS["allow"]),
        "deny": list(_DEFAULT_PERMISSIONS["deny"]),
    }
    if config.permission_mode == "permissive":
        for tool in _PERMISSIVE_ADDITIONS:
            if tool not in perms["allow"]:
                perms["allow"].append(tool)
    return perms


def _generate_hook_script(
    hook_name: str,
    config: ProjectConfig,
) -> str:
    """Generate a portable bash hook script for a command-type hook."""
    generators: dict[str, Callable[[ProjectConfig], str]] = {
        "format": _script_format,
        "lint": _script_lint,
        "typecheck": _script_typecheck,
        "block-rm-rf": _script_block_rm_rf,
        "block-env": _script_block_env,
        "block-main": _script_block_main,
        "session-context": _script_session_context,
        "stop-validator": _script_stop_validator,
        "memory-precompact": _script_memory_precompact,
        "budget-reminder": _script_budget_reminder,
        "session-tasks": _script_session_tasks,
        "commit-gate": _script_commit_gate,
    }
    generator = generators.get(hook_name)
    if generator is None:
        return _script_noop(hook_name)
    return generator(config)


# ── Hook script generators ─────────────────────────────────────────


def _safe_cmd(cmd: str, fallback: str = "echo 'No command configured'") -> str:
    """Return *cmd* if it looks safe to embed in a shell script.

    Rejects commands containing shell metacharacters (`;`, `|`, `&`,
    backticks, `$`, redirects, `../`) that could enable injection when
    the command string originates from an untrusted `.cc-rig.json`.
    Falls back to a harmless echo command on rejection.
    """
    if not cmd:
        return fallback
    if _SHELL_INJECTION_RE.search(cmd):
        return fallback
    return cmd


def _script_format(config: ProjectConfig) -> str:
    raw_cmd = config.format_cmd or ""
    # Strip trailing directory arg (e.g., "ruff format ." → "ruff format")
    single_cmd = raw_cmd.rstrip()
    if single_cmd.endswith(" ."):
        single_cmd = single_cmd[:-2]
    single_cmd = _safe_cmd(single_cmd, "echo 'No formatter configured'")
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: format — auto-format after file write\n"
        "# Event: PostToolUse (Write|Edit)\n"
        "set -euo pipefail\n"
        "\n"
        "# Extract file path from CC hook JSON input on stdin\n"
        'FILE=$(cat | grep -oE \'"file_path" *: *"[^"]*"\''
        " | head -1 | cut -d'\"' -f4 2>/dev/null || true)\n"
        "\n"
        'if [ -n "$FILE" ] && [ -f "$FILE" ]; then\n'
        f'  {single_cmd} "$FILE" 2>/dev/null || true\n'
        "fi\n"
        "\n"
        "exit 0\n"
    )


def _script_lint(config: ProjectConfig) -> str:
    lint_cmd = _safe_cmd(config.lint_cmd, "echo 'No linter configured'")
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: lint — lint before git commit\n"
        "# Event: PreToolUse (Bash matching git commit)\n"
        "set -euo pipefail\n"
        "\n"
        "# Read the tool input from stdin\n"
        'INPUT=$(cat 2>/dev/null || echo "")\n'
        "\n"
        "# Only run on git commit commands\n"
        'if echo "$INPUT" | grep -q "git commit"; then\n'
        f"  {lint_cmd}\n"
        "  exit $?\n"
        "fi\n"
        "\n"
        "exit 0\n"
    )


def _script_typecheck(config: ProjectConfig) -> str:
    tc_cmd = _safe_cmd(config.typecheck_cmd, "echo 'No typechecker configured'")
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: typecheck — typecheck before git commit\n"
        "# Event: PreToolUse (Bash matching git commit)\n"
        "set -euo pipefail\n"
        "\n"
        "# Read the tool input from stdin\n"
        'INPUT=$(cat 2>/dev/null || echo "")\n'
        "\n"
        "# Only run on git commit commands\n"
        'if echo "$INPUT" | grep -q "git commit"; then\n'
        f"  {tc_cmd}\n"
        "  exit $?\n"
        "fi\n"
        "\n"
        "exit 0\n"
    )


def _script_block_rm_rf(config: ProjectConfig) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: block-rm-rf — block dangerous commands\n"
        "# Event: PreToolUse (Bash)\n"
        "# Exit 2 = block the tool use\n"
        "set -euo pipefail\n"
        "\n"
        "# Read the tool input from stdin\n"
        'INPUT=$(cat 2>/dev/null || echo "")\n'
        "\n"
        "# Block dangerous rm commands\n"
        'if echo "$INPUT" | grep -qE '
        "'rm\\s+(-[a-zA-Z]*)?r[a-zA-Z]*f[a-zA-Z]*\\s+/($|\\s)'; then\n"
        '  echo "BLOCKED: rm -rf / is not allowed" >&2\n'
        "  exit 2\n"
        "fi\n"
        "\n"
        "# Block rm -rf on home directory\n"
        'if echo "$INPUT" | grep -qE '
        "'rm\\s+(-[a-zA-Z]*)?r[a-zA-Z]*f[a-zA-Z]*\\s+~($|/)'; then\n"
        '  echo "BLOCKED: rm -rf ~ is not allowed" >&2\n'
        "  exit 2\n"
        "fi\n"
        "\n"
        "# Block DROP TABLE\n"
        'if echo "$INPUT" | grep -qiE '
        "'DROP\\s+TABLE|DROP\\s+DATABASE'; then\n"
        '  echo "BLOCKED: DROP TABLE/DATABASE is not allowed" >&2\n'
        "  exit 2\n"
        "fi\n"
        "\n"
        "# Block disk overwrite\n"
        "if echo \"$INPUT\" | grep -qE '> /dev/sd[a-z]'; then\n"
        '  echo "BLOCKED: disk overwrite is not allowed" >&2\n'
        "  exit 2\n"
        "fi\n"
        "\n"
        "exit 0\n"
    )


def _script_block_env(config: ProjectConfig) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: block-env — block writing sensitive files\n"
        "# Event: PreToolUse (Write|Edit)\n"
        "# Exit 2 = block the tool use\n"
        "set -euo pipefail\n"
        "\n"
        "# Extract file_path from JSON input\n"
        "INPUT=$(cat 2>/dev/null || echo '')\n"
        'FILE_PATH=$(echo "$INPUT" | grep -oE \'"file_path" *: *"[^"]*"\''
        " | head -1 | cut -d'\"' -f4 2>/dev/null || true)\n"
        "\n"
        '[ -z "$FILE_PATH" ] && exit 0\n'
        "\n"
        "# Check for sensitive file patterns in the path only\n"
        "BLOCKED_PATTERNS=(\n"
        '  "\\.env$"\n'
        '  "\\.env\\.local$"\n'
        '  "\\.env\\.production$"\n'
        '  "credentials"\n'
        '  "secrets"\n'
        '  "\\.pem$"\n'
        '  "\\.key$"\n'
        '  "id_rsa"\n'
        '  "id_ed25519"\n'
        ")\n"
        "\n"
        'for pattern in "${BLOCKED_PATTERNS[@]}"; do\n'
        '  if echo "$FILE_PATH" | grep -qiE "$pattern"; then\n'
        '    echo "BLOCKED: writing to sensitive file '
        'matching $pattern" >&2\n'
        "    exit 2\n"
        "  fi\n"
        "done\n"
        "\n"
        "exit 0\n"
    )


def _script_block_main(config: ProjectConfig) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: block-main — block push to main/master\n"
        "# Event: PreToolUse (Bash matching git push)\n"
        "# Exit 2 = block the tool use\n"
        "set -euo pipefail\n"
        "\n"
        "# Extract command from JSON input\n"
        "INPUT=$(cat 2>/dev/null || echo '')\n"
        'CMD=$(echo "$INPUT" | grep -oE \'"command" *: *"[^"]*"\''
        " | head -1 | cut -d'\"' -f4 2>/dev/null || true)\n"
        "\n"
        "# Only check git push commands\n"
        'if echo "$CMD" | grep -q "git push"; then\n'
        "  # Block push to main or master\n"
        '  if echo "$CMD" | grep -qE '
        "'git push.*(main|master)($|\\s)'; then\n"
        '    echo "BLOCKED: direct push to main/master. '
        'Use a feature branch." >&2\n'
        "    exit 2\n"
        "  fi\n"
        "\n"
        "  # Also block if current branch is main/master\n"
        "  CURRENT_BRANCH=$(git branch --show-current 2>/dev/null"
        ' || echo "")\n'
        '  if [ "$CURRENT_BRANCH" = "main" ] || '
        '[ "$CURRENT_BRANCH" = "master" ]; then\n'
        "    # Allow if pushing to a different remote branch\n"
        '    if ! echo "$CMD" | grep -qE '
        "'git push.*origin\\s+[a-zA-Z]'; then\n"
        '      echo "BLOCKED: pushing from main/master branch. '
        'Create a feature branch." >&2\n'
        "      exit 2\n"
        "    fi\n"
        "  fi\n"
        "fi\n"
        "\n"
        "exit 0\n"
    )


def _script_stop_validator(config: ProjectConfig) -> str:
    test_cmd = _safe_cmd(config.test_cmd, "echo 'No test command configured'")
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: stop-validator — check work before stopping\n"
        "# Event: Stop\n"
        "set -euo pipefail\n"
        "\n"
        "# Check for uncommitted changes\n"
        "if git diff --quiet 2>/dev/null && "
        "git diff --cached --quiet 2>/dev/null; then\n"
        '  echo "All changes committed."\n'
        "else\n"
        '  echo "WARNING: There are uncommitted changes."\n'
        "fi\n"
        "\n"
        "# Remind about tests — don't run the full suite on every stop\n"
        f'echo "Reminder: run \\"{test_cmd}\\" before committing '
        'if you have not already."\n'
        "\n"
        "exit 0\n"
    )


def _script_session_context(config: ProjectConfig) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: session-context — print project context at session start\n"
        "# Event: SessionStart\n"
        "set -euo pipefail\n"
        "\n"
        "echo 'Project context files:'\n"
        "for f in agent_docs/architecture.md agent_docs/conventions.md "
        "agent_docs/testing.md agent_docs/deployment.md; do\n"
        '  [ -f "$f" ] && echo "  $f"\n'
        "done\n"
        "\n"
        'if [ -d "memory" ]; then\n'
        "  echo 'Team memory files:'\n"
        "  for f in memory/decisions.md memory/session-log.md; do\n"
        '    [ -f "$f" ] && echo "  $f"\n'
        "  done\n"
        "fi\n"
        "\n"
        "exit 0\n"
    )


def _script_memory_precompact(config: ProjectConfig) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: memory-precompact — reminder before context compaction\n"
        "# Event: PreCompact\n"
        "set -euo pipefail\n"
        "\n"
        'echo "Context is about to be compacted."\n'
        'echo "Save key decisions and patterns to memory/ files."\n'
        "\n"
        "exit 0\n"
    )


def _script_budget_reminder(config: ProjectConfig) -> str:
    h = config.harness
    if h.budget_per_run_tokens is not None:
        budget_line = f"BUDGET={h.budget_per_run_tokens}"
        warn_line = f"WARN_AT=$(( BUDGET * {h.budget_warn_at_percent} / 100 ))"
        display = (
            '  echo "Budget: $BUDGET tokens '
            f'(warn at {h.budget_warn_at_percent}%: $WARN_AT tokens)"\n'
        )
    else:
        budget_line = 'BUDGET="unlimited"'
        warn_line = ""
        display = '  echo "Budget: unlimited"\n'
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: budget-reminder — display budget status on stop\n"
        "# Event: Stop\n"
        "set -euo pipefail\n"
        "\n"
        "# Read budget from harness config if available\n"
        f"{budget_line}\n" + (f"{warn_line}\n" if warn_line else "") + "\n"
        'echo ""\n'
        'echo "=== Budget Reminder ==="\n'
        + display
        + '  echo "Review token usage for this session."\n'
        'echo "======================="\n'
        'echo ""\n'
        "\n"
        "exit 0\n"
    )


def _script_session_tasks(config: ProjectConfig) -> str:
    """Generate session-tasks hook: print task summary at session start."""
    lines = [
        "#!/usr/bin/env bash",
        "# cc-rig hook: session-tasks — print task summary at session start",
        "# Event: SessionStart",
        "set -euo pipefail",
        "",
        "# Count open and done tasks from tasks/todo.md",
        'if [ -f "tasks/todo.md" ]; then',
        '  OPEN=$(grep -c "^- \\[ \\]" tasks/todo.md 2>/dev/null || echo 0)',
        '  DONE=$(grep -c "^- \\[x\\]" tasks/todo.md 2>/dev/null || echo 0)',
        '  echo "Tasks: ${OPEN} open, ${DONE} done" >&2',
    ]
    if config.features.gtd:
        lines += [
            '  if [ -f "tasks/inbox.md" ]; then',
            '    INBOX=$(grep -c "^- " tasks/inbox.md 2>/dev/null || echo 0)',
            '    echo "Inbox: ${INBOX} unprocessed" >&2',
            "  fi",
        ]
    if config.features.memory:
        lines += [
            '  if [ -d "memory" ]; then',
            '    MLINES=$(cat memory/*.md 2>/dev/null | wc -l || echo 0)',
            '    echo "Memory: ${MLINES} lines" >&2',
            "  fi",
        ]
    lines += [
        "else",
        '  echo "No tasks/todo.md found." >&2',
        "fi",
        "",
        "exit 0",
    ]
    return "\n".join(lines) + "\n"


def _script_commit_gate(config: ProjectConfig) -> str:
    """Generate commit-gate hook: lint enforcement + test reminder on git commit."""
    lint_cmd = _safe_cmd(config.lint_cmd, "echo 'No linter configured'")
    lines = [
        "#!/usr/bin/env bash",
        "# cc-rig hook: commit-gate — lint gate + test reminder before commit",
        "# Event: PreToolUse (Bash)",
        "# Exit 2 = block the tool use",
        "set -euo pipefail",
        "",
        "# Read the tool input from stdin",
        'INPUT=$(cat 2>/dev/null || echo "")',
        "",
        "# Only fire on git commit commands",
        'if ! echo "$INPUT" | grep -q "git commit"; then',
        "  exit 0",
        "fi",
        "",
        "# Always run lint — block (exit 2) on failure",
        f"if ! {lint_cmd}; then",
        '  echo "Commit gate: lint failed. Fix lint errors before committing." >&2',
        "  exit 2",
        "fi",
        "",
        "# Lint passed — prompt about tests",
        'echo "Commit gate: lint passed. Did you run tests? '
        'If not, run ./init-sh.sh verify first." >&2',
        "",
        "exit 0",
    ]
    return "\n".join(lines) + "\n"


def _script_noop(hook_name: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        f"# cc-rig hook: {hook_name}\n"
        "# No-op — hook has no command-type action.\n"
        "exit 0\n"
    )
