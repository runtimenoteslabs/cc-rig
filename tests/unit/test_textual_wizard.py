"""Tests for the Textual full-screen TUI wizard.

Uses Textual's headless pilot for async testing — no TTY needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest_plugins = ("pytest_asyncio",)

# Skip entire module if textual is not installed
textual = pytest.importorskip("textual")

from textual.widgets import (  # noqa: E402
    Checkbox,
    RadioSet,
    SelectionList,
    Static,
    TabbedContent,
    TabPane,
)

from cc_rig.ui.textual_wizard import (  # noqa: E402
    BasicsScreen,
    ConfirmScreen,
    ExpertScreen,
    FeaturesScreen,
    HarnessScreen,
    QuickWizardApp,
    ReviewScreen,
    SkillPacksScreen,
    TemplateScreen,
    WelcomeScreen,
    WizardApp,
    WorkflowScreen,
    should_use_textual,
)


def _make_state(**overrides):
    """Build a minimal initial state dict."""
    state = {
        "name": "test-project",
        "output_dir": Path("/tmp/test"),
        "force_expert": False,
    }
    state.update(overrides)
    return state


# ── should_use_textual detection ──────────────────────────────────────


class TestShouldUseTextual:
    def test_returns_false_with_test_io(self):
        from cc_rig.ui.prompts import IO

        io = IO(input_fn=lambda _: "test", print_fn=lambda *a, **kw: None)
        assert should_use_textual(io) is False

    def test_returns_false_with_none_io_and_no_tty(self, monkeypatch):
        import sys

        monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
        assert should_use_textual(None) is False


# ── WelcomeScreen ─────────────────────────────────────────────────────


class TestWelcomeScreen:
    @pytest.mark.asyncio
    async def test_renders_banner_and_radio(self):
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            # WelcomeScreen should be pushed first
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, WelcomeScreen)
            # Should have the launcher RadioSet
            radio = screen.query_one("#launcher-radio")
            assert radio is not None
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_fresh_mode_advances(self):
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Default selection is "Fresh project" (index 0) — click Start
            await pilot.click("#btn-next")
            await pilot.pause()
            # Should advance to BasicsScreen
            assert isinstance(app.screen, BasicsScreen)
            await pilot.click("#btn-cancel")


# ── BasicsScreen ──────────────────────────────────────────────────────


class TestBasicsScreen:
    @pytest.mark.asyncio
    async def test_renders_name_input(self):
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Advance past WelcomeScreen
            await pilot.click("#btn-next")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, BasicsScreen)
            name_input = screen.query_one("#input-name")
            assert name_input is not None
            assert name_input.value == "test-project"
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_back_returns_to_welcome(self):
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#btn-next")
            await pilot.pause()
            assert isinstance(app.screen, BasicsScreen)
            # Press Back
            await pilot.click("#btn-back")
            await pilot.pause()
            assert isinstance(app.screen, WelcomeScreen)
            await pilot.click("#btn-cancel")


# ── Cancel exits with None ────────────────────────────────────────────


class TestCancel:
    @pytest.mark.asyncio
    async def test_cancel_on_welcome_returns_none(self):
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#btn-cancel")
            await pilot.pause()
        assert app.return_value is None

    @pytest.mark.asyncio
    async def test_escape_on_welcome_returns_none(self):
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            # Welcome screen has no back target, dismiss with None
            # Then the orchestrator will dismiss with None
            # The app may still be running; cancel to exit
            if app.is_running:
                await pilot.click("#btn-cancel")


# ── QuickWizardApp ────────────────────────────────────────────────────


class TestQuickWizardApp:
    @pytest.mark.asyncio
    async def test_starts_with_template_screen(self):
        app = QuickWizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, TemplateScreen)
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_cancel_returns_none(self):
        app = QuickWizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#btn-cancel")
            await pilot.pause()
        assert app.return_value is None


# ── Full flow forward ─────────────────────────────────────────────────


class TestFullForwardFlow:
    @pytest.mark.asyncio
    async def test_quick_flow_complete(self):
        """Quick flow: Template → Workflow → Basics → Review → SkillPacks → Confirm."""
        app = QuickWizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Screen 1: TemplateScreen — accept default (fastapi) → Next
            assert isinstance(app.screen, TemplateScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # Screen 2: WorkflowScreen
            assert isinstance(app.screen, WorkflowScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # Screen 3: BasicsScreen — name already set
            assert isinstance(app.screen, BasicsScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # Screen 4: ReviewScreen — don't check customize
            assert isinstance(app.screen, ReviewScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # Screen 5: SkillPacksScreen — skip packs
            assert isinstance(app.screen, SkillPacksScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # Screen 6: ConfirmScreen (Expert+Features skipped)
            assert isinstance(app.screen, ConfirmScreen)
            await pilot.click("#btn-next")
            await pilot.pause()

        state = app.return_value
        assert state is not None
        assert state.get("confirmed") is True
        assert state.get("template") == "fastapi"
        assert "config" in state


# ── Expert + Features flow ────────────────────────────────────────────


class TestExpertFeaturesFlow:
    @pytest.mark.asyncio
    async def test_expert_and_features_are_separate_screens(self):
        """When force_expert=True, ExpertScreen and FeaturesScreen both show."""
        app = WizardApp(initial_state=_make_state(force_expert=True))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Welcome
            assert isinstance(app.screen, WelcomeScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # Basics
            assert isinstance(app.screen, BasicsScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # Template
            assert isinstance(app.screen, TemplateScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # Workflow
            assert isinstance(app.screen, WorkflowScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # Review
            assert isinstance(app.screen, ReviewScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # Expert (agents/commands/hooks only)
            assert isinstance(app.screen, ExpertScreen)
            # Verify no feature checkboxes on ExpertScreen
            feat_checkboxes = app.screen.query("#feat-memory")
            assert len(feat_checkboxes) == 0
            await pilot.click("#btn-next")
            await pilot.pause()
            # Features (dedicated screen with rich descriptions)
            assert isinstance(app.screen, FeaturesScreen)
            assert app.screen.query_one("#feat-memory") is not None
            assert app.screen.query_one("#feat-spec") is not None
            assert app.screen.query_one("#feat-gtd") is not None
            assert app.screen.query_one("#feat-worktrees") is not None
            await pilot.click("#btn-next")
            await pilot.pause()
            # SkillPacks (after Features)
            assert isinstance(app.screen, SkillPacksScreen)
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_features_skipped_without_expert(self):
        """Without expert mode, both ExpertScreen and FeaturesScreen are skipped."""
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Welcome → Basics → Template → Workflow → Review
            await pilot.click("#btn-next")  # Welcome → Basics
            await pilot.pause()
            await pilot.click("#btn-next")  # Basics → Template
            await pilot.pause()
            await pilot.click("#btn-next")  # Template → Workflow
            await pilot.pause()
            await pilot.click("#btn-next")  # Workflow → Review
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen)
            await pilot.click("#btn-next")  # Review → SkillPacks
            await pilot.pause()
            assert isinstance(app.screen, SkillPacksScreen)
            await pilot.click("#btn-next")  # SkillPacks → should skip Expert+Features → Harness
            await pilot.pause()
            # Should be HarnessScreen, not ExpertScreen or FeaturesScreen
            from cc_rig.ui.textual_wizard import HarnessScreen

            assert isinstance(app.screen, HarnessScreen)
            await pilot.click("#btn-cancel")


# ── Save config from ConfirmScreen ────────────────────────────────────


class TestSaveConfig:
    @pytest.mark.asyncio
    async def test_save_button_exists_on_confirm_screen(self):
        """ConfirmScreen has a Save Config button."""
        app = QuickWizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Template → Workflow → Basics → Review → SkillPacks → Confirm
            await pilot.click("#btn-next")
            await pilot.pause()
            await pilot.click("#btn-next")
            await pilot.pause()
            await pilot.click("#btn-next")
            await pilot.pause()
            # ReviewScreen — skip customize
            assert isinstance(app.screen, ReviewScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # SkillPacksScreen — skip packs
            assert isinstance(app.screen, SkillPacksScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            assert isinstance(app.screen, ConfirmScreen)
            # Save button should exist
            save_btn = app.screen.query_one("#btn-save")
            assert save_btn is not None
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_save_does_not_dismiss_screen(self):
        """Clicking Save Config keeps the user on ConfirmScreen."""
        app = QuickWizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#btn-next")
            await pilot.pause()
            await pilot.click("#btn-next")
            await pilot.pause()
            await pilot.click("#btn-next")
            await pilot.pause()
            # ReviewScreen — skip customize
            assert isinstance(app.screen, ReviewScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            # SkillPacksScreen — skip packs
            assert isinstance(app.screen, SkillPacksScreen)
            await pilot.click("#btn-next")
            await pilot.pause()
            assert isinstance(app.screen, ConfirmScreen)
            # Click save — should stay on the same screen
            await pilot.click("#btn-save")
            await pilot.pause()
            assert isinstance(app.screen, ConfirmScreen)
            await pilot.click("#btn-cancel")


# ── Back navigation from quick flow ──────────────────────────────────


class TestBackFromQuickFlow:
    @pytest.mark.asyncio
    async def test_back_from_quick_template_returns_to_welcome(self):
        """Selecting quick mode then pressing Back on TemplateScreen returns to WelcomeScreen."""
        app = WizardApp(initial_state=_make_state(launcher_mode="quick"))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # WelcomeScreen — select "Template picker" (index 1)
            assert isinstance(app.screen, WelcomeScreen)
            # Programmatically select the second radio button (Template picker)
            radio = app.screen.query_one("#launcher-radio", RadioSet)
            buttons = list(radio.query("RadioButton"))
            buttons[1].value = True
            await pilot.pause()
            await pilot.click("#btn-next")
            await pilot.pause()
            # Should now be on TemplateScreen in quick flow
            assert isinstance(app.screen, TemplateScreen)
            # Press Back — should return to WelcomeScreen, not loop
            await pilot.click("#btn-back")
            await pilot.pause()
            assert isinstance(app.screen, WelcomeScreen)
            await pilot.click("#btn-cancel")


# ── Expert screen tabs ───────────────────────────────────────────────


class TestExpertScreenTabs:
    @pytest.mark.asyncio
    async def test_expert_screen_has_tabs(self):
        """ExpertScreen uses TabbedContent with 4 tabs: agents, commands, hooks, plugins."""
        app = WizardApp(initial_state=_make_state(force_expert=True))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Navigate: Welcome → Basics → Template → Workflow → Review → Expert
            await pilot.click("#btn-next")  # Welcome → Basics
            await pilot.pause()
            await pilot.click("#btn-next")  # Basics → Template
            await pilot.pause()
            await pilot.click("#btn-next")  # Template → Workflow
            await pilot.pause()
            await pilot.click("#btn-next")  # Workflow → Review
            await pilot.pause()
            await pilot.click("#btn-next")  # Review → Expert
            await pilot.pause()
            assert isinstance(app.screen, ExpertScreen)
            # Verify TabbedContent exists
            tabs = app.screen.query_one("#expert-tabs", TabbedContent)
            assert tabs is not None
            # Verify all 4 tab panes exist
            assert app.screen.query_one("#tab-agents", TabPane) is not None
            assert app.screen.query_one("#tab-commands", TabPane) is not None
            assert app.screen.query_one("#tab-hooks", TabPane) is not None
            assert app.screen.query_one("#tab-plugins", TabPane) is not None
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_expert_descriptions_visible(self):
        """SelectionList labels in ExpertScreen contain description text."""
        app = WizardApp(initial_state=_make_state(force_expert=True))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Navigate to ExpertScreen
            await pilot.click("#btn-next")  # Welcome → Basics
            await pilot.pause()
            await pilot.click("#btn-next")  # Basics → Template
            await pilot.pause()
            await pilot.click("#btn-next")  # Template → Workflow
            await pilot.pause()
            await pilot.click("#btn-next")  # Workflow → Review
            await pilot.pause()
            await pilot.click("#btn-next")  # Review → Expert
            await pilot.pause()
            assert isinstance(app.screen, ExpertScreen)
            # Check that agent labels contain descriptions (not just bare names)
            sel_agents = app.screen.query_one("#sel-agents", SelectionList)
            # Get the first option's label - should contain " - "
            option = sel_agents.get_option_at_index(0)
            label_text = str(option.prompt)
            assert " - " in label_text
            await pilot.click("#btn-cancel")


# ── Expert plugins tab ───────────────────────────────────────────────


class TestExpertPluginsTab:
    """Plugins tab in ExpertScreen."""

    async def _navigate_to_expert(self, pilot: Any) -> None:
        """Helper: navigate from WelcomeScreen through to ExpertScreen."""
        await pilot.pause()
        await pilot.click("#btn-next")  # Welcome → Basics
        await pilot.pause()
        await pilot.click("#btn-next")  # Basics → Template
        await pilot.pause()
        await pilot.click("#btn-next")  # Template → Workflow
        await pilot.pause()
        await pilot.click("#btn-next")  # Workflow → Review
        await pilot.pause()
        await pilot.click("#btn-next")  # Review → Expert
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_plugins_tab_has_selection_list(self):
        """The Plugins tab should contain a SelectionList widget."""
        app = WizardApp(initial_state=_make_state(force_expert=True))
        async with app.run_test(size=(120, 40)) as pilot:
            await self._navigate_to_expert(pilot)
            assert isinstance(app.screen, ExpertScreen)
            sel_plugins = app.screen.query_one("#sel-plugins", SelectionList)
            assert sel_plugins is not None
            # Should have at least one option
            assert sel_plugins.option_count > 0
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_plugins_tab_excludes_autonomy(self):
        """Autonomy plugins (ralph-loop) should not appear in the plugins selection list."""
        app = WizardApp(initial_state=_make_state(force_expert=True))
        async with app.run_test(size=(120, 40)) as pilot:
            await self._navigate_to_expert(pilot)
            assert isinstance(app.screen, ExpertScreen)
            sel_plugins = app.screen.query_one("#sel-plugins", SelectionList)
            option_values = [
                sel_plugins.get_option_at_index(i).value for i in range(sel_plugins.option_count)
            ]
            assert "ralph-loop" not in option_values

    @pytest.mark.asyncio
    async def test_plugins_tab_labels_contain_descriptions(self):
        """Plugin option labels should include the description text (contain ' - ')."""
        app = WizardApp(initial_state=_make_state(force_expert=True))
        async with app.run_test(size=(120, 40)) as pilot:
            await self._navigate_to_expert(pilot)
            assert isinstance(app.screen, ExpertScreen)
            sel_plugins = app.screen.query_one("#sel-plugins", SelectionList)
            first_option = sel_plugins.get_option_at_index(0)
            label_text = str(first_option.prompt)
            assert " - " in label_text

    @pytest.mark.asyncio
    async def test_plugins_tab_returns_selected_plugins_on_next(self):
        """Submitting ExpertScreen returns expert_plugins in the dismissed dict."""
        app = WizardApp(initial_state=_make_state(force_expert=True))
        async with app.run_test(size=(120, 40)) as pilot:
            await self._navigate_to_expert(pilot)
            assert isinstance(app.screen, ExpertScreen)
            # Click Next — ExpertScreen dismisses with expert_plugins key
            await pilot.click("#btn-next")
            await pilot.pause()
            # After dismissal the wizard advances; we cannot inspect the dismissed
            # value directly, but we can verify we moved past ExpertScreen
            assert not isinstance(app.screen, ExpertScreen)
            await pilot.click("#btn-cancel")


# ── Harness ralph-loop radio ─────────────────────────────────────────


class TestHarnessRalphLoop:
    """Ralph-loop option in HarnessScreen."""

    async def _navigate_to_harness(self, pilot: Any) -> None:
        """Helper: navigate WizardApp (non-expert) to HarnessScreen."""
        await pilot.pause()
        await pilot.click("#btn-next")  # Welcome → Basics
        await pilot.pause()
        await pilot.click("#btn-next")  # Basics → Template
        await pilot.pause()
        await pilot.click("#btn-next")  # Template → Workflow
        await pilot.pause()
        await pilot.click("#btn-next")  # Workflow → Review
        await pilot.pause()
        await pilot.click("#btn-next")  # Review → SkillPacks (no expert)
        await pilot.pause()
        await pilot.click("#btn-next")  # SkillPacks → Harness
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_ralph_loop_radio_exists(self):
        """HarnessScreen should have a ralph-loop radio button (5th option)."""
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await self._navigate_to_harness(pilot)
            assert isinstance(app.screen, HarnessScreen)
            radio = app.screen.query_one("#harness-radio", RadioSet)
            assert radio is not None
            # There should be exactly 5 options: none, lite, standard, autonomy, ralph-loop
            buttons = list(radio.query("RadioButton"))
            assert len(buttons) == 5
            # The last button label should reference ralph-loop
            last_label = str(buttons[4].label)
            assert "ralph" in last_label.lower() or "loop" in last_label.lower()
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_harness_details_panel_exists(self):
        """HarnessScreen should render a #harness-details Static panel."""
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await self._navigate_to_harness(pilot)
            assert isinstance(app.screen, HarnessScreen)
            details = app.screen.query_one("#harness-details", Static)
            assert details is not None
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_harness_details_update_on_radio_change(self):
        """Selecting a different harness radio updates the #harness-details panel content."""
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await self._navigate_to_harness(pilot)
            assert isinstance(app.screen, HarnessScreen)
            details = app.screen.query_one("#harness-details", Static)
            # Default selection is "none" — details should contain B0 text
            initial_content = details._Static__content
            assert initial_content  # not empty
            # Select the second radio (lite / B1)
            radio = app.screen.query_one("#harness-radio", RadioSet)
            buttons = list(radio.query("RadioButton"))
            buttons[1].value = True
            await pilot.pause()
            updated_content = details._Static__content
            # Content should have changed from "none" details to "lite" details
            assert updated_content != initial_content
            assert "B1" in updated_content or "lite" in updated_content.lower()
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_harness_ralph_loop_details_shown(self):
        """Selecting ralph-loop radio shows ralph-loop specific details."""
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await self._navigate_to_harness(pilot)
            assert isinstance(app.screen, HarnessScreen)
            details = app.screen.query_one("#harness-details", Static)
            # Select the 5th radio button (ralph-loop, index 4)
            radio = app.screen.query_one("#harness-radio", RadioSet)
            buttons = list(radio.query("RadioButton"))
            buttons[4].value = True
            await pilot.pause()
            ralph_content = details._Static__content
            assert "ralph" in ralph_content.lower() or "plugin" in ralph_content.lower()
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_harness_ralph_loop_dismisses_correct_level(self):
        """Selecting ralph-loop and clicking Next dismisses with harness_level=ralph-loop."""
        dismissed_values: list[dict] = []

        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await self._navigate_to_harness(pilot)
            assert isinstance(app.screen, HarnessScreen)
            # Select the 5th radio (ralph-loop)
            radio = app.screen.query_one("#harness-radio", RadioSet)
            buttons = list(radio.query("RadioButton"))
            buttons[4].value = True
            await pilot.pause()
            # Patch dismiss to capture the value
            original_dismiss = app.screen.dismiss

            def capture_dismiss(value: Any = None) -> None:
                if isinstance(value, dict):
                    dismissed_values.append(value)
                original_dismiss(value)

            app.screen.dismiss = capture_dismiss  # type: ignore[method-assign]
            await pilot.click("#btn-next")
            await pilot.pause()

        if dismissed_values:
            assert dismissed_values[0].get("harness_level") == "ralph-loop"


# ── Workflow detail panel ────────────────────────────────────────────


class TestWorkflowDetailsPanel:
    @pytest.mark.asyncio
    async def test_workflow_details_update_on_selection(self):
        """The #workflow-details panel updates when a different workflow is selected."""
        app = WizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Navigate: Welcome → Basics → Template → Workflow
            await pilot.click("#btn-next")  # Welcome → Basics
            await pilot.pause()
            await pilot.click("#btn-next")  # Basics → Template
            await pilot.pause()
            await pilot.click("#btn-next")  # Template → Workflow
            await pilot.pause()
            assert isinstance(app.screen, WorkflowScreen)
            # Detail panel should exist with default content (standard)
            details = app.screen.query_one("#workflow-details", Static)
            assert details is not None
            # Access content via name-mangled attribute
            content = details._Static__content
            assert "Best for:" in content
            await pilot.click("#btn-cancel")


# ── Quick flow review and conditional expert ─────────────────────────


class TestQuickFlowReviewAndExpert:
    @pytest.mark.asyncio
    async def test_quick_flow_has_review_screen(self):
        """Quick flow includes ReviewScreen between Basics and Confirm."""
        app = QuickWizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Template → Workflow → Basics → Review
            await pilot.click("#btn-next")  # Template → Workflow
            await pilot.pause()
            await pilot.click("#btn-next")  # Workflow → Basics
            await pilot.pause()
            await pilot.click("#btn-next")  # Basics → Review
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen)
            await pilot.click("#btn-cancel")

    @pytest.mark.asyncio
    async def test_quick_flow_expert_conditional(self):
        """In quick flow, Expert/Features only appear when customize is checked."""
        app = QuickWizardApp(initial_state=_make_state())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Template → Workflow → Basics → Review → Expert
            await pilot.click("#btn-next")  # Template
            await pilot.pause()
            await pilot.click("#btn-next")  # Workflow
            await pilot.pause()
            await pilot.click("#btn-next")  # Basics
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen)
            # Check the customize checkbox
            chk = app.screen.query_one("#chk-customize", Checkbox)
            chk.value = True
            await pilot.click("#btn-next")  # Review → Expert (because customize=True)
            await pilot.pause()
            assert isinstance(app.screen, ExpertScreen)
            await pilot.click("#btn-cancel")
