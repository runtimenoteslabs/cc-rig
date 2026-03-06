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
from textual.binding import Binding
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
from cc_rig.plugins.registry import PLUGIN_CATALOG, WORKFLOW_PLUGINS
from cc_rig.presets.manager import BUILTIN_TEMPLATES, BUILTIN_WORKFLOWS, load_workflow
from cc_rig.ui.banner import BANNER, BANNER_COMPACT, TAGLINE


class AutoSelectRadioSet(RadioSet):
    """RadioSet that selects on arrow-key navigation (no extra Space needed).

    Standard Textual RadioSet separates highlight (arrow keys) from selection
    (Space/Enter). This subclass rebinds arrow keys to navigate-and-toggle,
    matching native OS radio-button behavior (GTK, macOS, Windows).
    Also fixes VHS demo recordings where arrow keys highlight but don't select.

    Note: We add new bindings rather than overriding action_next/previous_button
    because RadioSet._on_mount() calls action_next_button() to set the initial
    highlight — overriding that would break the initial selection logic.
    """

    BINDINGS = [
        Binding("down,right", "next_and_select", "Next option", show=False),
        Binding("enter,space", "toggle_button", "Toggle", show=False),
        Binding("up,left", "previous_and_select", "Previous option", show=False),
    ]

    def action_next_and_select(self) -> None:
        """Navigate to the next button and select it."""
        self.action_next_button()
        self.action_toggle_button()

    def action_previous_and_select(self) -> None:
        """Navigate to the previous button and select it."""
        self.action_previous_button()
        self.action_toggle_button()


# ── CSS ──────────────────────────────────────────────────────────────

APP_CSS = """
Screen {
    background: $surface;
}

#brand-header {
    dock: top;
    height: 1;
    background: #0d7377;
    color: #ffffff;
    padding: 0 2;
}

#brand-header #brand-logo {
    text-style: bold;
    color: #ffffff;
    width: auto;
    content-align: left middle;
}

#brand-header #brand-step {
    color: #b0d0d0;
    content-align: right middle;
    width: 1fr;
}

#body {
    padding: 2 3;
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
    scrollbar-color: #0d7377;
    scrollbar-color-hover: #10999e;
    scrollbar-color-active: #10999e;
}

TabbedContent {
    height: 1fr;
    min-height: 20;
}

#workflow-details {
    border: solid #0d7377;
    border-left: thick #10999e;
    padding: 1 2;
    min-height: 5;
    max-height: 16;
    overflow-y: auto;
    margin: 1 0;
}

#harness-details {
    border: solid #0d7377;
    border-left: thick #10999e;
    padding: 1 2;
    min-height: 5;
    max-height: 22;
    overflow-y: auto;
    margin: 1 0;
}

#banner {
    text-align: center;
    color: #5eeaef;
    text-style: bold;
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
    border: solid #0d7377;
}

.feature-group {
    margin: 1 0;
}

.feature-group Label {
    margin-bottom: 0;
}

Checkbox > .toggle--button {
    color: #555555;
}

Checkbox.-on > .toggle--button {
    color: #ffffff;
    text-style: bold;
}

RadioSet RadioButton > .toggle--button {
    color: #555555;
}

RadioSet RadioButton.-on > .toggle--button {
    color: #ffffff;
    text-style: bold;
}

Input:focus {
    border: tall #10999e;
}

_Button.-primary {
    background: #0d7377;
    color: #ffffff;
}

_Button.-primary:hover {
    background: #15b5ba;
    color: #ffffff;
}

_Button.-primary:focus {
    background: #ffffff;
    color: #0d7377;
    text-style: bold;
}

#feature-details {
    border: solid #0d7377;
    border-left: thick #10999e;
    padding: 1 2;
    min-height: 5;
    max-height: 16;
    overflow-y: auto;
    margin: 1 0;
}

.hidden {
    display: none;
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
    NavBar .spacer {
        width: 1fr;
    }
    """

    def __init__(self, show_back: bool = True, next_label: str = "Next") -> None:
        super().__init__()
        self._show_back = show_back
        self._next_label = next_label

    def compose(self) -> ComposeResult:
        if self._show_back:
            yield _Button("Back", id="btn-back", variant="default")
        yield Static("", classes="spacer")
        yield _Button(self._next_label, id="btn-next", variant="primary")
        yield _Button("Cancel", id="btn-cancel", variant="error")


# ── Persistent keyboard hints ────────────────────────────────────────


class KeyHintsBar(Static):
    """Persistent keyboard hints shown on all screens."""

    DEFAULT_CSS = """
    KeyHintsBar {
        dock: bottom;
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        content-align: center middle;
        padding: 0 2;
    }
    """

    def __init__(self) -> None:
        super().__init__(" ESC Back  |  TAB Navigate  |  ENTER Select  |  SPACE Toggle ")


# ── Branded header ───────────────────────────────────────────────────


class BrandHeader(Horizontal):
    """Top header bar with compact cc-rig logo and step indicator."""

    DEFAULT_CSS = """
    BrandHeader {
        dock: top;
        height: 1;
        background: #0d7377;
        color: #ffffff;
        padding: 0 2;
    }
    BrandHeader #brand-logo {
        text-style: bold;
        color: #ffffff;
        width: auto;
        content-align: left middle;
    }
    BrandHeader #brand-step {
        color: #b0d0d0;
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
            yield AutoSelectRadioSet(
                RadioButton("Fresh project - full guided setup", value=True),
                RadioButton("Template picker - pick template + workflow"),
                RadioButton("Load saved config - reuse a previous setup"),
                RadioButton("Load config file - from a .json path"),
                RadioButton("Apply to existing repo - scan and propose"),
                id="launcher-radio",
            )
        yield NavBar(show_back=False, next_label="Start")
        yield KeyHintsBar()

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
        yield KeyHintsBar()

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
                "Determines tool commands, agent docs, and framework-specific rules.",
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
                selected = self._state.get("template", detected or "fastapi")
                buttons.append(RadioButton(label, value=(t == selected)))
            yield AutoSelectRadioSet(*buttons, id="template-radio")
        yield NavBar()
        yield KeyHintsBar()

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
                "Controls which agents, commands, hooks, plugins, and features are generated.",
                classes="description",
            )
            buttons = []
            for i, w in enumerate(BUILTIN_WORKFLOWS):
                data = load_workflow(w)
                desc = data.get("description", w)
                agents = len(data.get("agents", []))
                commands = len(data.get("commands", []))
                plugins = len(WORKFLOW_PLUGINS.get(w, []))
                label = f"{w} - {desc} ({agents} agents, {commands} cmds, {plugins} plugins)"
                selected = self._state.get("workflow", "standard")
                buttons.append(RadioButton(label, value=(w == selected)))
            yield AutoSelectRadioSet(*buttons, id="workflow-radio")
            # Show details for the selected workflow
            default_detail = WORKFLOW_DETAILS.get(self._state.get("workflow", "standard"), "")
            yield Static(default_detail, id="workflow-details")
        yield NavBar()
        yield KeyHintsBar()

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


# ── Config summary helper ────────────────────────────────────────────


def _format_config_summary(config: Any, output_dir: str = ".") -> str:
    """Format config for display in ReviewScreen and ConfirmScreen."""
    flags = []
    for name, attr in [
        ("Memory", "memory"),
        ("Spec workflow", "spec_workflow"),
        ("GTD", "gtd"),
        ("Worktrees", "worktrees"),
    ]:
        if getattr(config.features, attr, False):
            flags.append(name)
    features_str = ", ".join(flags) or "none"

    lines = [
        f"  Project:    {config.project_name}",
        f"  Stack:      {config.language} / {config.framework}",
        f"  Type:       {config.project_type}",
        f"  Workflow:   {config.workflow}",
        "",
        f"  Agents:     {len(config.agents)}",
        f"  Commands:   {len(config.commands)}",
        f"  Hooks:      {len(config.hooks)}",
        f"  Features:   {features_str}",
        f"  Skills:     {len(config.recommended_skills)} recommended",
        f"  Plugins:    {len(config.recommended_plugins)}",
        f"  MCPs:       {len(config.default_mcps)}",
        f"  Harness:    {config.harness.level}",
        f"  Output:     {output_dir}",
    ]
    return "\n".join(lines)


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
            yield Label("Configuration preview", classes="screen-title")
            yield Label(
                "Review your selections, then decide whether to customize.",
                classes="description",
            )
            if config:
                yield Static(_format_config_summary(config), id="summary-box")
            yield Label("")
            yield Label("Expert mode", classes="screen-title")
            yield Checkbox(
                "Customize agents, commands, hooks, plugins and features",
                id="chk-customize",
            )
            yield Label(
                "  Add or remove individual agents, commands, hooks and plugins\n"
                "  Toggle features: memory, spec workflow, GTD, worktrees\n"
                "  The defaults above work well for most projects",
                classes="description",
            )
        yield NavBar()
        yield KeyHintsBar()

    def on_mount(self) -> None:
        self.query_one("#chk-customize", Checkbox).focus()

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
            get_plugin_descriptions,
        )

        yield BrandHeader(self._state.get("step_label", ""))
        config = self._state.get("config")
        current_agents = config.agents if config else []
        current_commands = config.commands if config else []
        current_hooks = config.hooks if config else []
        current_plugin_names = {p.name for p in config.recommended_plugins} if config else set()

        agent_descs = get_agent_descriptions()
        command_descs = get_command_descriptions()
        hook_descs = get_hook_descriptions()
        plugin_descs = get_plugin_descriptions()

        # Exclude autonomy plugins (ralph-loop managed by harness)
        available_plugins = {k: v for k, v in PLUGIN_CATALOG.items() if v.category != "autonomy"}

        agents_label = f"Agents ({len(current_agents)}/{len(VALID_AGENTS)} selected)"
        cmds_label = f"Commands ({len(current_commands)}/{len(VALID_COMMANDS)} selected)"
        plugins_label = f"Plugins ({len(current_plugin_names)}/{len(available_plugins)} selected)"
        hooks_label = f"Hooks ({len(current_hooks)}/{len(VALID_HOOKS)} selected)"

        with VerticalScroll(id="body"):
            yield Label("Expert customization", classes="screen-title")
            yield Label(
                "Select agents, commands, plugins and hooks for your project.",
                classes="description",
            )

            with TabbedContent(id="expert-tabs"):
                with TabPane(agents_label, id="tab-agents"):
                    yield SelectionList[str](
                        *[
                            (
                                f"{a} - {agent_descs.get(a, '')}",
                                a,
                                a in current_agents,
                            )
                            for a in sorted(VALID_AGENTS)
                        ],
                        id="sel-agents",
                    )
                with TabPane(cmds_label, id="tab-commands"):
                    yield SelectionList[str](
                        *[
                            (
                                f"{c} - {command_descs.get(c, '')}",
                                c,
                                c in current_commands,
                            )
                            for c in sorted(VALID_COMMANDS)
                        ],
                        id="sel-commands",
                    )
                with TabPane(plugins_label, id="tab-plugins"):
                    yield SelectionList[str](
                        *[
                            (
                                f"{name} - {plugin_descs.get(name, '')}",
                                name,
                                name in current_plugin_names,
                            )
                            for name in sorted(available_plugins)
                        ],
                        id="sel-plugins",
                    )
                with TabPane(hooks_label, id="tab-hooks"):
                    yield SelectionList[str](
                        *[
                            (
                                f"{h} - {hook_descs.get(h, '')}",
                                h,
                                h in current_hooks,
                            )
                            for h in sorted(VALID_HOOKS)
                        ],
                        id="sel-hooks",
                    )
        yield NavBar()
        yield KeyHintsBar()

    def on_mount(self) -> None:
        agents_list = self.query_one("#sel-agents", SelectionList)
        agents_list.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            agents = list(self.query_one("#sel-agents", SelectionList).selected)
            commands = list(self.query_one("#sel-commands", SelectionList).selected)
            hooks = list(self.query_one("#sel-hooks", SelectionList).selected)
            plugins = list(self.query_one("#sel-plugins", SelectionList).selected)
            self.dismiss(
                {
                    "expert_agents": agents,
                    "expert_commands": commands,
                    "expert_hooks": hooks,
                    "expert_plugins": plugins,
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
                "Toggle optional capabilities. Each adds files and hooks.",
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

            # Detail panel — updates on focus/change
            first = FEATURE_DETAILS[0]
            initial_text = f"{first['description']}\n\nAdds: {first['adds']}"
            yield Static(initial_text, id="feature-details")
        yield NavBar()
        yield KeyHintsBar()

    def on_mount(self) -> None:
        self.query_one("#feat-memory", Checkbox).focus()

    def on_descendant_focus(self, event: Any) -> None:
        widget = event.widget
        if hasattr(widget, "id") and widget.id and widget.id.startswith("feat-"):
            self._update_detail(widget.id)

    def _update_detail(self, widget_id: str) -> None:
        from cc_rig.ui.descriptions import FEATURE_DETAILS

        for detail in FEATURE_DETAILS:
            if detail["widget_id"] == widget_id:
                text = f"{detail['description']}\n\nAdds: {detail['adds']}"
                self.query_one("#feature-details", Static).update(text)
                break

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
        config = self._state.get("config")
        base_count = len(config.recommended_skills) if config else 0

        with VerticalScroll(id="body"):
            yield Label("Optional skill packs", classes="screen-title")
            if base_count:
                yield Label(
                    f"Your stack already includes {base_count} skills. "
                    "Packs add specialized knowledge for specific domains.",
                    classes="description",
                )
            else:
                yield Label(
                    "Packs add specialized knowledge for specific domains.",
                    classes="description",
                )

            for pack_name, pack in SKILL_PACKS.items():
                n_skills = len(pack.skill_names)
                label = f"{pack.label} ({n_skills} skills) - {pack.description}"
                recommended = pack.suggested_templates is None or (
                    template in (pack.suggested_templates or [])
                )
                if recommended and template:
                    label += "  ★ recommended for your stack"
                prev_packs = self._state.get("skill_packs", [])
                yield Checkbox(
                    label,
                    value=(pack_name in prev_packs),
                    id=f"pack-{pack_name}",
                )
        yield NavBar()
        yield KeyHintsBar()

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
    """Select runtime harness level (B0-B3 + ralph-loop) with educational detail panel."""

    _LEVELS = ["none", "lite", "standard", "autonomy", "ralph-loop"]
    _FEATURE_LEVELS = {"ralph-loop", "custom"}

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, state: dict[str, Any]) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        from cc_rig.ui.descriptions import HARNESS_DETAILS

        yield BrandHeader(self._state.get("step_label", ""))

        with VerticalScroll(id="body"):
            yield Label("Runtime harness", classes="screen-title")
            yield Label(
                "Controls supervision level: budgets, quality gates and autonomous looping.",
                classes="description",
            )
            prev_level = self._state.get("harness_level", "none")
            yield AutoSelectRadioSet(
                RadioButton(
                    "None (B0) - Scaffold only, you drive",
                    value=(prev_level == "none"),
                ),
                RadioButton(
                    "Lite (B1) - Task tracking + budget awareness",
                    value=(prev_level == "lite"),
                ),
                RadioButton(
                    "Standard (B2) - Verification gates (tests + lint must pass)",
                    value=(prev_level == "standard"),
                ),
                RadioButton(
                    "Autonomy (B3) - Autonomous iteration with safety rails",
                    value=(prev_level == "autonomy"),
                ),
                RadioButton(
                    "Ralph Loop - Official Anthropic autonomous loop (plugin)",
                    value=(prev_level == "ralph-loop"),
                ),
                id="harness-radio",
            )
            default_detail = HARNESS_DETAILS.get(prev_level, "")
            yield Static(default_detail, id="harness-details")

            # B1/B2 feature checkboxes — shown for ralph-loop and custom
            show_features = prev_level in self._FEATURE_LEVELS
            yield Label(
                "Select individual features:",
                id="harness-features-label",
                classes="" if show_features else "hidden",
            )
            yield Checkbox(
                "Task tracking (todo.md + session-tasks hook)",
                value=self._state.get("harness_task_tracking", True),
                id="harness-task-tracking",
                classes="" if show_features else "hidden",
            )
            yield Checkbox(
                "Budget awareness (budget-reminder hook)",
                value=self._state.get("harness_budget_awareness", True),
                id="harness-budget-awareness",
                classes="" if show_features else "hidden",
            )
            yield Checkbox(
                "Verification gates (commit-gate hook + init-sh.sh)",
                value=self._state.get("harness_verification_gates", False),
                id="harness-verification-gates",
                classes="" if show_features else "hidden",
            )
        yield NavBar()
        yield KeyHintsBar()

    def on_mount(self) -> None:
        self.query_one("#harness-radio", RadioSet).focus()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        from cc_rig.ui.descriptions import HARNESS_DETAILS

        idx = event.radio_set.pressed_index
        if 0 <= idx < len(self._LEVELS):
            level = self._LEVELS[idx]
            detail = HARNESS_DETAILS.get(level, "")
            self.query_one("#harness-details", Static).update(detail)
            # Show/hide B1/B2 feature checkboxes
            show = level in self._FEATURE_LEVELS
            for wid in (
                "#harness-features-label",
                "#harness-task-tracking",
                "#harness-budget-awareness",
                "#harness-verification-gates",
            ):
                widget = self.query_one(wid)
                if show:
                    widget.remove_class("hidden")
                else:
                    widget.add_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            radio = self.query_one("#harness-radio", RadioSet)
            idx = radio.pressed_index if radio.pressed_index >= 0 else 0
            level = self._LEVELS[idx]
            result: dict[str, Any] = {"harness_level": level}
            # Include feature flags for ralph-loop and custom
            if level in self._FEATURE_LEVELS:
                result["harness_task_tracking"] = self.query_one(
                    "#harness-task-tracking", Checkbox
                ).value
                result["harness_budget_awareness"] = self.query_one(
                    "#harness-budget-awareness", Checkbox
                ).value
                result["harness_verification_gates"] = self.query_one(
                    "#harness-verification-gates", Checkbox
                ).value
            self.dismiss(result)
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
                out = str(self._state.get("output_dir", "."))
                yield Static(
                    _format_config_summary(config, out),
                    id="summary-box",
                )
            yield Label("")
        yield _ConfirmNavBar()
        yield KeyHintsBar()

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
    _ConfirmNavBar .spacer {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield _Button("Back", id="btn-back", variant="default")
        yield Static("", classes="spacer")
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
    (ReviewScreen, "Configuration preview", None),
    (ExpertScreen, "Customize", _wants_expert),
    (FeaturesScreen, "Features", _wants_expert),
    (SkillPacksScreen, "Skill packs", None),
    (HarnessScreen, "Runtime harness", None),
    (ConfirmScreen, "Confirm", None),
]

_QUICK_SCREENS: list[tuple[type, str, Any]] = [
    (TemplateScreen, "Select your stack", None),
    (WorkflowScreen, "Select your workflow", None),
    (BasicsScreen, "Project name", None),
    (ReviewScreen, "Configuration preview", None),
    (ExpertScreen, "Customize", _wants_expert),
    (FeaturesScreen, "Features", _wants_expert),
    (SkillPacksScreen, "Skill packs", None),
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

            visible = [s for s in self._screens if s[2] is None or s[2](state)]
            visible_idx = next(i for i, s in enumerate(visible) if s[0] is screen_cls)
            state["step_label"] = f"  Step {visible_idx + 1} of {len(visible)} - {title}"

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
        from cc_rig.config.project import Features, PluginRecommendation

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
        if "expert_plugins" in state:
            config.recommended_plugins = [
                PluginRecommendation(
                    name=name,
                    marketplace=PLUGIN_CATALOG[name].marketplace,
                    category=PLUGIN_CATALOG[name].category,
                    description=PLUGIN_CATALOG[name].description,
                    requires_binary=PLUGIN_CATALOG[name].requires_binary,
                    replaces_mcp=PLUGIN_CATALOG[name].replaces_mcp,
                )
                for name in state["expert_plugins"]
                if name in PLUGIN_CATALOG
            ]

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
        Ralph-loop adds the ralph-loop plugin if not already present.
        """
        from cc_rig.config.project import HarnessConfig, PluginRecommendation
        from cc_rig.plugins.registry import PLUGIN_CATALOG

        config = state.get("config")
        if config is None:
            return state

        level = state.get("harness_level", "none")
        if level in ("ralph-loop", "custom"):
            config.harness = HarnessConfig(
                level=level,
                task_tracking=state.get("harness_task_tracking", False),
                budget_awareness=state.get("harness_budget_awareness", False),
                verification_gates=state.get("harness_verification_gates", False),
            )
        else:
            config.harness = HarnessConfig(level=level)

        # B3 requires the autonomy-loop hook — add it automatically
        if level == "autonomy" and "autonomy-loop" not in config.hooks:
            config.hooks = list(config.hooks) + ["autonomy-loop"]

        # Ralph-loop: add the plugin to recommended_plugins
        if level == "ralph-loop":
            ralph_spec = PLUGIN_CATALOG.get("ralph-loop")
            if ralph_spec:
                plugin_names = {p.name for p in config.recommended_plugins}
                if "ralph-loop" not in plugin_names:
                    config.recommended_plugins = list(config.recommended_plugins) + [
                        PluginRecommendation(
                            name=ralph_spec.name,
                            marketplace=ralph_spec.marketplace,
                            category=ralph_spec.category,
                            description=ralph_spec.description,
                        )
                    ]

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
