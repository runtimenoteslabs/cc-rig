"""CLI entry point for cc-rig."""

from __future__ import annotations

import argparse
import sys
from typing import Any, Callable

from cc_rig import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cc-rig",
        description="Project setup generator for Claude Code",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"cc-rig {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    # init
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a new project configuration",
    )
    init_parser.add_argument(
        "--template",
        help="Template preset (e.g. fastapi, nextjs)",
    )
    init_parser.add_argument(
        "--workflow",
        help="Workflow preset (e.g. standard, speedrun)",
    )
    init_parser.add_argument(
        "--name",
        help="Project name",
    )
    init_parser.add_argument(
        "-o",
        "--output",
        help="Output directory (default: current)",
    )
    init_parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick setup with picker",
    )
    init_parser.add_argument(
        "--expert",
        action="store_true",
        help="Expert configurator",
    )
    init_parser.add_argument(
        "--config",
        help="Load from saved config file",
    )
    init_parser.add_argument(
        "--migrate",
        action="store_true",
        help="Migrate existing repo",
    )
    init_parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write to current directory (skip output prompt)",
    )

    # config
    config_parser = subparsers.add_parser(
        "config",
        help="Manage saved configurations",
    )
    config_sub = config_parser.add_subparsers(dest="config_command")

    config_save = config_sub.add_parser("save", help="Save current config")
    config_save.add_argument("name", nargs="?", help="Config name")
    config_save.add_argument(
        "--export",
        metavar="PATH",
        help="Export to custom path",
    )
    config_save.add_argument(
        "--portable",
        action="store_true",
        help="Strip machine-specific paths",
    )
    config_save.add_argument(
        "--local",
        action="store_true",
        help="Save to personal dir (~/.cc-rig/configs/)",
    )
    config_save.add_argument(
        "--project",
        action="store_true",
        help="Save to project dir (.cc-rig.json)",
    )

    config_load = config_sub.add_parser("load", help="Load a saved config")
    config_load.add_argument("name", help="Config name or path")

    config_sub.add_parser("list", help="List saved configs")

    config_inspect = config_sub.add_parser(
        "inspect",
        help="Inspect a config",
    )
    config_inspect.add_argument("name", help="Config name or path")

    config_update = config_sub.add_parser(
        "update",
        help="Re-run wizard with existing config pre-filled",
    )
    config_update.add_argument(
        "-d",
        "--dir",
        default=".",
        help="Project directory (default: current)",
    )
    config_update.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: just re-pick template + workflow",
    )
    config_update.add_argument(
        "--expert",
        action="store_true",
        help="Expert mode: full customization",
    )

    config_diff = config_sub.add_parser("diff", help="Diff two configs")
    config_diff.add_argument("name", help="Config name or path to diff against")

    config_lock = config_sub.add_parser("lock", help="Lock a config")
    config_lock.add_argument("name", help="Config name or path")

    config_unlock = config_sub.add_parser("unlock", help="Unlock a config")
    config_unlock.add_argument("name", help="Config name or path")

    # preset
    preset_parser = subparsers.add_parser(
        "preset",
        help="List, inspect, create, and install presets",
    )
    preset_sub = preset_parser.add_subparsers(dest="preset_command")

    preset_list = preset_sub.add_parser("list", help="List available presets")
    preset_list_filter = preset_list.add_mutually_exclusive_group()
    preset_list_filter.add_argument(
        "--templates",
        action="store_true",
        help="Show templates only",
    )
    preset_list_filter.add_argument(
        "--workflows",
        action="store_true",
        help="Show workflows only",
    )

    preset_inspect = preset_sub.add_parser("inspect", help="Inspect a preset")
    preset_inspect.add_argument("name", help="Preset name")

    preset_create = preset_sub.add_parser("create", help="Create preset from current project")
    preset_create.add_argument("name", help="Preset name")
    preset_create_type = preset_create.add_mutually_exclusive_group()
    preset_create_type.add_argument(
        "--template",
        action="store_const",
        const="template",
        dest="preset_type",
        help="Extract template portion",
    )
    preset_create_type.add_argument(
        "--workflow",
        action="store_const",
        const="workflow",
        dest="preset_type",
        help="Extract workflow portion",
    )
    preset_create.set_defaults(preset_type="workflow")

    preset_install = preset_sub.add_parser("install", help="Install preset from local file")
    preset_install.add_argument("path", help="Path to preset JSON file")

    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="Check project health")
    doctor_parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix safe issues (permissions, missing memory files)",
    )
    doctor_parser.add_argument(
        "--check-compat",
        action="store_true",
        help="Check feature compatibility with installed Claude Code version",
    )
    doctor_parser.add_argument(
        "-d",
        "--dir",
        default=".",
        help="Project directory (default: current)",
    )

    # harness
    harness_parser = subparsers.add_parser(
        "harness",
        help="Add runtime harness to project",
    )
    harness_sub = harness_parser.add_subparsers(dest="harness_command")
    harness_init = harness_sub.add_parser("init", help="Initialize harness")
    harness_level = harness_init.add_mutually_exclusive_group()
    harness_level.add_argument(
        "--lite",
        action="store_const",
        const="lite",
        dest="level",
        help="B1: task tracking + budget awareness",
    )
    harness_level.add_argument(
        "--standard",
        action="store_const",
        const="standard",
        dest="level",
        help="B2: + verification gates + review notes (default)",
    )
    harness_level.add_argument(
        "--autonomy",
        action="store_const",
        const="autonomy",
        dest="level",
        help="B3: autonomous iteration with safety rails",
    )
    harness_level.add_argument(
        "--ralph",
        action="store_const",
        const="autonomy",
        dest="level",
        help=argparse.SUPPRESS,  # hidden alias for --autonomy
    )
    harness_init.add_argument(
        "-d",
        "--dir",
        default=".",
        help="Project directory (default: current)",
    )
    harness_init.set_defaults(level="standard")

    harness_status = harness_sub.add_parser("status", help="Show harness state")
    harness_status.add_argument(
        "--dir",
        default=".",
        help="Project directory (default: current)",
    )

    # skills
    skills_parser = subparsers.add_parser(
        "skills",
        help="Manage community skills",
    )
    skills_sub = skills_parser.add_subparsers(dest="skills_command")

    skills_list_p = skills_sub.add_parser("list", help="Show installed skills")
    skills_list_p.add_argument(
        "-d",
        "--dir",
        default=".",
        help="Project directory",
    )

    skills_catalog_p = skills_sub.add_parser("catalog", help="Show all available skills")
    skills_catalog_p.add_argument(
        "--phase",
        help="Filter by SDLC phase",
    )

    skills_add_p = skills_sub.add_parser("add", help="Install a skill from catalog")
    skills_add_p.add_argument("name", help="Skill name (from catalog)")
    skills_add_p.add_argument(
        "-d",
        "--dir",
        default=".",
        help="Project directory",
    )

    skills_remove_p = skills_sub.add_parser("remove", help="Remove an installed skill")
    skills_remove_p.add_argument("name", help="Skill name to remove")
    skills_remove_p.add_argument(
        "-d",
        "--dir",
        default=".",
        help="Project directory",
    )

    skills_install_p = skills_sub.add_parser(
        "install",
        help="Retry failed downloads from init",
    )
    skills_install_p.add_argument(
        "-d",
        "--dir",
        default=".",
        help="Project directory",
    )

    # clean
    clean_parser = subparsers.add_parser("clean", help="Remove generated files")
    clean_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    clean_parser.add_argument(
        "-d",
        "--dir",
        default=".",
        help="Project directory (default: current)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "init":
            return _cmd_init(args)
        if args.command == "preset":
            return _cmd_preset(args)
        if args.command == "config":
            return _cmd_config(args)
        if args.command == "harness":
            return _cmd_harness(args)
        if args.command == "skills":
            return _cmd_skills(args)
        if args.command == "doctor":
            return _cmd_doctor(args)
        if args.command == "clean":
            return _cmd_clean(args)
        print(f"cc-rig: '{args.command}' not yet implemented")
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130


def _cmd_init(args: argparse.Namespace) -> int:
    """Dispatch init subcommand to wizard."""
    from cc_rig.config.cc_version import detect_cc_version
    from cc_rig.wizard.flow import run_wizard

    # Check Claude Code installation
    cc = detect_cc_version()
    for w in cc.warnings:
        print(f"  ! {w}")

    return run_wizard(args)


def _cmd_preset(args: argparse.Namespace) -> int:
    """Dispatch preset subcommand."""
    cmd = getattr(args, "preset_command", None)
    if cmd == "list":
        return _preset_list(args)
    if cmd == "inspect":
        return _preset_inspect(args)
    if cmd == "create":
        return _preset_create(args)
    if cmd == "install":
        return _preset_install(args)
    # Default to list
    return _preset_list(args)


def _cmd_config(args: argparse.Namespace) -> int:
    """Dispatch config subcommands."""

    from cc_rig.config.manager import (
        diff_configs,
        inspect_config,
        is_locked,
        list_configs,
        load_config,
        lock_config,
        save_config,
        unlock_config,
    )

    cmd = getattr(args, "config_command", None)

    if cmd == "update":
        return _config_update(args)
    if cmd == "save":
        return _config_save(args, save_config)
    if cmd == "load":
        return _config_load_cmd(args, load_config)
    if cmd == "list":
        return _config_list(list_configs)
    if cmd == "inspect":
        return _config_inspect(args, inspect_config, is_locked)
    if cmd == "diff":
        return _config_diff(args, load_config, diff_configs)
    if cmd == "lock":
        return _config_lock(args, lock_config)
    if cmd == "unlock":
        return _config_unlock(args, unlock_config)

    # Default to list
    return _config_list(list_configs)


def _config_update(args: argparse.Namespace) -> int:
    """Re-run wizard with existing config pre-filled."""
    from pathlib import Path

    from cc_rig.wizard.flow import run_update_wizard

    project_dir = Path(args.dir).resolve()
    return run_update_wizard(
        project_dir,
        expert=getattr(args, "expert", False),
        quick=getattr(args, "quick", False),
    )


def _config_save(args: argparse.Namespace, save_fn: Callable[..., Any]) -> int:
    """Save current project config."""
    from pathlib import Path

    from cc_rig.config.project import ProjectConfig

    project_flag = getattr(args, "project", False)

    cc_rig_json = Path(".cc-rig.json")
    if not cc_rig_json.exists():
        print("No .cc-rig.json found in current directory.")
        print("Run 'cc-rig init' first to generate a project config.")
        return 1

    config = ProjectConfig.from_json(cc_rig_json.read_text())
    export_path = getattr(args, "export", None)
    portable = getattr(args, "portable", False)

    if export_path:
        dest = save_fn(config, path=Path(export_path), portable=portable)
    elif project_flag:
        dest = save_fn(config, path=Path(".cc-rig.json"), portable=portable)
    else:
        dest = save_fn(
            config,
            name=args.name,
            portable=portable,
        )
    print(f"Saved: {dest}")
    return 0


def _config_load_cmd(args: argparse.Namespace, load_fn: Callable[..., Any]) -> int:
    """Load and display a saved config."""
    try:
        config = load_fn(args.name)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Loaded: {config.project_name} ({config.template_preset} + {config.workflow_preset})")
    return 0


def _config_list(list_fn: Callable[..., Any]) -> int:
    """List saved configs."""
    from pathlib import Path

    result = list_fn(project_dir=Path("."))

    if result["personal"]:
        print("\nPersonal configs (~/.cc-rig/configs/):")
        for c in result["personal"]:
            lock = " [LOCKED]" if c["locked"] else ""
            print(f"  {c['name']:<20} {c['template']} + {c['workflow']}{lock}")
    else:
        print("\nNo personal configs saved.")

    if result["project"]:
        print("\nProject config:")
        for c in result["project"]:
            lock = " [LOCKED]" if c["locked"] else ""
            print(f"  {c['name']:<20} {c['template']} + {c['workflow']}{lock}")
    else:
        print("\nNo project config (.cc-rig.json) found.")

    print()
    return 0


def _config_inspect(
    args: argparse.Namespace,
    inspect_fn: Callable[..., Any],
    is_locked_fn: Callable[..., Any],
) -> int:
    """Inspect a config."""
    try:
        output = inspect_fn(args.name)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    print(output)
    return 0


def _config_diff(
    args: argparse.Namespace,
    load_fn: Callable[..., Any],
    diff_fn: Callable[..., Any],
) -> int:
    """Diff current project config vs a saved config."""
    from pathlib import Path

    from cc_rig.config.project import ProjectConfig

    cc_rig_json = Path(".cc-rig.json")
    if not cc_rig_json.exists():
        print("No .cc-rig.json in current directory to diff against.")
        return 1

    try:
        current = ProjectConfig.from_json(cc_rig_json.read_text())
        other = load_fn(args.name)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1

    result = diff_fn(current, other)
    if result:
        print(result)
    else:
        print("Configs are identical.")
    return 0


def _config_lock(args: argparse.Namespace, lock_fn: Callable[..., Any]) -> int:
    """Lock a config."""
    try:
        path = lock_fn(args.name)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Locked: {path}")
    return 0


def _config_unlock(args: argparse.Namespace, unlock_fn: Callable[..., Any]) -> int:
    """Unlock a config."""
    try:
        path = unlock_fn(args.name)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Unlocked: {path}")
    return 0


def _cmd_harness(args: argparse.Namespace) -> int:
    """Dispatch harness subcommands."""
    cmd = getattr(args, "harness_command", None)
    if cmd == "init":
        return _harness_init(args)
    if cmd == "status":
        return _harness_status(args)
    # Default: show help
    print("Usage: cc-rig harness init [--lite|--standard|--autonomy]")
    print("       cc-rig harness status")
    return 0


def _harness_init(args: argparse.Namespace) -> int:
    """Initialize harness in an existing project."""
    import json
    from pathlib import Path

    from cc_rig.config.project import HarnessConfig, ProjectConfig
    from cc_rig.generators.harness import generate_harness
    from cc_rig.generators.settings import generate_settings

    project_dir = Path(args.dir).resolve()
    cc_rig_json = project_dir / ".cc-rig.json"

    if not cc_rig_json.exists():
        print("No .cc-rig.json found. Run 'cc-rig init' first.")
        return 1

    # Load existing config
    try:
        config = ProjectConfig.from_json(cc_rig_json.read_text())
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"Error reading .cc-rig.json: {exc}")
        return 1

    level = args.level

    # B3 autonomy warning + confirmation
    if level == "autonomy":
        from cc_rig.wizard.harness import AUTONOMY_WARNING_LINES

        print()
        for line in AUTONOMY_WARNING_LINES:
            print(line)
        print()
        try:
            response = input('  Type "I understand" to confirm: ').strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 130
        if response != "I understand":
            print("  Cancelled. Autonomy mode not enabled.")
            return 0

    # Set harness config
    config.harness = HarnessConfig(level=level)

    # Generate harness files
    files = generate_harness(config, project_dir)

    # Regenerate settings.json (picks up new harness hooks)
    settings_files = generate_settings(config, project_dir)
    files.extend(f for f in settings_files if f not in files)

    # Update .cc-rig.json with harness config
    cc_rig_json.write_text(config.to_json() + "\n")

    # Update manifest if it exists
    manifest_path = project_dir / ".claude" / ".cc-rig-manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            existing = set(manifest.get("files", []))
            existing.update(files)
            manifest["files"] = sorted(existing)
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        except json.JSONDecodeError:
            import warnings

            warnings.warn(
                "Could not update manifest: invalid JSON",
                stacklevel=1,
            )

    print(f"Harness initialized: {level} ({len(files)} files generated)")
    for f in files:
        print(f"  + {f}")
    return 0


def _harness_status(args: argparse.Namespace) -> int:
    """Show harness state for the current project."""
    import json
    from pathlib import Path

    project_dir = Path(getattr(args, "dir", ".")).resolve()
    cc_rig_json = project_dir / ".cc-rig.json"

    if not cc_rig_json.exists():
        print("No .cc-rig.json found. Not a cc-rig project.")
        return 1

    try:
        data = json.loads(cc_rig_json.read_text())
    except json.JSONDecodeError as exc:
        print(f"Error reading .cc-rig.json: {exc}")
        return 1

    harness = data.get("harness", {})
    level = harness.get("level", "none")

    print(f"\nHarness: {level.upper()}")

    if level == "none":
        print("  No harness configured.")
        print("  Use 'cc-rig harness init' to add one.")
        print()
        return 0

    print(f"  Max iterations:     {harness.get('max_iterations', 20)}")
    print(f"  Checkpoint commits: {harness.get('checkpoint_commits', True)}")
    print(f"  Tests must pass:    {harness.get('require_tests_pass', True)}")
    print(f"  Lint must pass:     {harness.get('require_lint_pass', True)}")
    print(f"  If blocked:         {harness.get('if_blocked', 'stop')}")

    budget = harness.get("budget_per_run_tokens")
    if budget:
        print(f"  Budget:             {budget:,} tokens")
    else:
        print("  Budget:             unlimited")

    # Check for task files
    todo = project_dir / "tasks" / "todo.md"
    if todo.exists():
        content = todo.read_text()
        total = content.count("- [ ]") + content.count("- [x]")
        done = content.count("- [x]")
        print(f"\n  Tasks: {done}/{total} complete")

    print()
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    """Run project health checks."""
    from pathlib import Path

    from cc_rig.doctor import run_doctor

    project_dir = Path(args.dir).resolve()
    check_compat = getattr(args, "check_compat", False)
    result = run_doctor(project_dir, fix=args.fix, check_compat=check_compat)

    if result.fixes:
        print("\nFixes applied:")
        for fix in result.fixes:
            print(f"  + {fix}")

    if result.errors:
        print("\nErrors:")
        for err in result.errors:
            print(f"  x {err}")

    if result.warnings:
        print("\nWarnings:")
        for warn in result.warnings:
            print(f"  ! {warn}")

    if result.passed and not result.warnings:
        print("\nAll checks passed.")
    elif result.passed:
        print(f"\nPassed with {len(result.warnings)} warning(s).")
    else:
        print(f"\n{len(result.errors)} error(s), {len(result.warnings)} warning(s).")

    return 0 if result.passed else 1


def _cmd_clean(args: argparse.Namespace) -> int:
    """Remove generated files."""
    from pathlib import Path

    from cc_rig.clean import run_clean
    from cc_rig.ui.prompts import confirm

    project_dir = Path(args.dir).resolve()

    try:
        result = run_clean(
            project_dir,
            force=args.force,
            confirm_fn=lambda prompt: confirm(prompt, default=False),
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1

    if result.total_removed == 0 and not result.already_missing:
        print("Nothing to clean (cancelled or empty manifest).")
        return 0

    if result.removed:
        print(f"\nRemoved {len(result.removed)} file(s).")
    if result.already_missing:
        print(f"  ({len(result.already_missing)} already missing)")
    if result.restored:
        print(f"  Restored {len(result.restored)} pre-existing file(s).")
    if result.skipped_user_modified:
        print(f"\n  Preserved {len(result.skipped_user_modified)} user-modified file(s):")
        for f in result.skipped_user_modified:
            print(f"    {f}")
    if result.dirs_removed:
        print(f"  Cleaned up {len(result.dirs_removed)} empty directory(ies).")

    print("Clean complete.")
    return 0


def _cmd_skills(args: argparse.Namespace) -> int:
    """Dispatch skills subcommands."""
    cmd = getattr(args, "skills_command", None)
    if cmd == "list":
        return _skills_list(args)
    if cmd == "catalog":
        return _skills_catalog(args)
    if cmd == "add":
        return _skills_add(args)
    if cmd == "remove":
        return _skills_remove(args)
    if cmd == "install":
        return _skills_install(args)
    # Default to list
    return _skills_list(args)


def _skills_list(args: argparse.Namespace) -> int:
    """Show installed skills grouped by phase."""
    from pathlib import Path

    from cc_rig.skills.registry import SKILL_CATALOG

    project_dir = Path(getattr(args, "dir", ".")).resolve()
    skills_dir = project_dir / ".claude" / "skills"

    if not skills_dir.is_dir():
        print("No skills installed. Run 'cc-rig init' to set up your project.")
        return 0

    # Find installed skills
    installed: list[tuple[str, str, str]] = []  # (name, phase, source)
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        name = skill_dir.name
        spec = SKILL_CATALOG.get(name)
        phase = spec.sdlc_phase if spec else "local"
        source = spec.repo if spec else "local"
        installed.append((name, phase, source))

    if not installed:
        print("No skills installed.")
        return 0

    # Group by phase
    by_phase: dict[str, list[tuple[str, str]]] = {}
    for name, phase, source in installed:
        by_phase.setdefault(phase, []).append((name, source))

    print(f"\nInstalled skills ({len(installed)}):\n")
    for phase in (
        "coding",
        "testing",
        "review",
        "security",
        "database",
        "devops",
        "planning",
        "local",
    ):
        entries = by_phase.get(phase, [])
        if entries:
            print(f"  {phase.upper()}")
            for name, source in entries:
                print(f"    {name:<35} ({source})")
    print()
    return 0


def _skills_catalog(args: argparse.Namespace) -> int:
    """Show all available skills in the registry."""
    from cc_rig.skills.registry import SKILL_CATALOG

    phase_filter = getattr(args, "phase", None)

    # Group by phase
    by_phase: dict[str, list] = {}
    for spec in SKILL_CATALOG.values():
        if phase_filter and spec.sdlc_phase != phase_filter:
            continue
        by_phase.setdefault(spec.sdlc_phase, []).append(spec)

    if not by_phase:
        print(f"No skills found for phase: {phase_filter}")
        return 0

    print(f"\nSkill catalog ({len(SKILL_CATALOG)} skills):\n")
    phase_order = ["coding", "testing", "review", "security", "database", "devops", "planning"]
    for phase in phase_order:
        specs = by_phase.get(phase, [])
        if specs:
            print(f"  {phase.upper()}")
            for s in specs:
                print(f"    {s.name:<35} {s.description}")
                print(f"    {'':35} {s.repo}")
    print()
    return 0


def _skills_add(args: argparse.Namespace) -> int:
    """Download and install a skill from the catalog."""
    from pathlib import Path

    from cc_rig.skills.downloader import download_skills
    from cc_rig.skills.registry import SKILL_CATALOG

    project_dir = Path(args.dir).resolve()
    name = args.name

    spec = SKILL_CATALOG.get(name)
    if not spec:
        print(f"Unknown skill: {name}")
        print("Run 'cc-rig skills catalog' to see available skills.")
        return 1

    # Check if already installed
    skill_md = project_dir / ".claude" / "skills" / name / "SKILL.md"
    if skill_md.exists():
        print(f"Skill '{name}' is already installed.")
        return 0

    print(f"Installing {name} from {spec.repo}...")
    report = download_skills([spec], project_dir)

    if name in report.installed:
        print(f"Installed: {name}")
        for f in report.all_files:
            print(f"  + {f}")
        return 0
    else:
        reason = dict(report.failed).get(name, "unknown error")
        print(f"Failed to install {name}: {reason}")
        return 1


def _skills_remove(args: argparse.Namespace) -> int:
    """Remove an installed skill."""
    import shutil
    from pathlib import Path

    project_dir = Path(args.dir).resolve()
    name = args.name
    skill_dir = project_dir / ".claude" / "skills" / name

    if not skill_dir.is_dir():
        print(f"Skill '{name}' is not installed.")
        return 1

    shutil.rmtree(skill_dir)
    print(f"Removed: {name}")
    return 0


def _skills_install(args: argparse.Namespace) -> int:
    """Retry failed downloads — install all resolved skills for the project."""
    import json
    from pathlib import Path

    from cc_rig.config.project import ProjectConfig
    from cc_rig.skills.downloader import download_skills
    from cc_rig.skills.registry import resolve_skills

    project_dir = Path(args.dir).resolve()
    cc_rig_json = project_dir / ".cc-rig.json"

    if not cc_rig_json.exists():
        print("No .cc-rig.json found. Run 'cc-rig init' first.")
        return 1

    try:
        config = ProjectConfig.from_json(cc_rig_json.read_text())
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"Error reading .cc-rig.json: {exc}")
        return 1

    # Resolve which skills should be installed
    specs = resolve_skills(
        config.template_preset or config.framework or "",
        config.workflow or "standard",
        config.default_mcps,
    )

    if not specs:
        print("No skills to install for this configuration.")
        return 0

    # Filter to skills not already installed
    skills_dir = project_dir / ".claude" / "skills"
    missing = [s for s in specs if not (skills_dir / s.name / "SKILL.md").exists()]

    if not missing:
        print(f"All {len(specs)} skills already installed.")
        return 0

    print(f"Installing {len(missing)} missing skill(s)...")
    report = download_skills(missing, project_dir)

    if report.installed:
        print(f"\nInstalled ({len(report.installed)}):")
        for name in report.installed:
            print(f"  + {name}")

    if report.failed:
        print(f"\nFailed ({len(report.failed)}):")
        for name, reason in report.failed:
            print(f"  x {name}: {reason}")

    return 0 if not report.failed else 1


def _preset_list(args: argparse.Namespace | None = None) -> int:
    """List available templates and workflows."""
    from cc_rig.presets.manager import list_presets

    filter_type = None
    if args and getattr(args, "templates", False):
        filter_type = "templates"
    elif args and getattr(args, "workflows", False):
        filter_type = "workflows"

    result = list_presets(filter_type=filter_type)

    if result.get("templates"):
        print("\nTemplates:")
        for t in result["templates"]:
            src = " (user)" if t.get("source") == "user" else ""
            print(f"  {t['name']:<12} {t['language']} / {t['framework']}{src}")

    if result.get("workflows"):
        print("\nWorkflows:")
        for w in result["workflows"]:
            src = " (user)" if w.get("source") == "user" else ""
            print(f"  {w['name']:<15} {w['description']}{src}")

    print()
    return 0


def _preset_inspect(args: argparse.Namespace) -> int:
    """Inspect a preset."""
    from cc_rig.presets.manager import inspect_preset

    try:
        output = inspect_preset(args.name)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    print(output)
    return 0


def _preset_create(args: argparse.Namespace) -> int:
    """Create a preset from current project config."""
    from pathlib import Path

    from cc_rig.presets.manager import create_preset

    cc_rig_json = Path(".cc-rig.json")
    if not cc_rig_json.exists():
        print("No .cc-rig.json found in current directory.")
        print("Run 'cc-rig init' first to generate a project config.")
        return 1

    try:
        dest = create_preset(
            cc_rig_json,
            args.name,
            preset_type=args.preset_type,
        )
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Created {args.preset_type} preset: {dest}")
    return 0


def _preset_install(args: argparse.Namespace) -> int:
    """Install a preset from a local file."""
    from pathlib import Path

    from cc_rig.presets.manager import install_preset

    source = Path(args.path)
    try:
        dest = install_preset(source)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Installed: {dest}")
    return 0


def _main_entry() -> None:
    """Entry point for console_scripts. Handles exit code."""
    sys.exit(main())
