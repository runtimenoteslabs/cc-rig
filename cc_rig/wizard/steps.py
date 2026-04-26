"""Concrete wizard steps for the guided flow.

Each step reads from / writes to a shared ``state`` dict and
returns a ``StepResult`` indicating forward, back, or cancel.
"""

from __future__ import annotations

from typing import Any

from cc_rig.config.detection import detect_project
from cc_rig.presets.manager import (
    BUILTIN_PACKS,
    BUILTIN_TEMPLATES,
    BUILTIN_TIERS,
    load_pack,
    load_workflow,
)
from cc_rig.ui.descriptions import TEMPLATE_DESCRIPTIONS
from cc_rig.ui.prompts import IO, ask_choice, ask_input, confirm
from cc_rig.wizard.stepper import BACK, StepAction, StepResult


def _is_back(value: object) -> bool:
    return value is BACK


# ── Step: Launcher ────────────────────────────────────────────────


class LauncherStep:
    name = "launcher"
    title = "How would you like to start?"

    def execute(self, state: dict[str, Any], io: IO) -> StepResult:
        from cc_rig.wizard.launcher import run_launcher

        mode = run_launcher(io)
        return StepResult(data={"launcher_mode": mode})


# ── Step: Basics ──────────────────────────────────────────────────


class BasicsStep:
    name = "basics"
    title = "Project basics"

    def execute(self, state: dict[str, Any], io: IO) -> StepResult:
        from pathlib import Path

        output_dir = state.get("output_dir", Path("."))
        existing_name = state.get("name", "") or ""

        name = ask_input(
            "Project name",
            existing_name or output_dir.name,
            io=io,
            allow_back=True,
        )
        if _is_back(name):
            return StepResult(action=StepAction.BACK)

        desc = ask_input("Description (optional)", "", io=io, allow_back=True)
        if _is_back(desc):
            return StepResult(action=StepAction.BACK)

        return StepResult(data={"name": name, "desc": desc})


# ── Step: Template ────────────────────────────────────────────────


class TemplateStep:
    name = "template"
    title = "Select your stack"

    def execute(self, state: dict[str, Any], io: IO) -> StepResult:
        from pathlib import Path

        output_dir = state.get("output_dir", Path("."))
        detected = detect_project(output_dir)
        template = None

        if detected.framework:
            io.say(f"\nDetected: {detected.language} / {detected.framework}")
            use_detected = confirm(f"Use {detected.framework}?", io=io, allow_back=True)
            if _is_back(use_detected):
                return StepResult(action=StepAction.BACK)
            if use_detected:
                template = detected.framework

        if not template:
            options = [(t, TEMPLATE_DESCRIPTIONS.get(t, t)) for t in BUILTIN_TEMPLATES]
            template = ask_choice("Select template:", options, "fastapi", io=io, allow_back=True)
            if _is_back(template):
                return StepResult(action=StepAction.BACK)

        return StepResult(data={"template": template})


# ── Step: Workflow ────────────────────────────────────────────────


class WorkflowStep:
    name = "workflow"
    title = "How much structure do you want?"

    def execute(self, state: dict[str, Any], io: IO) -> StepResult:
        descriptions: dict[str, str] = {}
        for w in BUILTIN_TIERS:
            data = load_workflow(w)
            descriptions[w] = data.get("description", w)
        options = [(w, f"{w} - {descriptions[w]}") for w in BUILTIN_TIERS]
        tier = ask_choice("Select tier:", options, "standard", io=io, allow_back=True)
        if _is_back(tier):
            return StepResult(action=StepAction.BACK)
        return StepResult(data={"workflow": tier})


class PackStep:
    name = "pack"
    title = "Add a community process pack?"

    def execute(self, state: dict[str, Any], io: IO) -> StepResult:
        if state.get("workflow") == "quick":
            return StepResult(data={"pack": ""})

        options = [("none", "none - Just the cc-rig workflow")]
        for p in BUILTIN_PACKS:
            data = load_pack(p)
            desc = data.get("description", p)
            skills = len(data.get("process_skills", []))
            options.append((p, f"{p} - {desc} ({skills} skills)"))
        pack = ask_choice(
            "Add a process pack? (optional):", options, "none", io=io, allow_back=True
        )
        if _is_back(pack):
            return StepResult(action=StepAction.BACK)
        return StepResult(data={"pack": "" if pack == "none" else pack})


# ── Step: Review ──────────────────────────────────────────────────


class ReviewStep:
    name = "review"
    title = "Configuration preview"

    def execute(self, state: dict[str, Any], io: IO) -> StepResult:
        from cc_rig.config.defaults import compute_defaults
        from cc_rig.ui.display import format_summary

        config = compute_defaults(
            state["template"],
            state["workflow"],
            project_name=state.get("name", ""),
            project_desc=state.get("desc", ""),
            output_dir=str(state.get("output_dir", ".")),
            process_pack=state.get("pack") or None,
        )
        state["config"] = config
        io.say(format_summary(config))
        return StepResult()


# ── Step: Expert ──────────────────────────────────────────────────


class ExpertStep:
    name = "expert"
    title = "Customize (expert)"

    def execute(self, state: dict[str, Any], io: IO) -> StepResult:
        from cc_rig.wizard.expert import run_expert

        config = state.get("config")
        if config is None:
            return StepResult()

        force_expert = state.get("force_expert", False)
        if force_expert:
            # --expert flag: always enter expert mode, no confirmation needed
            config = run_expert(config, io)
            state["config"] = config
            return StepResult()

        do_customize = confirm("Customize?", default=False, io=io, allow_back=True)
        if _is_back(do_customize):
            return StepResult(action=StepAction.BACK)
        if do_customize:
            config = run_expert(config, io)
            state["config"] = config
        return StepResult()


# ── Step: Skill Packs ────────────────────────────────────────────


class SkillPacksStep:
    name = "skill_packs"
    title = "Optional skill packs"

    def execute(self, state: dict[str, Any], io: IO) -> StepResult:
        from cc_rig.skills.registry import SKILL_PACKS

        want_packs = confirm("Add optional skill packs?", default=False, io=io, allow_back=True)
        if _is_back(want_packs):
            return StepResult(action=StepAction.BACK)
        if not want_packs:
            return StepResult(data={"skill_packs": []})

        template = state.get("template", "")
        options = []
        for pack_name, pack in SKILL_PACKS.items():
            label = f"{pack.label} - {pack.description}"
            recommended = pack.suggested_templates is None or (
                template in (pack.suggested_templates or [])
            )
            if recommended and template:
                label += " (recommended)"
            options.append((pack_name, label))

        selected = []
        for value, label in options:
            pick = confirm(f"  {label}?", default=False, io=io)
            if pick:
                selected.append(value)

        # Apply to config if already computed
        config = state.get("config")
        if config is not None:
            config.skill_packs = list(selected)
            if selected:
                from cc_rig.config.defaults import compute_defaults

                refreshed = compute_defaults(
                    state.get("template", config.template_preset or "fastapi"),
                    state.get("workflow", config.workflow or "standard"),
                    project_name=config.project_name,
                    project_desc=config.project_desc,
                    output_dir=config.output_dir,
                    skill_packs=selected,
                )
                config.recommended_skills = refreshed.recommended_skills
            state["config"] = config

        return StepResult(data={"skill_packs": selected})


# ── Step: Harness ─────────────────────────────────────────────────


class HarnessStep:
    name = "harness"
    title = "Runtime harness"

    def execute(self, state: dict[str, Any], io: IO) -> StepResult:
        from cc_rig.wizard.harness import ask_harness

        config = state.get("config")
        if config is None:
            return StepResult()

        want_harness = confirm("Add runtime harness?", default=False, io=io, allow_back=True)
        if _is_back(want_harness):
            return StepResult(action=StepAction.BACK)
        if want_harness:
            config.harness = ask_harness(io)
            state["config"] = config
        return StepResult()


# ── Step: Confirm ─────────────────────────────────────────────────


class ConfirmStep:
    name = "confirm"
    title = "Generate?"

    def execute(self, state: dict[str, Any], io: IO) -> StepResult:
        proceed = confirm("Generate?", io=io, allow_back=True)
        if _is_back(proceed):
            return StepResult(action=StepAction.BACK)
        if not proceed:
            io.say("Cancelled.")
            return StepResult(action=StepAction.CANCEL)
        return StepResult()
