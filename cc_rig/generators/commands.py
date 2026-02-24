"""Generate .claude/commands/ slash command markdown files."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import NamedTuple

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker


class CommandDef(NamedTuple):
    """Command definition: (description, allowed_tools, prompt_body)."""

    description: str
    allowed_tools: str
    body: str


# ── Command definitions ────────────────────────────────────────────

_COMMAND_DEFS: dict[str, tuple[str, str, str]] = {
    "fix-issue": (
        "End-to-end: reproduce, diagnose, fix, test, commit",
        "Read, Write, Edit, Bash, Glob, Grep",
        (
            "$ARGUMENTS\n"
            "\n"
            "Follow these steps to fix the issue described above:\n"
            "\n"
            "1. **Reproduce**: Find or write a test that "
            "demonstrates the bug. Run it to confirm failure.\n"
            "2. **Diagnose**: Read the relevant code. Trace the "
            "execution path. Identify the root cause.\n"
            "3. **Fix**: Make the minimal change that fixes the "
            "root cause. Do not refactor unrelated code.\n"
            "4. **Test**: Run the failing test. Confirm it passes. "
            "Run the full test suite to check for regressions.\n"
            "5. **Commit**: Create a focused commit with a message "
            "that explains what was wrong and why the fix works."
        ),
    ),
    "review": (
        "Multi-dimensional code review of recent changes",
        "Read, Glob, Grep, Bash",
        (
            "$ARGUMENTS\n"
            "\n"
            "Review the specified code or recent changes:\n"
            "\n"
            "1. Run `git diff` to see current changes "
            "(or read the specified files).\n"
            "2. Evaluate across six dimensions: correctness, "
            "security, performance, readability, testing, "
            "architecture.\n"
            "3. For each issue, state: dimension, severity "
            "(critical/warning/nit), location, and concrete fix.\n"
            "4. End with a verdict: approve, request-changes, or "
            "needs-discussion.\n"
            "5. If approved, note any optional improvements "
            "as nits."
        ),
    ),
    "test": (
        "Generate tests for specified code with coverage awareness",
        "Read, Write, Edit, Bash, Glob, Grep",
        (
            "$ARGUMENTS\n"
            "\n"
            "Generate tests for the specified code:\n"
            "\n"
            "1. Read the target code. Identify public API, edge "
            "cases, and error paths.\n"
            "2. Check existing tests to avoid duplication.\n"
            "3. Write tests covering: happy path, error cases, "
            "boundary values, integration points.\n"
            "4. Follow the project's test conventions "
            "(see agent_docs/testing.md).\n"
            "5. Run the tests to verify they pass.\n"
            "6. Report coverage of the new tests if possible."
        ),
    ),
    "plan": (
        "Architecture-first planning with checkpoints",
        "Read, Glob, Grep, Bash",
        (
            "$ARGUMENTS\n"
            "\n"
            "Create an implementation plan for the described work:\n"
            "\n"
            "1. **Understand**: Read relevant code and docs. Map "
            "the current architecture.\n"
            "2. **Design**: Propose the approach. Identify affected "
            "files and interfaces.\n"
            "3. **Break down**: Split into ordered tasks with "
            "clear checkpoints.\n"
            "4. **Risk**: Note assumptions, unknowns, and "
            "potential blockers.\n"
            "5. **Present**: Show the plan with estimated effort "
            "per task.\n"
            "\n"
            "Do not start implementing. This is a planning step "
            "only. Wait for approval before proceeding."
        ),
    ),
    "learn": (
        "Explain code, concept, or pattern in this project",
        "Read, Glob, Grep",
        (
            "$ARGUMENTS\n"
            "\n"
            "Explain the specified code, concept, or pattern:\n"
            "\n"
            "1. Find the relevant code or documentation.\n"
            "2. Explain what it does in plain language.\n"
            "3. Explain WHY it was designed this way.\n"
            "4. Show how it connects to the rest of the "
            "codebase.\n"
            "5. If applicable, note common gotchas or "
            "misunderstandings.\n"
            "\n"
            "Adjust the explanation depth to match the question. "
            "Use code examples from this project, not generic ones."
        ),
    ),
    "assumptions": (
        "Surface hidden assumptions with confidence levels",
        "Read, Glob, Grep",
        (
            "$ARGUMENTS\n"
            "\n"
            "Surface your assumptions about the specified topic:\n"
            "\n"
            "1. List every assumption you are making.\n"
            "2. Rate each with a confidence level: "
            "HIGH / MEDIUM / LOW.\n"
            "3. For LOW confidence items, explain what "
            "information would resolve the uncertainty.\n"
            "4. Ask the user to confirm or correct each "
            "assumption.\n"
            "\n"
            "This is a checkpoint. Do not proceed with "
            "implementation until assumptions are validated."
        ),
    ),
    "remember": (
        "Capture learnings and decisions to memory files",
        "Read, Write, Edit",
        (
            "$ARGUMENTS\n"
            "\n"
            "Save the specified learning or decision to memory:\n"
            "\n"
            "1. Determine the category: decision, pattern, "
            "gotcha, or general.\n"
            "2. Write a one-line entry to the appropriate file:\n"
            "   - `memory/decisions.md` for architectural "
            "decisions\n"
            "   - `memory/patterns.md` for discovered patterns\n"
            "   - `memory/gotchas.md` for surprises and known "
            "issues\n"
            "   - `memory/people.md` for ownership changes\n"
            "3. Format: `[YYYY-MM-DD] Brief description`\n"
            "4. If session-log.md has >20 entries, summarize "
            "older ones.\n"
            "\n"
            "Keep entries concise. One line per learning."
        ),
    ),
    "refactor": (
        "Safe refactoring: plan, apply, verify",
        "Read, Write, Edit, Bash, Glob, Grep",
        (
            "$ARGUMENTS\n"
            "\n"
            "Refactor the specified code safely:\n"
            "\n"
            "1. **Verify tests exist** for the code. If not, "
            "write them first.\n"
            "2. **Plan** the refactoring in small steps.\n"
            "3. **Apply** one step at a time:\n"
            "   a. Make the change.\n"
            "   b. Run tests.\n"
            "   c. Commit if green.\n"
            "4. **Verify** the final result is measurably better "
            "(fewer lines, clearer names, less coupling).\n"
            "\n"
            "Never change behavior during a refactoring commit. "
            "If tests break, revert and rethink."
        ),
    ),
    "spec-create": (
        "Interview user and produce a specification document",
        "Read, Write, Edit, Glob, Grep",
        (
            "$ARGUMENTS\n"
            "\n"
            "Create a specification through user interview:\n"
            "\n"
            "1. Ask 3-5 clarifying questions about the feature.\n"
            "2. Draft a spec with:\n"
            "   - Summary\n"
            "   - User stories (As a... I want... So that...)\n"
            "   - Acceptance criteria (Given/When/Then)\n"
            "   - Task breakdown with estimates\n"
            "   - Out of scope\n"
            "   - Open questions\n"
            "3. Save to `specs/<feature-name>.md`\n"
            "4. Review with user and iterate.\n"
            "\n"
            "Be precise about scope boundaries. Ambiguity in "
            "specs causes bugs in implementation."
        ),
    ),
    "spec-execute": (
        "Pick a task from spec and implement with validation",
        "Read, Write, Edit, Bash, Glob, Grep",
        (
            "$ARGUMENTS\n"
            "\n"
            "Execute a task from an existing specification:\n"
            "\n"
            "1. Read the spec file. List available tasks.\n"
            "2. Pick the next unfinished task (or the one "
            "specified).\n"
            "3. Implement it:\n"
            "   a. Write tests based on acceptance criteria.\n"
            "   b. Implement until tests pass.\n"
            "   c. Run full test suite.\n"
            "4. Mark the task as done in the spec.\n"
            "5. Commit with a message referencing the spec.\n"
            "\n"
            "Follow the spec exactly. If the spec is wrong, "
            "update it first, then implement."
        ),
    ),
    "techdebt": (
        "Identify and prioritize technical debt",
        "Read, Glob, Grep, Bash",
        (
            "$ARGUMENTS\n"
            "\n"
            "Analyze the codebase for technical debt:\n"
            "\n"
            "1. Scan for indicators:\n"
            "   - TODO/FIXME/HACK comments\n"
            "   - Duplicated logic\n"
            "   - Dead code\n"
            "   - Missing tests for critical paths\n"
            "   - Outdated dependencies\n"
            "   - Overly complex functions (high cyclomatic "
            "complexity)\n"
            "2. Categorize each item by type.\n"
            "3. Rate impact: HIGH (blocks features), MEDIUM "
            "(slows work), LOW (cosmetic).\n"
            "4. Output a prioritized list with location and "
            "suggested fix."
        ),
    ),
    "security": (
        "Security audit focused on OWASP top 10",
        "Read, Glob, Grep, Bash",
        (
            "$ARGUMENTS\n"
            "\n"
            "Run a security audit on the specified scope:\n"
            "\n"
            "1. Check for OWASP Top 10 vulnerabilities:\n"
            "   - Injection (SQL, command, template)\n"
            "   - Broken authentication\n"
            "   - Sensitive data exposure\n"
            "   - Broken access control\n"
            "   - Security misconfiguration\n"
            "   - XSS (if web)\n"
            "   - Insecure dependencies\n"
            "2. Check for hardcoded secrets or credentials.\n"
            "3. Review auth and authz boundaries.\n"
            "4. Output findings with severity, location, "
            "and recommended fix.\n"
            "\n"
            "Prioritize critical and high severity findings."
        ),
    ),
    "document": (
        "Generate documentation for a module or API",
        "Read, Write, Edit, Glob, Grep",
        (
            "$ARGUMENTS\n"
            "\n"
            "Document the specified module or API:\n"
            "\n"
            "1. Read the source code and existing docs.\n"
            "2. Identify public interfaces, parameters, return "
            "types.\n"
            "3. Write documentation with:\n"
            "   - Module overview\n"
            "   - Public API reference with type signatures\n"
            "   - Usage examples (from this project)\n"
            "   - Important caveats or side effects\n"
            "4. Update existing docs rather than creating new "
            "files.\n"
            "\n"
            "Match the project's documentation style. Document "
            "the WHY, not just the WHAT."
        ),
    ),
    "optimize": (
        "Performance analysis and targeted optimization",
        "Read, Write, Edit, Bash, Glob, Grep",
        (
            "$ARGUMENTS\n"
            "\n"
            "Analyze and optimize the specified code:\n"
            "\n"
            "1. **Profile**: Identify the bottleneck. Do not "
            "guess.\n"
            "2. **Measure**: Establish a baseline metric.\n"
            "3. **Optimize**: Apply the minimal change that "
            "addresses the bottleneck.\n"
            "4. **Verify**: Measure again. Confirm improvement.\n"
            "5. **Test**: Run tests to ensure correctness.\n"
            "\n"
            "Common targets: N+1 queries, unnecessary "
            "allocations, blocking I/O, missing indexes, "
            "redundant computation.\n"
            "\n"
            "Premature optimization is the root of all evil. "
            "Only optimize measured bottlenecks."
        ),
    ),
    "gtd-capture": (
        "Quick capture an idea or task to inbox",
        "Read, Write, Edit",
        (
            "$ARGUMENTS\n"
            "\n"
            "Capture the described item to the GTD inbox:\n"
            "\n"
            "1. Add the item to `tasks/inbox.md` with a "
            "timestamp.\n"
            "2. Format: `- [ ] [YYYY-MM-DD] <description>`\n"
            "3. Do not process or prioritize yet. Just capture.\n"
            "\n"
            "The inbox is for raw capture. Processing happens "
            "during `/gtd-process`."
        ),
    ),
    "gtd-process": (
        "Process inbox items: action, defer, or delete",
        "Read, Write, Edit",
        (
            "$ARGUMENTS\n"
            "\n"
            "Process unprocessed items in `tasks/inbox.md`:\n"
            "\n"
            "For each item in the inbox:\n"
            "1. **Is it actionable?**\n"
            "   - Yes, <2 min → do it now, mark done.\n"
            "   - Yes, larger → move to `tasks/todo.md` with "
            "context.\n"
            "   - No, maybe later → move to "
            "`tasks/someday.md`.\n"
            "   - No, not needed → delete it.\n"
            "2. Add context to moved items: what is the next "
            "action?\n"
            "3. Remove processed items from inbox.\n"
            "\n"
            "Goal: empty inbox after processing."
        ),
    ),
    "daily-plan": (
        "Morning planning: review tasks and set daily priorities",
        "Read, Write, Edit",
        (
            "$ARGUMENTS\n"
            "\n"
            "Create today's plan:\n"
            "\n"
            "1. Read `tasks/todo.md` — what is in progress?\n"
            "2. Read `tasks/inbox.md` — anything urgent?\n"
            "3. Check `memory/session-log.md` — what was done "
            "yesterday?\n"
            "4. Pick 1-3 tasks for today. Be realistic.\n"
            "5. Output the daily plan:\n"
            "   - Carry-over items\n"
            "   - Today's focus (1-3 tasks)\n"
            "   - Blocked items (if any)\n"
            "\n"
            "Start with the most important task, not the easiest."
        ),
    ),
    "worktree": (
        "Spawn a parallel worker in an isolated git worktree",
        "Read, Bash, Task",
        (
            "$ARGUMENTS\n"
            "\n"
            "Spawn a parallel worker for the described task:\n"
            "\n"
            "1. Create a new branch for the task.\n"
            "2. Spawn the parallel-worker agent with:\n"
            "   - `isolation: worktree`\n"
            "   - `background: true`\n"
            "3. Pass the task description to the worker.\n"
            "4. The worker will implement, test, commit, and "
            "create a PR.\n"
            "\n"
            "Monitor the worker's progress. Review the PR when "
            "it is ready.\n"
            "\n"
            "Note: This uses Claude Code's native worktree "
            "support via the Task tool."
        ),
    ),
}


def generate_commands(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate .claude/commands/{name}.md for each command in config.

    Returns list of relative file paths written.
    """
    if not config.commands:
        return []

    commands_dir = output_dir / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    files_written: list[str] = []

    for cmd_name in config.commands:
        raw = _COMMAND_DEFS.get(cmd_name)
        if raw is None:
            warnings.warn(
                f"Unknown command '{cmd_name}' — skipped",
                stacklevel=2,
            )
            continue

        defn = CommandDef(*raw)
        content = (
            f"---\ndescription: {defn.description}\n"
            f"allowed-tools: {defn.allowed_tools}\n---\n\n{defn.body}\n"
        )

        filename = f"{cmd_name}.md"
        rel = f".claude/commands/{filename}"
        if tracker is not None:
            tracker.write_text(rel, content)
        else:
            (commands_dir / filename).write_text(content)
        files_written.append(rel)

    return files_written
