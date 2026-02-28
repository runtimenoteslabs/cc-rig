"""Expert configurator (Screen 6) — fine-grained multi-selects."""

from __future__ import annotations

from cc_rig.config.project import Features, ProjectConfig
from cc_rig.config.schema import VALID_AGENTS, VALID_COMMANDS, VALID_HOOKS
from cc_rig.ui.prompts import IO, ask_choice, ask_multi


def run_expert(config: ProjectConfig, io: IO) -> ProjectConfig:
    """Run the expert configurator.

    Shows a single category picker, then dives into only the
    selected categories. Reduces the 5 sequential yes/no prompts
    to one multi-select + N detail selects.

    Returns a modified ProjectConfig.
    """
    io.say("\n--- Expert Configurator ---")
    io.say(
        f"  Agents: {len(config.agents)}  Commands: {len(config.commands)}  "
        f"Hooks: {len(config.hooks)}"
    )
    io.say("")

    categories = ask_multi(
        "What would you like to customize?",
        [
            ("agents", f"Agents ({len(config.agents)} selected)"),
            ("commands", f"Commands ({len(config.commands)} selected)"),
            ("hooks", f"Hooks ({len(config.hooks)} selected)"),
            ("features", "Feature flags"),
            ("permissions", "Permission mode"),
        ],
        defaults=[],
        io=io,
    )

    if "agents" in categories:
        agent_options = [(a, a) for a in sorted(VALID_AGENTS)]
        config.agents = ask_multi(
            "Select agents:",
            agent_options,
            defaults=config.agents,
            io=io,
        )

    if "commands" in categories:
        cmd_options = [(c, c) for c in sorted(VALID_COMMANDS)]
        config.commands = ask_multi(
            "Select commands:",
            cmd_options,
            defaults=config.commands,
            io=io,
        )

    if "hooks" in categories:
        hook_options = [(h, h) for h in sorted(VALID_HOOKS)]
        config.hooks = ask_multi(
            "Select hooks:",
            hook_options,
            defaults=config.hooks,
            io=io,
        )

    if "features" in categories:
        f = config.features

        from cc_rig.ui.prompts import confirm

        memory = confirm(
            "  Enable team memory (git-tracked decisions, patterns, team knowledge)?",
            default=f.memory,
            io=io,
        )

        # Spec-workflow and GTD are mutually exclusive — present as a single choice
        if f.spec_workflow:
            task_default = "spec"
        elif f.gtd:
            task_default = "gtd"
        else:
            task_default = "none"
        task_choice = ask_choice(
            "  Task workflow:",
            [
                ("none", "None - no structured task workflow"),
                ("spec", "Spec workflow - plan before code (specs → implement)"),
                ("gtd", "GTD - capture ideas, process later (inbox → todo)"),
            ],
            default=task_default,
            io=io,
        )

        worktrees = confirm(
            "  Enable git worktrees (parallel branches)?",
            default=f.worktrees,
            io=io,
        )

        config.features = Features(
            memory=memory,
            spec_workflow=(task_choice == "spec"),
            gtd=(task_choice == "gtd"),
            worktrees=worktrees,
        )

    if "permissions" in categories:
        config.permission_mode = ask_choice(
            "Permission mode:",
            [
                ("default", "default - ask before risky actions"),
                ("permissive", "permissive - pre-approve common tools"),
            ],
            default=config.permission_mode,
            io=io,
        )

    io.say("\nExpert configuration complete.")
    return config
