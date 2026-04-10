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
_SHELL_INJECTION_RE = re.compile(r"[;|&`$><\n\r]|\.\./")

# Workflow → CC effort level mapping (V2.1)
_WORKFLOW_EFFORT: dict[str, str] = {
    "speedrun": "low",
    "standard": "medium",
    "gstack": "medium",
    "aihero": "medium",
    "spec-driven": "high",
    "superpowers": "high",
    "gtd": "medium",
    "gtd-lite": "medium",
    "verify-heavy": "high",
}


# ── Hook metadata registry ─────────────────────────────────────────
# Maps hook name -> (event, matcher, hook_type, if_condition)
# hook_type is "command", "prompt", or "agent".
# if_condition uses CC permission rule syntax (v2.1.85+), empty = no condition.


_HOOK_REGISTRY: dict[str, tuple[str, str, str, str]] = {
    "format": ("PostToolUse", "Write|Edit", "command", ""),
    "lint": ("PreToolUse", "Bash", "command", "Bash(git commit*)"),
    "typecheck": ("PreToolUse", "Bash", "command", "Bash(git commit*)"),
    "block-rm-rf": ("PreToolUse", "Bash", "command", "Bash(rm *)"),
    "block-env": ("PreToolUse", "Write|Edit", "command", ""),
    "block-main": ("PreToolUse", "Bash", "command", "Bash(git push*)"),
    "session-context": ("SessionStart", "", "command", ""),
    "stop-validator": ("Stop", "", "command", ""),
    "memory-precompact": ("PreCompact", "", "command", ""),
    "push-review": ("PreToolUse", "Bash", "command", "Bash(git push*)"),
    "subagent-review": ("SubagentStop", "", "agent", ""),
    "commit-message": ("PreToolUse", "Bash", "command", "Bash(git commit*)"),
    "doc-review": ("Stop", "", "agent", ""),
    "budget-reminder": ("Stop", "", "command", ""),
    "session-tasks": ("SessionStart", "", "command", ""),
    "commit-gate": ("PreToolUse", "Bash", "command", "Bash(git commit*)"),
    "context-survival": ("PreCompact", "", "command", ""),
    "session-telemetry": ("Stop", "", "command", ""),
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
    "memory-precompact": (
        "Context is about to be compacted. Save any key decisions, "
        "patterns, or learnings to the appropriate team memory files "
        "(memory/) before context is lost. Use one-line entries."
    ),
    "push-review": (
        "Before pushing, review the changes being pushed. "
        "Summarize what is included and confirm all tests pass "
        "and no sensitive files are included. Output ONLY raw JSON "
        "with no other text and no markdown formatting:\\n"
        '{"ok": true}\\n'
        "If there are issues, output ONLY:\\n"
        '{"ok": false, "reason": "brief description of issues"}'
    ),
    "subagent-review": (
        "Review the subagent's output for quality. Check that "
        "the work is complete, tests pass, and the code follows "
        "project conventions. Flag any concerns."
    ),
    "commit-message": (
        "Ensure the commit message is descriptive and explains "
        "WHY the change was made, not just WHAT changed. Output "
        "ONLY raw JSON with no other text and no markdown formatting:\\n"
        '{"ok": true}\\n'
        "If the message needs improvement, output ONLY:\\n"
        '{"ok": false, "reason": "brief suggestion"}'
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

    # Auto-add harness hooks based on feature flags
    active_hooks = list(config.hooks)
    h = config.harness
    if h.budget_awareness and "budget-reminder" not in active_hooks:
        active_hooks.append("budget-reminder")
    if h.task_tracking and "session-tasks" not in active_hooks:
        active_hooks.append("session-tasks")
    if h.verification_gates and "commit-gate" not in active_hooks:
        active_hooks.append("commit-gate")
    if h.context_awareness and "context-survival" not in active_hooks:
        active_hooks.append("context-survival")
    if h.session_telemetry and "session-telemetry" not in active_hooks:
        active_hooks.append("session-telemetry")

    for hook_name in active_hooks:
        meta = _HOOK_REGISTRY.get(hook_name)
        if meta is None:
            continue

        event, matcher, hook_type, if_condition = meta

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

        if if_condition:
            hook_entry["if"] = if_condition

        event_entry: dict[str, Any] = {
            "hooks": [hook_entry],
        }
        if matcher:
            event_entry["matcher"] = matcher

        hooks_by_event.setdefault(event, []).append(event_entry)

    if hooks_by_event:
        settings["hooks"] = hooks_by_event

    # Plugins
    if config.recommended_plugins:
        enabled_plugins: dict[str, bool] = {}
        for plugin in config.recommended_plugins:
            key = f"{plugin.name}@{plugin.marketplace}"
            enabled_plugins[key] = True
        settings["enabledPlugins"] = enabled_plugins

    # Effort level per workflow (V2.1)
    effort = _WORKFLOW_EFFORT.get(config.workflow, "medium")
    settings["effortLevel"] = effort

    # Suppress built-in git instructions for high-rigor workflows (V2.1)
    # These workflows have comprehensive guardrails in CLAUDE.md already.
    if config.workflow in ("superpowers", "verify-heavy", "spec-driven"):
        settings["includeGitInstructions"] = False

    # Auto mode (V2.3, CC v2.1.89+)
    if config.permission_mode == "auto":
        settings.setdefault("permissions", {})["defaultMode"] = "auto"
        auto_mode: dict[str, Any] = {
            "environment": [f"Trusted local development ({config.framework})"],
            "allow": ["Installing packages from lockfile"],
        }
        if config.workflow in ("superpowers", "verify-heavy", "spec-driven"):
            auto_mode["soft_deny"] = [
                "Production deploys without approval",
                "Force push to any branch",
            ]
        settings["autoMode"] = auto_mode

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
    if config.permission_mode in ("permissive", "auto"):
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
        "context-survival": _script_context_survival,
        "session-telemetry": _script_session_telemetry,
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


def _script_check_on_commit(tool_name: str, cmd: str) -> str:
    """Generate a hook script that runs a check tool before git commit.

    Output hygiene: suppress stdout on success (exit 0 silently).
    On failure, truncate to first 20 lines to limit token drain.
    """
    safe_cmd = _safe_cmd(cmd, f"echo 'No {tool_name} configured'")
    return (
        "#!/usr/bin/env bash\n"
        f"# cc-rig hook: {tool_name} — {tool_name} before git commit\n"
        "# Event: PreToolUse (Bash matching git commit)\n"
        "set -euo pipefail\n"
        "\n"
        "# Read the tool input from stdin\n"
        'INPUT=$(cat 2>/dev/null || echo "")\n'
        "\n"
        "# Only run on git commit commands\n"
        'if echo "$INPUT" | grep -q "git commit"; then\n'
        f"  OUTPUT=$({safe_cmd} 2>&1) && exit 0\n"
        "  RC=$?\n"
        '  LINES=$(echo "$OUTPUT" | wc -l)\n'
        '  if [ "$LINES" -gt 20 ]; then\n'
        '    echo "$OUTPUT" | head -20\n'
        f'    echo "... ($LINES total lines, showing first 20)"\n'
        "  else\n"
        '    echo "$OUTPUT"\n'
        "  fi\n"
        "  exit $RC\n"
        "fi\n"
        "\n"
        "exit 0\n"
    )


def _script_lint(config: ProjectConfig) -> str:
    return _script_check_on_commit("lint", config.lint_cmd)


def _script_typecheck(config: ProjectConfig) -> str:
    return _script_check_on_commit("typecheck", config.typecheck_cmd)


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
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: stop-validator — check work before stopping\n"
        "# Event: Stop\n"
        "set -euo pipefail\n"
        "\n"
        "# Only warn if there are uncommitted changes\n"
        "if ! git diff --quiet 2>/dev/null || "
        "! git diff --cached --quiet 2>/dev/null; then\n"
        '  echo "WARNING: uncommitted changes."\n'
        "fi\n"
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


def _script_context_survival(config: ProjectConfig) -> str:
    """Generate context survival instructions for PreCompact hook.

    Pure bash (echo statements only). All values baked in at generation time.
    Output is injected into the compaction summary prompt by Claude Code.
    """
    lines = [
        "#!/usr/bin/env bash",
        "# cc-rig hook: context-survival -- project-specific compaction survival",
        "# Event: PreCompact",
        "set -euo pipefail",
        "",
        'echo "=== COMPACTION SURVIVAL INSTRUCTIONS ==="',
        'echo ""',
        'echo "PRESERVE the following project-critical context:"',
        'echo ""',
        f'echo "Project: {config.project_name}"',
        f'echo "Stack: {config.language} / {config.framework}"',
        f'echo "Workflow: {config.workflow}"',
        'echo ""',
        'echo "Key commands (ALWAYS preserve):"',
    ]

    if config.test_cmd:
        lines.append(f'echo "  Test: {config.test_cmd}"')
    if config.lint_cmd:
        lines.append(f'echo "  Lint: {config.lint_cmd}"')
    if config.format_cmd:
        lines.append(f'echo "  Format: {config.format_cmd}"')
    if config.typecheck_cmd:
        lines.append(f'echo "  Typecheck: {config.typecheck_cmd}"')

    lines.extend(
        [
            'echo ""',
            'echo "Key file paths:"',
            f'echo "  Source: {config.source_dir}/"',
            f'echo "  Tests: {config.test_dir}/"',
            'echo "  Agent docs: agent_docs/"',
        ]
    )

    # Feature-conditional sections
    feature_lines: list[str] = []
    if config.features.memory:
        feature_lines.append('echo "  - Team memory: memory/ (reload decisions.md)"')
    if config.features.spec_workflow:
        feature_lines.append('echo "  - Active specs: specs/"')
    if config.features.gtd:
        feature_lines.append('echo "  - GTD state: tasks/inbox.md, tasks/todo.md"')
    h = config.harness
    if h.autonomy_loop:
        feature_lines.append('echo "  - Autonomy state: claude-progress.txt"')
    if h.budget_awareness:
        feature_lines.append('echo "  - Budget status and token usage"')

    if feature_lines:
        lines.append('echo ""')
        lines.append('echo "Active features to remember:"')
        lines.extend(feature_lines)

    lines.extend(
        [
            'echo ""',
            'echo "DISCARD: verbose tool output, file listings, exploration results."',
            'echo "KEEP: decisions made, current task, blockers, branch name."',
            'echo "=== END SURVIVAL INSTRUCTIONS ==="',
            "",
            "exit 0",
        ]
    )

    return "\n".join(lines) + "\n"


def _script_session_telemetry(config: ProjectConfig) -> str:
    """Generate session telemetry collector for Stop hook.

    Appends structured metrics to .claude/telemetry.jsonl after each session.
    Uses inline Python (same pattern as budget-reminder) with graceful degradation.
    """
    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: session-telemetry -- append session metrics to telemetry file\n"
        "# Event: Stop\n"
        "set -euo pipefail\n"
        "\n"
        "# Session telemetry (requires python3, best-effort)\n"
        "if command -v python3 >/dev/null 2>&1; then\n"
        "  python3 << 'PYEOF'\n"
        "import glob, json, os, sys, time\n"
        "\n"
        "def find_latest_jsonl():\n"
        "    base = os.path.expanduser('~/.claude/projects')\n"
        "    if not os.path.isdir(base):\n"
        "        return None\n"
        "    cwd = os.getcwd()\n"
        "    project_dir = cwd.replace('/', '-')\n"
        "    project_path = os.path.join(base, project_dir)\n"
        "    if not os.path.isdir(project_path):\n"
        "        return None\n"
        "    files = glob.glob(os.path.join(project_path, '*.jsonl'))\n"
        "    if not files:\n"
        "        return None\n"
        "    return max(files, key=os.path.getmtime)\n"
        "\n"
        "PRICING = {\n"
        "    'opus': (15.0, 75.0, 18.75, 1.50),\n"
        "    'sonnet': (3.0, 15.0, 3.75, 0.30),\n"
        "    'haiku': (0.80, 4.0, 1.0, 0.08),\n"
        "}\n"
        "\n"
        "def parse_session(path):\n"
        "    turn_count = 0\n"
        "    tool_call_count = 0\n"
        "    model = 'sonnet'\n"
        "    compaction_count = 0\n"
        "    first_ts = None\n"
        "    last_ts = None\n"
        "    # Collect assistant usage entries with cache keys for dedup.\n"
        "    usage_entries = []  # list of (cache_key, usage_dict)\n"
        "    try:\n"
        "        with open(path) as f:\n"
        "            for line in f:\n"
        "                line = line.strip()\n"
        "                if not line:\n"
        "                    continue\n"
        "                try:\n"
        "                    msg = json.loads(line)\n"
        "                except (json.JSONDecodeError, ValueError):\n"
        "                    continue\n"
        "                msg_type = msg.get('type', '')\n"
        "                ts = msg.get('timestamp')\n"
        "                if ts:\n"
        "                    if first_ts is None:\n"
        "                        first_ts = ts\n"
        "                    last_ts = ts\n"
        "                if msg_type == 'human':\n"
        "                    turn_count += 1\n"
        "                elif msg_type == 'assistant':\n"
        "                    inner = msg.get('message', {})\n"
        "                    m = inner.get('model', '')\n"
        "                    if 'opus' in m:\n"
        "                        model = 'opus'\n"
        "                    elif 'haiku' in m:\n"
        "                        model = 'haiku'\n"
        "                    elif m:\n"
        "                        model = 'sonnet'\n"
        "                    usage = inner.get('usage', {})\n"
        "                    ck = (usage.get('cache_creation_input_tokens', 0),\n"
        "                          usage.get('cache_read_input_tokens', 0))\n"
        "                    usage_entries.append((ck, usage))\n"
        "                    for block in inner.get('content', []):\n"
        "                        if isinstance(block, dict) and block.get('type') == 'tool_use':\n"
        "                            tool_call_count += 1\n"
        "                elif msg_type == 'system' and 'compact' in str(msg).lower():\n"
        "                    compaction_count += 1\n"
        "    except (OSError, IOError):\n"
        "        return None\n"
        "    # Dedup: consecutive entries with identical cache keys, keep last.\n"
        "    deduped = []\n"
        "    for i, (ck, usage) in enumerate(usage_entries):\n"
        "        is_last = (i == len(usage_entries) - 1) or (usage_entries[i + 1][0] != ck)\n"
        "        if is_last:\n"
        "            deduped.append(usage)\n"
        "    t_in = t_out = t_cc = t_cr = 0\n"
        "    for usage in deduped:\n"
        "        t_in += usage.get('input_tokens', 0)\n"
        "        t_out += usage.get('output_tokens', 0)\n"
        "        t_cc += usage.get('cache_creation_input_tokens', 0)\n"
        "        t_cr += usage.get('cache_read_input_tokens', 0)\n"
        "    total_cache = t_cc + t_cr\n"
        "    cache_read_ratio = (t_cr / total_cache) if total_cache > 0 else 0.0\n"
        "    entries_deduped = len(usage_entries) - len(deduped)\n"
        "    return {\n"
        "        'turn_count': turn_count,\n"
        "        'tool_call_count': tool_call_count,\n"
        "        'model': model,\n"
        "        'input_tokens': t_in,\n"
        "        'output_tokens': t_out,\n"
        "        'cache_creation_tokens': t_cc,\n"
        "        'cache_read_tokens': t_cr,\n"
        "        'compaction_count': compaction_count,\n"
        "        'first_ts': first_ts,\n"
        "        'last_ts': last_ts,\n"
        "        'cache_read_ratio': cache_read_ratio,\n"
        "        'entries_deduped': entries_deduped,\n"
        "    }\n"
        "\n"
        "path = find_latest_jsonl()\n"
        "if not path:\n"
        "    sys.exit(0)\n"
        "\n"
        "metrics = parse_session(path)\n"
        "if not metrics:\n"
        "    sys.exit(0)\n"
        "\n"
        "# Calculate duration\n"
        "duration_min = 0\n"
        "if metrics['first_ts'] and metrics['last_ts']:\n"
        "    try:\n"
        "        # Timestamps may be ISO format or epoch\n"
        "        ft = metrics['first_ts']\n"
        "        lt = metrics['last_ts']\n"
        "        if isinstance(ft, str) and isinstance(lt, str):\n"
        "            from datetime import datetime\n"
        "            t1 = datetime.fromisoformat(ft.replace('Z', '+00:00'))\n"
        "            t2 = datetime.fromisoformat(lt.replace('Z', '+00:00'))\n"
        "            duration_min = max(0, (t2 - t1).total_seconds() / 60)\n"
        "        elif isinstance(ft, (int, float)) and isinstance(lt, (int, float)):\n"
        "            duration_min = max(0, (lt - ft) / 60)\n"
        "    except (ValueError, TypeError):\n"
        "        pass\n"
        "\n"
        "# Calculate cost\n"
        "p = PRICING[metrics['model']]\n"
        "cost = (\n"
        "    metrics['input_tokens'] * p[0]\n"
        "    + metrics['output_tokens'] * p[1]\n"
        "    + metrics['cache_creation_tokens'] * p[2]\n"
        "    + metrics['cache_read_tokens'] * p[3]\n"
        ") / 1_000_000\n"
        "\n"
        "record = {\n"
        "    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z'),\n"
        "    'session_file': os.path.basename(path),\n"
        "    'duration_minutes': round(duration_min, 1),\n"
        "    'turn_count': metrics['turn_count'],\n"
        "    'tool_call_count': metrics['tool_call_count'],\n"
        "    'model': metrics['model'],\n"
        "    'input_tokens': metrics['input_tokens'],\n"
        "    'output_tokens': metrics['output_tokens'],\n"
        "    'estimated_cost_usd': round(cost, 4),\n"
        "    'compaction_count': metrics['compaction_count'],\n"
        "    'cache_read_ratio': round(metrics['cache_read_ratio'], 4),\n"
        "    'entries_deduped': metrics['entries_deduped'],\n"
        "}\n"
        "\n"
        "telemetry_path = os.path.join('.claude', 'telemetry.jsonl')\n"
        "os.makedirs(os.path.dirname(telemetry_path), exist_ok=True)\n"
        "with open(telemetry_path, 'a') as f:\n"
        "    f.write(json.dumps(record) + '\\n')\n"
        "\n"
        "total_tokens = (\n"
        "    metrics['input_tokens'] + metrics['output_tokens']\n"
        "    + metrics['cache_creation_tokens'] + metrics['cache_read_tokens']\n"
        ")\n"
        "use_color = os.isatty(1) and not os.environ.get('NO_COLOR')\n"
        "G = '\\033[32m' if use_color else ''\n"
        "C = '\\033[36m' if use_color else ''\n"
        "B = '\\033[1m' if use_color else ''\n"
        "D = '\\033[2m' if use_color else ''\n"
        "R = '\\033[0m' if use_color else ''\n"
        "cache_pct = f'{metrics[\"cache_read_ratio\"]:.0%}'\n"
        "dedup_note = ''\n"
        "if metrics['entries_deduped'] > 0:\n"
        "    dedup_note = f' | deduped {metrics[\"entries_deduped\"]}'\n"
        "print(f'{B}{C}Telemetry saved{R}  '\n"
        "      f'{metrics[\"turn_count\"]} turns, '\n"
        "      f'{total_tokens:,} tokens, '\n"
        "      f'{G}~${cost:.2f}{R} | '\n"
        "      f'cache {G}{cache_pct}{R}{dedup_note}')\n"
        "PYEOF\n"
        "fi\n"
        "\n"
        "exit 0\n"
    )


def _script_budget_reminder(config: ProjectConfig) -> str:
    # Session cost parsing via inline Python (graceful degradation)
    cost_section = (
        "# Session cost tracking (requires python3, best-effort)\n"
        "if command -v python3 >/dev/null 2>&1; then\n"
        "  COST_OUTPUT=$(python3 << 'PYEOF'\n"
        "import glob, json, os, sys\n"
        "\n"
        "def find_latest_jsonl():\n"
        "    base = os.path.expanduser('~/.claude/projects')\n"
        "    if not os.path.isdir(base):\n"
        "        return None\n"
        "    # Scope to current project: /path/to/proj -> -path-to-proj\n"
        "    cwd = os.getcwd()\n"
        "    project_dir = cwd.replace('/', '-')\n"
        "    project_path = os.path.join(base, project_dir)\n"
        "    if not os.path.isdir(project_path):\n"
        "        return None\n"
        "    files = glob.glob(os.path.join(project_path, '*.jsonl'))\n"
        "    if not files:\n"
        "        return None\n"
        "    return max(files, key=os.path.getmtime)\n"
        "\n"
        "# Per-million pricing by model family\n"
        "PRICING = {\n"
        "    'opus': (15.0, 75.0, 18.75, 1.50),\n"
        "    'sonnet': (3.0, 15.0, 3.75, 0.30),\n"
        "    'haiku': (0.80, 4.0, 1.0, 0.08),\n"
        "}\n"
        "\n"
        "def detect_model(path):\n"
        "    try:\n"
        "        with open(path) as f:\n"
        "            for line in f:\n"
        "                line = line.strip()\n"
        "                if not line:\n"
        "                    continue\n"
        "                try:\n"
        "                    msg = json.loads(line)\n"
        "                except (json.JSONDecodeError, ValueError):\n"
        "                    continue\n"
        "                if msg.get('type') != 'assistant':\n"
        "                    continue\n"
        "                model = msg.get('message', {}).get('model', '')\n"
        "                if 'opus' in model:\n"
        "                    return 'opus'\n"
        "                if 'haiku' in model:\n"
        "                    return 'haiku'\n"
        "                if model:\n"
        "                    return 'sonnet'\n"
        "    except (OSError, IOError):\n"
        "        pass\n"
        "    return 'sonnet'\n"
        "\n"
        "def parse_session_tokens(path):\n"
        "    # Collect assistant entries with cache keys for dedup.\n"
        "    entries = []  # list of (cache_key, usage_dict)\n"
        "    try:\n"
        "        with open(path) as f:\n"
        "            for line in f:\n"
        "                line = line.strip()\n"
        "                if not line:\n"
        "                    continue\n"
        "                try:\n"
        "                    msg = json.loads(line)\n"
        "                except (json.JSONDecodeError, ValueError):\n"
        "                    continue\n"
        "                if msg.get('type') != 'assistant':\n"
        "                    continue\n"
        "                usage = msg.get('message', {}).get('usage', {})\n"
        "                ck = (usage.get('cache_creation_input_tokens', 0),\n"
        "                      usage.get('cache_read_input_tokens', 0))\n"
        "                entries.append((ck, usage))\n"
        "    except (OSError, IOError):\n"
        "        return None\n"
        "    # Dedup: consecutive entries with identical cache keys, keep last.\n"
        "    deduped = []\n"
        "    for i, (ck, usage) in enumerate(entries):\n"
        "        is_last = (i == len(entries) - 1) or (entries[i + 1][0] != ck)\n"
        "        if is_last:\n"
        "            deduped.append(usage)\n"
        "    t_in = t_out = t_cc = t_cr = 0\n"
        "    for usage in deduped:\n"
        "        t_in += usage.get('input_tokens', 0)\n"
        "        t_out += usage.get('output_tokens', 0)\n"
        "        t_cc += usage.get('cache_creation_input_tokens', 0)\n"
        "        t_cr += usage.get('cache_read_input_tokens', 0)\n"
        "    entries_deduped = len(entries) - len(deduped)\n"
        "    return t_in, t_out, t_cc, t_cr, entries_deduped, len(entries)\n"
        "\n"
        "path = find_latest_jsonl()\n"
        "if not path:\n"
        "    sys.exit(0)\n"
        "\n"
        "result = parse_session_tokens(path)\n"
        "if not result:\n"
        "    sys.exit(0)\n"
        "\n"
        "t_in, t_out, t_cc, t_cr, n_deduped, n_raw = result\n"
        "model = detect_model(path)\n"
        "p_in, p_out, p_cc, p_cr = PRICING[model]\n"
        "cost = (t_in * p_in + t_out * p_out + t_cc * p_cc + t_cr * p_cr) / 1_000_000\n"
        "total_tokens = t_in + t_out + t_cc + t_cr\n"
        "total_cache = t_cc + t_cr\n"
        "cache_ratio = (t_cr / total_cache * 100) if total_cache > 0 else 0\n"
        "label = model.capitalize()\n"
        "# Color support\n"
        "use_color = os.isatty(1) and not os.environ.get('NO_COLOR')\n"
        "G = '\\033[32m' if use_color else ''\n"
        "Y = '\\033[33m' if use_color else ''\n"
        "C = '\\033[36m' if use_color else ''\n"
        "D = '\\033[2m' if use_color else ''\n"
        "B = '\\033[1m' if use_color else ''\n"
        "R = '\\033[0m' if use_color else ''\n"
        "dedup_note = ''\n"
        "if n_deduped > 0:\n"
        "    dedup_note = f' | deduped {n_deduped}'\n"
        "print(f'{B}{C}Budget{R}  '\n"
        "      f'{total_tokens:,} tokens, '\n"
        "      f'{G}~${cost:.2f}{R} ({label}) | '\n"
        "      f'cache {G}{cache_ratio:.0f}%{R}{dedup_note}')\n"
        "PYEOF\n"
        "  ) 2>/dev/null || true\n"
        '  [ -n "$COST_OUTPUT" ] && echo "$COST_OUTPUT"\n'
        "fi\n"
    )

    return (
        "#!/usr/bin/env bash\n"
        "# cc-rig hook: budget-reminder — display budget status on stop\n"
        "# Event: Stop\n"
        "set -euo pipefail\n"
        "\n" + cost_section + "\n"
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
            "    MLINES=$(cat memory/*.md 2>/dev/null | wc -l || echo 0)",
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
        "# Always run lint — block (exit 2) on failure, silent on success",
        f"LINT_OUT=$({lint_cmd} 2>&1) || " + "{",
        '  LINES=$(echo "$LINT_OUT" | wc -l)',
        '  if [ "$LINES" -gt 20 ]; then',
        '    echo "$LINT_OUT" | head -20',
        '    echo "... ($LINES total lines, showing first 20)"',
        "  else",
        '    echo "$LINT_OUT"',
        "  fi",
        '  echo "Commit gate: lint failed. Fix lint errors before committing." >&2',
        "  exit 2",
        "}",
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
