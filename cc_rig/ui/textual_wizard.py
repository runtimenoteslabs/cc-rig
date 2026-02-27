"""Textual full-screen TUI wizard for cc-rig.

Provides a modern arrow-key, RadioSet-based wizard that replaces the
CLI numbered-list prompts when Textual is installed and stdout is a TTY.

The app collects all wizard data across multiple screens, then returns
a state dict. The existing StepRunner CLI path remains as fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    RadioButton,
    RadioSet,
    SelectionList,
    Static,
    TabbedContent,
    TabPane,
)

from cc_rig.config.schema import VALID_AGENTS, VALID_COMMANDS, VALID_HOOKS
from cc_rig.presets.manager import BUILTIN_TEMPLATES, BUILTIN_WORKFLOWS, load_workflow
from cc_rig.ui.banner import BANNER, BANNER_COMPACT, TAGLINE

# ── CSS ──────────────────────────────────────────────────────────────

APP_CSS = """
Screen {
    background: $surface;
}

#brand-header {
    dock: top;
    height: 3;
    background: $primary;
    color: $text;
    padding: 0 2;
}

#brand-header #brand-logo {
    text-style: bold;
    width: auto;
    content-align: left middle;
}

#brand-header #brand-step {
    content-align: right middle;
    width: 1fr;
}

#body {
    padding: 1 2;
}

.screen-title {
    text-style: bold;
    margin-bottom: 1;
}

.description {
    color: $text-muted;
    margin-bottom: 1;
}

.field-label {
    margin-top: 1;
    margin-bottom: 0;
}

RadioSet {
    margin: 1 0;
}

SelectionList {
    height: 1fr;
    min-height: 10;
    margin: 1 0;
}

TabbedContent {
    height: 1fr;
    min-height: 20;
}

#workflow-details, #harness-details {
    border: solid $primary;
    padding: 1 2;
    min-height: 8;
    margin: 1 0;
}

#banner {
    text-align: center;
    color: $accent;
    margin-bottom: 1;
}

#tagline {
    text-align: center;
    color: $text-muted;
    margin-bottom: 1;
}

#summary-box {
    margin: 1 0;
    padding: 1 2;
    border: solid $primary;
}

.feature-group {
    margin: 1 0;
}

.feature-group Label {
    margin-bottom: 0;
}
"""


# ── Button with Space support ────────────────────────────────────────


class _Button(Button):
    """Button that also activates on Space (standard UI convention)."""

    BINDINGS = [
        *Button.BINDINGS,
        ("space", "press", "Press button"),
    ]


# ── Shared navigation bar ────────────────────────────────────────────


class NavBar(Horizontal):
    """Bottom navigation bar with Next/Back/Cancel buttons."""

    DEFAULT_CSS = """
    NavBar {
        dock: bottom;
        height: auto;
        align: center middle;
        padding: 1 1;
    }
    NavBar _Button {
        margin: 0 1;
    }
    """

    def __init__(self, show_back: bool = True, next_label: str = "Next") -> None:
        super().__init__()
        self._show_back = show_back
        self._next_label = next_label

    def compose(self) -> ComposeResult:
        if self._show_back:
            yield _Button("Back", id="btn-back", variant="default")
        yield _Button(self._next_label, id="btn-next", variant="primary")
        yield _Button("Cancel", id="btn-cancel", variant="error")


# ── Branded header ───────────────────────────────────────────────────


class BrandHeader(Horizontal):
    """Top header bar with compact cc-rig logo and step indicator."""

    DEFAULT_CSS = """
    BrandHeader {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        padding: 0 2;
    }
    BrandHeader #brand-logo {
        text-style: bold;
        width: auto;
        content-align: left middle;
    }
    BrandHeader #brand-step {
        content-align: right middle;
        width: 1fr;
    }
    """

    def __init__(self, step_label: str = "") -> None:
        super().__init__(id="brand-header")
        self._step_label = step_label

    def compose(self) -> ComposeResult:
        yield Static(BANNER_COMPACT, id="brand-logo")
        yield Static(self._step_label, id="brand-step")


# ── Screen 1: Welcome ────────────────────────────────────────────────


class WelcomeScreen(ModalScreen[Optional[dict]]):
    """Launcher screen — choose how to start."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, state: dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        yield BrandHeader(self._state.get("step_label", ""))
        with VerticalScroll(id="body"):
            yield Static(BANNER.strip(), id="banner")
            yield Static(TAGLINE, id="tagline")
            yield Label("How would you like to start?", classes="screen-title")
            yield RadioSet(
                RadioButton("Fresh project — full guided setup", value=True),
                RadioButton("Template picker — pick template + workflow"),
                RadioButton("Load saved config — reuse a previous setup"),
                RadioButton("Load config file — from a .json path"),
                RadioButton("Apply to existing repo — scan and propose"),
                id="launcher-radio",
            )
            yield Label(
                "Tip: Use arrow keys to navigate, Enter to select, Escape to go back.",
                classes="description",
            )
        yield NavBar(show_back=False, next_label="Start")

    def on_mount(self) -> None:
        self.query_one("#launcher-radio", RadioSet).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            modes = ["fresh", "quick", "config", "file", "migrate"]
            radio = self.query_one("#launcher-radio", RadioSet)
            idx = radio.pressed_index if radio.pressed_index >= 0 else 0
            self.dismiss({"launcher_mode": modes[idx]})
        elif event.button.id == "btn-cancel":
            self.dismiss("cancel")

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 2: Basics ─────────────────────────────────────────────────


class BasicsScreen(ModalScreen[Optional[dict]]):
    """Project name and description inputs."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, state: dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        yield BrandHeader(self._state.get("step_label", ""))
        with VerticalScroll(id="body"):
            yield Label("Project basics", classes="screen-title")
            yield Label("Project name:", classes="field-label")
            default_name = self._state.get("name", "") or ""
            yield Input(
                value=default_name,
                placeholder="my-project",
                id="input-name",
            )
            yield Label("Description (optional):", classes="field-label")
            yield Input(
                value=self._state.get("desc", ""),
                placeholder="A brief description",
                id="input-desc",
            )
            yield Label("Output directory:", classes="field-label")
            yield Input(
                value=str(self._state.get("output_dir", ".")),
                placeholder="/path/to/project",
                id="input-output-dir",
            )
        yield NavBar()

    def on_mount(self) -> None:
        self.query_one("#input-name", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            name = self.query_one("#input-name", Input).value.strip()
            if not name:
                self.notify("Project name is required", severity="error")
                return
            desc = self.query_one("#input-desc", Input).value.strip()
            output_dir_raw = self.query_one("#input-output-dir", Input).value.strip() or "."
            self.dismiss({"name": name, "desc": desc, "output_dir": Path(output_dir_raw).resolve()})
        elif event.button.id == "btn-back":
            self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss("cancel")

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 3: Template ───────────────────────────────────────────────


class TemplateScreen(ModalScreen[Optional[dict]]):
    """Select framework/template."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, state: dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        from cc_rig.ui.descriptions import TEMPLATE_DESCRIPTIONS

        yield BrandHeader(self._state.get("step_label", ""))
        detected = self._state.get("detected_framework", "")
        with VerticalScroll(id="body"):
            yield Label("Select your stack", classes="screen-title")
            yield Label(
                "Pick the framework closest to your project. "
                "This controls which language-specific agents, linters, "
                "and test commands are configured.",
                classes="description",
            )
            if detected:
                yield Label(
                    f"Detected: {detected} (highlighted below)",
                    classes="description",
                )
            buttons = []
            for t in BUILTIN_TEMPLATES:
                desc = TEMPLATE_DESCRIPTIONS.get(t, t)
                label = desc
                if t == detected:
                    label = f"{desc} (detected)"
                buttons.append(RadioButton(label, value=(t == (detected or "fastapi"))))
            yield RadioSet(*buttons, id="template-radio")
        yield NavBar()

    def on_mount(self) -> None:
        self.query_one("#template-radio", RadioSet).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            radio = self.query_one("#template-radio", RadioSet)
            idx = radio.pressed_index if radio.pressed_index >= 0 else 0
            template = BUILTIN_TEMPLATES[idx]
            self.dismiss({"template": template})
        elif event.button.id == "btn-back":
            self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss("cancel")

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 4: Workflow ────────────────────────────────────────────────


class WorkflowScreen(ModalScreen[Optional[dict]]):
    """Select workflow preset with educational detail panel."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, state: dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        from cc_rig.ui.descriptions import WORKFLOW_DETAILS

        yield BrandHeader(self._state.get("step_label", ""))
        with VerticalScroll(id="body"):
            yield Label("Select your workflow", classes="screen-title")
            yield Label(
                "Choose how you want to work with Claude Code. "
                "Select a workflow to see details below.",
                classes="description",
            )
            buttons = []
            for i, w in enumerate(BUILTIN_WORKFLOWS):
                data = load_workflow(w)
                desc = data.get("description", w)
                agents = len(data.get("agents", []))
                commands = len(data.get("commands", []))
                label = f"{w} — {desc} ({agents} agents, {commands} cmds)"
                buttons.append(RadioButton(label, value=(w == "standard")))
            yield RadioSet(*buttons, id="workflow-radio")
            # Default to standard details
            default_detail = WORKFLOW_DETAILS.get("standard", "")
            yield Static(default_detail, id="workflow-details")
        yield NavBar()

    def on_mount(self) -> None:
        self.query_one("#workflow-radio", RadioSet).focus()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        from cc_rig.ui.descriptions import WORKFLOW_DETAILS

        idx = event.radio_set.pressed_index
        if idx >= 0 and idx < len(BUILTIN_WORKFLOWS):
            workflow = BUILTIN_WORKFLOWS[idx]
            detail = WORKFLOW_DETAILS.get(workflow, "")
            self.query_one("#workflow-details", Static).update(detail)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            radio = self.query_one("#workflow-radio", RadioSet)
            idx = radio.pressed_index if radio.pressed_index >= 0 else 0
            workflow = BUILTIN_WORKFLOWS[idx]
            self.dismiss({"workflow": workflow})
        elif event.button.id == "btn-back":
            self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss("cancel")

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 5: Review ─────────────────────────────────────────────────


class ReviewScreen(ModalScreen[Optional[dict]]):
    """Show computed config summary. Option to customize."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, state: dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        yield BrandHeader(self._state.get("step_label", ""))
        config = self._state.get("config")
        with VerticalScroll(id="body"):
            yield Label("Review configuration", classes="screen-title")
            yield Label(
                "Your workflow pre-selected agents (specialized AI roles), "
                "commands (slash commands you invoke), and hooks (auto-actions "
                "on events like save, commit, push).",
                classes="description",
            )
            if config:
                yield Static(self._format_config(config), id="summary-box")
            yield Label("")
            yield Checkbox(
                "Customize agents, commands, hooks, and features",
                id="chk-customize",
            )
            yield Label(
                "  Opens expert view to add or remove individual agents, "
                "commands, and hooks, then toggle features like cross-session "
                "memory, spec-driven workflow, GTD task management, and "
                "git worktrees. The defaults above are good for most projects.",
                classes="description",
            )
        yield NavBar()

    def on_mount(self) -> None:
        self.query_one("#chk-customize", Checkbox).focus()

    def _format_config(self, config: Any) -> str:
        lines = [
            f"  Project:    {config.project_name}",
            f"  Stack:      {config.language} / {config.framework}",
            f"  Type:       {config.project_type}",
            f"  Workflow:   {config.workflow}",
            "",
            f"  Agents:     {', '.join(config.agents)}",
            f"  Commands:   {', '.join(config.commands)}",
            f"  Hooks:      {', '.join(config.hooks)}",
            f"  Features:   {self._format_features(config.features)}",
            f"  Skills:     {len(config.recommended_skills)} recommended",
            f"  MCPs:       {', '.join(config.default_mcps) or 'none'}",
        ]
        return "\n".join(lines)

    def _format_features(self, features: Any) -> str:
        flags = []
        if features.memory:
            flags.append("memory")
        if features.spec_workflow:
            flags.append("spec-workflow")
        if features.gtd:
            flags.append("gtd")
        if features.worktrees:
            flags.append("worktrees")
        return ", ".join(flags) or "none"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            chk = self.query_one("#chk-customize", Checkbox)
            self.dismiss({"wants_expert": chk.value})
        elif event.button.id == "btn-back":
            self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss("cancel")

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 6: Expert ─────────────────────────────────────────────────


class ExpertScreen(ModalScreen[Optional[dict]]):
    """Multi-select for agents, commands, and hooks — organized in tabs."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, state: dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        from cc_rig.ui.descriptions import (
            get_agent_descriptions,
            get_command_descriptions,
            get_hook_descriptions,
        )

        yield BrandHeader(self._state.get("step_label", ""))
        config = self._state.get("config")
        current_agents = config.agents if config else []
        current_commands = config.commands if config else []
        current_hooks = config.hooks if config else []

        agent_descs = get_agent_descriptions()
        command_descs = get_command_descriptions()
        hook_descs = get_hook_descriptions()

        with VerticalScroll(id="body"):
            yield Label("Expert customization", classes="screen-title")
            yield Label(
                "Select agents, commands, and hooks for your project.",
                classes="description",
            )

            with TabbedContent(id="expert-tabs"):
                with TabPane(f"Agents ({len(current_agents)})", id="tab-agents"):
                    yield SelectionList[str](
                        *[
                            (
                                f"{a} — {agent_descs.get(a, '')}",
                                a,
                                a in current_agents,
                            )
                            for a in sorted(VALID_AGENTS)
                        ],
                        id="sel-agents",
                    )
                with TabPane(f"Commands ({len(current_commands)})", id="tab-commands"):
                    yield SelectionList[str](
                        *[
                            (
                                f"{c} — {command_descs.get(c, '')}",
                                c,
                                c in current_commands,
                            )
                            for c in sorted(VALID_COMMANDS)
                        ],
                        id="sel-commands",
                    )
                with TabPane(f"Hooks ({len(current_hooks)})", id="tab-hooks"):
                    yield SelectionList[str](
                        *[
                            (
                                f"{h} — {hook_descs.get(h, '')}",
                                h,
                                h in current_hooks,
                            )
                            for h in sorted(VALID_HOOKS)
                        ],
                        id="sel-hooks",
                    )
        yield NavBar()

    def on_mount(self) -> None:
        agents_list = self.query_one("#sel-agents", SelectionList)
        agents_list.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            agents = list(self.query_one("#sel-agents", SelectionList).selected)
            commands = list(self.query_one("#sel-commands", SelectionList).selected)
            hooks = list(self.query_one("#sel-hooks", SelectionList).selected)
            self.dismiss(
                {
                    "expert_agents": agents,
                    "expert_commands": commands,
                    "expert_hooks": hooks,
                }
            )
        elif event.button.id == "btn-back":
            self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss("cancel")

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 6b: Features ──────────────────────────────────────────────


class FeaturesScreen(ModalScreen[Optional[dict]]):
    """Feature flag toggles — memory, spec-workflow, GTD, worktrees."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, state: dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        from cc_rig.ui.descriptions import FEATURE_DETAILS, WORKFLOW_FEATURE_DEFAULTS

        yield BrandHeader(self._state.get("step_label", ""))
        config = self._state.get("config")
        features = config.features if config else None
        workflow = self._state.get("workflow", "standard")
        recommended = WORKFLOW_FEATURE_DEFAULTS.get(workflow, set())

        with VerticalScroll(id="body"):
            yield Label("Features", classes="screen-title")
            yield Label(
                "Each feature adds the agents, commands, and hooks it needs "
                "automatically. Your workflow pre-enabled the ones marked "
                "below — toggle any on or off.",
                classes="description",
            )

            for detail in FEATURE_DETAILS:
                key = detail["key"]
                current_val = getattr(features, key, False) if features else False
                label = detail["label"]
                if key in recommended:
                    label += "  ★ your workflow enables this"
                yield Checkbox(
                    label,
                    value=current_val,
                    id=detail["widget_id"],
                )
                yield Label(
                    f"  {detail['description']}\n  Adds: {detail['adds']}",
                    classes="description",
                )
        yield NavBar()

    def on_mount(self) -> None:
        self.query_one("#feat-memory", Checkbox).focus()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Enforce mutual exclusion: spec-workflow and GTD cannot both be on."""
        if event.checkbox.id == "feat-spec" and event.value:
            self.query_one("#feat-gtd", Checkbox).value = False
        elif event.checkbox.id == "feat-gtd" and event.value:
            self.query_one("#feat-spec", Checkbox).value = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            self.dismiss(
                {
                    "expert_features": {
                        "memory": self.query_one("#feat-memory", Checkbox).value,
                        "spec_workflow": self.query_one("#feat-spec", Checkbox).value,
                        "gtd": self.query_one("#feat-gtd", Checkbox).value,
                        "worktrees": self.query_one("#feat-worktrees", Checkbox).value,
                    },
                }
            )
        elif event.button.id == "btn-back":
            self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss("cancel")

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 6c: Skill Packs ──────────────────────────────────────────


class SkillPacksScreen(ModalScreen[Optional[dict]]):
    """Optional skill packs — deeper coverage for specific domains."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, state: dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        from cc_rig.skills.registry import SKILL_PACKS

        yield BrandHeader(self._state.get("step_label", ""))
        template = self._state.get("template", "")

        with VerticalScroll(id="body"):
            yield Label("Optional skill packs", classes="screen-title")
            yield Label(
                "Add deeper coverage for specific domains. "
                "These are opt-in and extend your base skill set.",
                classes="description",
            )

            for pack_name, pack in SKILL_PACKS.items():
                label = f"{pack.label} — {pack.description}"
                recommended = pack.suggested_templates is None or (
                    template in (pack.suggested_templates or [])
                )
                if recommended and template:
                    label += "  ★ recommended for your stack"
                yield Checkbox(
                    label,
                    value=False,
                    id=f"pack-{pack_name}",
                )
        yield NavBar()

    def on_mount(self) -> None:
        from cc_rig.skills.registry import SKILL_PACKS

        first_pack = next(iter(SKILL_PACKS), None)
        if first_pack:
            self.query_one(f"#pack-{first_pack}", Checkbox).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from cc_rig.skills.registry import SKILL_PACKS

        if event.button.id == "btn-next":
            selected = []
            for pack_name in SKILL_PACKS:
                chk = self.query_one(f"#pack-{pack_name}", Checkbox)
                if chk.value:
                    selected.append(pack_name)
            self.dismiss({"skill_packs": selected})
        elif event.button.id == "btn-back":
            self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss("cancel")

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 7: Harness ────────────────────────────────────────────────


class HarnessScreen(ModalScreen[Optional[dict]]):
    """Select runtime harness level (B0-B3) with educational detail panel."""

    _LEVELS = ["none", "lite", "standard", "autonomy"]

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, state: dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        from cc_rig.ui.descriptions import HARNESS_DETAILS

        yield BrandHeader(self._state.get("step_label", ""))
        config = self._state.get("config")
        has_autonomy_hook = "autonomy-loop" in (config.hooks if config else [])

        with VerticalScroll(id="body"):
            yield Label("Runtime harness", classes="screen-title")
            yield Label(
                "Your workflow chose what tools Claude has (agents, commands, hooks). "
                "The harness controls how strictly Claude is supervised — budgets, "
                "quality gates, and autonomous looping. Each level builds on the "
                "previous one.",
                classes="description",
            )
            if config and not has_autonomy_hook:
                yield Label(
                    "Note: Selecting Autonomy (B3) will automatically enable "
                    "the autonomy-loop hook.",
                    classes="description",
                )
            yield RadioSet(
                RadioButton(
                    "None (B0) — Scaffold only, you drive",
                    value=True,
                ),
                RadioButton("Lite (B1) — Task tracking + budget awareness"),
                RadioButton("Standard (B2) — Verification gates (tests + lint must pass)"),
                RadioButton("Autonomy (B3) — Autonomous iteration with safety rails"),
                id="harness-radio",
            )
            default_detail = HARNESS_DETAILS.get("none", "")
            yield Static(default_detail, id="harness-details")
        yield NavBar()

    def on_mount(self) -> None:
        self.query_one("#harness-radio", RadioSet).focus()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        from cc_rig.ui.descriptions import HARNESS_DETAILS

        idx = event.radio_set.pressed_index
        if 0 <= idx < len(self._LEVELS):
            level = self._LEVELS[idx]
            detail = HARNESS_DETAILS.get(level, "")
            self.query_one("#harness-details", Static).update(detail)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            radio = self.query_one("#harness-radio", RadioSet)
            idx = radio.pressed_index if radio.pressed_index >= 0 else 0
            level = self._LEVELS[idx]
            if level == "autonomy":
                self.notify(
                    "Autonomy mode enables autonomous iteration with safety rails.",
                    severity="warning",
                )
            self.dismiss({"harness_level": level})
        elif event.button.id == "btn-back":
            self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss("cancel")

    def action_go_back(self) -> None:
        self.dismiss(None)


# ── Screen 8: Confirm ────────────────────────────────────────────────


class ConfirmScreen(ModalScreen[Optional[dict]]):
    """Final confirmation before generation."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, state: dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        yield BrandHeader(self._state.get("step_label", ""))
        config = self._state.get("config")
        with VerticalScroll(id="body"):
            yield Label("Ready to generate", classes="screen-title")
            if config:
                out = self._state.get("output_dir", ".")
                yield Static(
                    f"  Project:  {config.project_name}\n"
                    f"  Stack:    {config.language} / {config.framework}\n"
                    f"  Workflow: {config.workflow}\n"
                    f"  Harness:  {config.harness.level}\n"
                    f"  Output:   {out}",
                    id="summary-box",
                )
            yield Label("")
        yield _ConfirmNavBar()

    def on_mount(self) -> None:
        self.query_one("#btn-next", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            self.dismiss({"confirmed": True})
        elif event.button.id == "btn-save":
            self._save_config()
        elif event.button.id == "btn-back":
            self.dismiss(None)
        elif event.button.id == "btn-cancel":
            self.dismiss("cancel")

    def _save_config(self) -> None:
        config = self._state.get("config")
        if config is None:
            self.notify("No configuration to save", severity="error")
            return
        try:
            from cc_rig.config.manager import save_config

            dest = save_config(config)
            self.notify(f"Config saved: {dest}", severity="information")
        except OSError as exc:
            self.notify(f"Save failed: {exc}", severity="error")

    def action_go_back(self) -> None:
        self.dismiss(None)


class _ConfirmNavBar(Horizontal):
    """Navigation bar for ConfirmScreen with Save Config button."""

    DEFAULT_CSS = """
    _ConfirmNavBar {
        dock: bottom;
        height: auto;
        align: center middle;
        padding: 1 1;
    }
    _ConfirmNavBar _Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield _Button("Back", id="btn-back", variant="default")
        yield _Button("Save Config", id="btn-save", variant="default")
        yield _Button("Generate", id="btn-next", variant="primary")
        yield _Button("Cancel", id="btn-cancel", variant="error")


# ── Main WizardApp ───────────────────────────────────────────────────

# Screen definitions for the guided flow.
# Each entry: (screen_class, step_title, condition_fn_or_None)
# condition_fn receives state and returns True to show the screen.


def _wants_expert(s: dict[str, Any]) -> bool:
    return bool(s.get("wants_expert") or s.get("force_expert"))


_GUIDED_SCREENS: list[tuple[type, str, Any]] = [
    (WelcomeScreen, "Welcome", None),
    (BasicsScreen, "Project basics", None),
    (TemplateScreen, "Select your stack", None),
    (WorkflowScreen, "Select your workflow", None),
    (ReviewScreen, "Review configuration", None),
    (SkillPacksScreen, "Skill packs", None),
    (ExpertScreen, "Customize", _wants_expert),
    (FeaturesScreen, "Features", _wants_expert),
    (HarnessScreen, "Runtime harness", None),
    (ConfirmScreen, "Confirm", None),
]

_QUICK_SCREENS: list[tuple[type, str, Any]] = [
    (TemplateScreen, "Select your stack", None),
    (WorkflowScreen, "Select your workflow", None),
    (BasicsScreen, "Project name", None),
    (ReviewScreen, "Review configuration", None),
    (SkillPacksScreen, "Skill packs", None),
    (ExpertScreen, "Customize", _wants_expert),
    (FeaturesScreen, "Features", _wants_expert),
    (ConfirmScreen, "Confirm", None),
]


class WizardApp(App[Optional[dict]]):
    """Full-screen TUI wizard. Returns state dict or None if cancelled."""

    CSS = APP_CSS
    TITLE = "cc-rig"

    def __init__(
        self,
        initial_state: dict[str, Any] | None = None,
        screens: list[tuple[type, str, Any]] | None = None,
    ) -> None:
        super().__init__()
        self._initial_state = dict(initial_state or {})
        self._screens = screens or _GUIDED_SCREENS
        # Parent context for returning from quick flow to guided flow
        self._parent_screens: list[tuple[type, str, Any]] | None = None
        self._parent_step: int = 0

    def on_mount(self) -> None:
        self._run_wizard()

    @work
    async def _run_wizard(self) -> None:
        state = dict(self._initial_state)
        step = 0

        while step < len(self._screens):
            screen_cls, title, condition = self._screens[step]

            # Skip screens whose condition is not met
            if condition is not None and not condition(state):
                step += 1
                continue

            total = len(self._screens)
            state["step_label"] = f"  Step {step + 1} of {total} — {title}"

            # Compute config before review/confirm screens need it
            if screen_cls in (ReviewScreen, ConfirmScreen) and "config" not in state:
                state = self._compute_config(state)

            result = await self.push_screen_wait(screen_cls(state))

            if result is None:
                # Back navigation
                if step == 0 and self._parent_screens is not None:
                    # Return from quick flow to parent (guided) flow
                    self._screens = self._parent_screens
                    step = self._parent_step
                    self._parent_screens = None
                    self._parent_step = 0
                else:
                    step = max(0, step - 1)
                    # Skip back over conditional screens that were skipped forward
                    while step > 0:
                        _, _, cond = self._screens[step]
                        if cond is not None and not cond(state):
                            step -= 1
                        else:
                            break
                continue

            if result == "cancel":
                self.exit(None)
                return

            state.update(result)

            # After template or workflow change, recompute config
            if screen_cls in (TemplateScreen, WorkflowScreen):
                if "template" in state and "workflow" in state:
                    state = self._compute_config(state)

            # Apply skill pack selections
            if screen_cls is SkillPacksScreen:
                state = self._apply_skill_packs(state)

            # Apply expert overrides
            if screen_cls in (ExpertScreen, FeaturesScreen):
                state = self._apply_expert(state)

            # Apply harness selection
            if screen_cls is HarnessScreen:
                state = self._apply_harness(state)

            # Handle launcher mode selection
            if screen_cls is WelcomeScreen:
                mode = state.get("launcher_mode", "fresh")
                if mode == "migrate":
                    # Run detection, store result, continue through wizard
                    state = self._run_detection(state)
                    # Fall through to normal Basics → Template → ... flow
                elif mode == "quick":
                    # Save parent context so Back from step 0 returns here
                    self._parent_screens = list(self._screens)
                    self._parent_step = step
                    # Swap to quick screen sequence and restart
                    self._screens = _QUICK_SCREENS
                    step = 0
                    continue
                elif mode in ("config", "file"):
                    # These need CLI input — exit TUI
                    self.exit(state)
                    return

            step += 1

        self.exit(state)

    def _run_detection(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run project detection and store results in state."""
        from cc_rig.config.detection import detect_project

        output_dir = state.get("output_dir", ".")
        detected = detect_project(output_dir)
        if detected.framework:
            state["detected_framework"] = detected.framework
            state["detected_language"] = detected.language
            self.notify(
                f"Detected: {detected.language} / {detected.framework}",
                severity="information",
            )
        else:
            lang_msg = f" ({detected.language})" if detected.language else ""
            self.notify(
                f"Could not auto-detect framework{lang_msg}. Please select a template.",
                severity="warning",
            )
        return state

    def _compute_config(self, state: dict[str, Any]) -> dict[str, Any]:
        """Build ProjectConfig from current state selections."""
        from cc_rig.config.defaults import compute_defaults

        template = state.get("template", "fastapi")
        workflow = state.get("workflow", "standard")
        try:
            config = compute_defaults(
                template,
                workflow,
                project_name=state.get("name", ""),
                project_desc=state.get("desc", ""),
                output_dir=str(state.get("output_dir", ".")),
            )
            state["config"] = config
        except (KeyError, ValueError):
            pass
        return state

    def _apply_expert(self, state: dict[str, Any]) -> dict[str, Any]:
        """Apply expert screen selections to config."""
        from cc_rig.config.project import Features

        config = state.get("config")
        if config is None:
            return state

        if "expert_agents" in state:
            config.agents = state["expert_agents"]
        if "expert_commands" in state:
            config.commands = state["expert_commands"]
        if "expert_hooks" in state:
            config.hooks = state["expert_hooks"]
        if "expert_features" in state:
            config.features = Features(**state["expert_features"])

        state["config"] = config
        return state

    def _apply_skill_packs(self, state: dict[str, Any]) -> dict[str, Any]:
        """Apply skill pack selections to config and recompute recommended_skills."""
        config = state.get("config")
        if config is None:
            return state

        selected_packs = state.get("skill_packs", [])
        config.skill_packs = list(selected_packs)

        # Recompute recommended_skills with packs included
        if selected_packs:
            from cc_rig.config.defaults import compute_defaults

            template = state.get("template", config.template_preset or "fastapi")
            workflow = state.get("workflow", config.workflow or "standard")
            refreshed = compute_defaults(
                template,
                workflow,
                project_name=config.project_name,
                project_desc=config.project_desc,
                output_dir=config.output_dir,
                skill_packs=selected_packs,
            )
            config.recommended_skills = refreshed.recommended_skills

        state["config"] = config
        return state

    def _apply_harness(self, state: dict[str, Any]) -> dict[str, Any]:
        """Apply harness level to config.

        B3 (autonomy) automatically adds the autonomy-loop hook if missing.
        """
        from cc_rig.config.project import HarnessConfig

        config = state.get("config")
        if config is None:
            return state

        level = state.get("harness_level", "none")
        config.harness = HarnessConfig(level=level)

        # B3 requires the autonomy-loop hook — add it automatically
        if level == "autonomy" and "autonomy-loop" not in config.hooks:
            config.hooks = list(config.hooks) + ["autonomy-loop"]

        state["config"] = config
        return state


# ── Quick flow app ───────────────────────────────────────────────────


class QuickWizardApp(WizardApp):
    """Simplified 4-screen wizard for --quick mode."""

    def __init__(self, initial_state: dict[str, Any] | None = None) -> None:
        super().__init__(initial_state=initial_state, screens=_QUICK_SCREENS)


# ── Detection helper ─────────────────────────────────────────────────


def should_use_textual(io: Any = None) -> bool:
    """Check if we should use the Textual TUI.

    Returns True when:
      - textual is importable
      - stdout is a TTY
      - io is not a test-injected IO object
    """
    import sys

    from cc_rig.ui.tui import HAS_TEXTUAL

    if not HAS_TEXTUAL:
        return False

    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False

    # Don't use Textual if io has been injected (test mode)
    if io is not None:
        from cc_rig.ui.prompts import IO

        if isinstance(io, IO) and io._input is not input:
            return False

    return True
