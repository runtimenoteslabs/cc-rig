"""Expert configurator (Screen 6) — fine-grained multi-selects."""

from __future__ import annotations

from cc_rig.config.project import Features, ProjectConfig
from cc_rig.config.schema import VALID_AGENTS, VALID_COMMANDS, VALID_HOOKS
from cc_rig.ui.prompts import IO, ask_choice, ask_multi, confirm


def run_expert(config: ProjectConfig, io: IO) -> ProjectConfig:
    """Run the expert configurator.

    Pre-filled with current config values. User can modify
    agents, commands, hooks, features, and permission mode.

    Returns a modified ProjectConfig.
    """
    io.say("\n--- Expert Configurator ---")
    io.say("Pre-filled with workflow defaults. Modify as needed.\n")

    # Agents
    if confirm("Customize agents?", default=False, io=io):
        agent_options = [(a, a) for a in sorted(VALID_AGENTS)]
        config.agents = ask_multi(
            "Select agents:",
            agent_options,
            defaults=config.agents,
            io=io,
        )

    # Commands
    if confirm("Customize commands?", default=False, io=io):
        cmd_options = [(c, c) for c in sorted(VALID_COMMANDS)]
        config.commands = ask_multi(
            "Select commands:",
            cmd_options,
            defaults=config.commands,
            io=io,
        )

    # Hooks
    if confirm("Customize hooks?", default=False, io=io):
        hook_options = [(h, h) for h in sorted(VALID_HOOKS)]
        config.hooks = ask_multi(
            "Select hooks:",
            hook_options,
            defaults=config.hooks,
            io=io,
        )

    # Features
    if confirm("Toggle feature flags?", default=False, io=io):
        f = config.features
        config.features = Features(
            memory=confirm(
                "  Enable memory (session logs, decisions, patterns)?",
                default=f.memory,
                io=io,
            ),
            spec_workflow=confirm(
                "  Enable spec-driven workflow (plan before code)?",
                default=f.spec_workflow,
                io=io,
            ),
            gtd=confirm(
                "  Enable GTD task management (capture, process, plan)?",
                default=f.gtd,
                io=io,
            ),
            worktrees=confirm(
                "  Enable git worktrees (parallel branches)?",
                default=f.worktrees,
                io=io,
            ),
        )

    # Permission mode
    if confirm("Customize permission mode?", default=False, io=io):
        config.permission_mode = ask_choice(
            "Permission mode:",
            [
                ("default", "default — ask before risky actions"),
                ("permissive", "permissive — pre-approve common tools"),
            ],
            default=config.permission_mode,
            io=io,
        )

    io.say("\nExpert configuration complete.")
    return config
