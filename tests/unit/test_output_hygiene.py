"""Tests for output hygiene features: compact commands, context hygiene, RTK detection."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.doctor import run_doctor
from cc_rig.generators.claude_md import _COMPACT_COMMANDS
from cc_rig.presets.manager import BUILTIN_TEMPLATES
from tests.conftest import generate_project

# ── Layer 1: Compact Command Guardrails ──────────────────────────


class TestCompactCommandsCoverage:
    """Every template must have compact command entries."""

    def test_all_templates_have_entries(self):
        """Guard: _COMPACT_COMMANDS covers every built-in template."""
        missing = [t for t in BUILTIN_TEMPLATES if t not in _COMPACT_COMMANDS]
        assert not missing, f"Templates missing compact commands: {missing}"

    def test_each_entry_is_nonempty(self):
        """Each template has at least one compact command hint."""
        for template, hints in _COMPACT_COMMANDS.items():
            assert len(hints) >= 1, f"{template}: no compact command hints"

    def test_generic_fallback_exists(self):
        """Generic template serves as fallback."""
        assert "generic" in _COMPACT_COMMANDS
        assert len(_COMPACT_COMMANDS["generic"]) >= 1


class TestCompactCommandsInClaudeMd:
    """Compact commands appear in generated CLAUDE.md guardrails section."""

    def _generate(self, template, workflow, tmp_path):
        from cc_rig.generators.claude_md import generate_claude_md

        config = compute_defaults(template, workflow, project_name="test-proj")
        generate_claude_md(config, tmp_path)
        return (tmp_path / "CLAUDE.md").read_text()

    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_compact_commands_present(self, template, tmp_path):
        """Every template includes at least one compact command guardrail."""
        content = self._generate(template, "standard", tmp_path)
        hints = _COMPACT_COMMANDS.get(template, _COMPACT_COMMANDS["generic"])
        for hint in hints:
            assert hint in content, f"{template}: missing hint: {hint[:50]}..."

    def test_fastapi_pytest_hint(self, tmp_path):
        content = self._generate("fastapi", "standard", tmp_path)
        assert "pytest -q --tb=short" in content

    def test_nextjs_npm_hint(self, tmp_path):
        content = self._generate("nextjs", "standard", tmp_path)
        assert "npm ls --depth=0" in content

    def test_gin_go_test_hint(self, tmp_path):
        content = self._generate("gin", "standard", tmp_path)
        assert "go test -short" in content

    def test_rails_test_hint(self, tmp_path):
        content = self._generate("rails", "standard", tmp_path)
        assert "rails test" in content

    def test_rust_cargo_hint(self, tmp_path):
        content = self._generate("rust-cli", "standard", tmp_path)
        assert "cargo test" in content

    def test_spring_mvn_hint(self, tmp_path):
        content = self._generate("spring", "standard", tmp_path)
        assert "mvnw test" in content or "gradlew test" in content

    def test_laravel_artisan_hint(self, tmp_path):
        content = self._generate("laravel", "standard", tmp_path)
        assert "artisan test" in content

    def test_phoenix_mix_hint(self, tmp_path):
        content = self._generate("phoenix", "standard", tmp_path)
        assert "mix test" in content

    def test_dotnet_hint(self, tmp_path):
        content = self._generate("dotnet", "standard", tmp_path)
        assert "dotnet test" in content

    def test_compact_in_speedrun(self, tmp_path):
        """Compact commands are unconditional, present even in speedrun."""
        content = self._generate("fastapi", "speedrun", tmp_path)
        assert "pytest -q --tb=short" in content

    def test_compact_in_guardrails_section(self, tmp_path):
        """Compact commands appear within the Guardrails section."""
        content = self._generate("fastapi", "standard", tmp_path)
        guardrails_start = content.index("## Guardrails")
        # Find next section
        next_section = content.index("## ", guardrails_start + 1)
        guardrails_text = content[guardrails_start:next_section]
        assert "pytest -q --tb=short" in guardrails_text

    def test_unknown_template_falls_back_to_generic(self, tmp_path):
        """Unknown framework uses generic compact commands."""
        from cc_rig.generators.claude_md import generate_claude_md

        config = compute_defaults("fastapi", "standard", project_name="test")
        config.framework = "unknown-framework"
        config.template_preset = "unknown"
        generate_claude_md(config, tmp_path)
        content = (tmp_path / "CLAUDE.md").read_text()
        generic_hints = _COMPACT_COMMANDS["generic"]
        for hint in generic_hints:
            assert hint in content


# ── Layer 2: Context Hygiene in Agent Docs ───────────────────────


class TestContextHygieneInHarness:
    """Output hygiene section appended to harness.md when context_awareness=True."""

    def _generate_with_harness(self, tmp_path, level):
        from cc_rig.config.project import HarnessConfig
        from cc_rig.generators.harness import generate_harness

        config = compute_defaults("fastapi", "standard", project_name="test")
        config.harness = HarnessConfig(level=level)
        generate_harness(config, tmp_path)
        return tmp_path

    def test_output_hygiene_in_lite(self, tmp_path):
        """B1 lite has context_awareness=True, should include output hygiene."""
        self._generate_with_harness(tmp_path, "lite")
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "Output Hygiene" in content

    def test_output_hygiene_in_standard(self, tmp_path):
        """B2 standard has context_awareness=True."""
        self._generate_with_harness(tmp_path, "standard")
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "Output Hygiene" in content

    def test_output_hygiene_in_autonomy(self, tmp_path):
        """B3 autonomy has context_awareness=True."""
        self._generate_with_harness(tmp_path, "autonomy")
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "Output Hygiene" in content

    def test_no_output_hygiene_in_none(self, tmp_path):
        """B0 none has no harness files at all."""
        self._generate_with_harness(tmp_path, "none")
        harness_md = tmp_path / "agent_docs" / "harness.md"
        if harness_md.exists():
            content = harness_md.read_text()
            # Should not have output hygiene since context_awareness=False
            assert "Output Hygiene" not in content

    def test_mentions_git_diff_stat(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite")
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "git diff --stat" in content

    def test_mentions_quiet_flags(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite")
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "--quiet" in content or "--short" in content

    def test_mentions_head_tail(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite")
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "`head`/`tail`" in content

    def test_mentions_rtk(self, tmp_path):
        """Output hygiene section mentions RTK as complementary tool."""
        self._generate_with_harness(tmp_path, "lite")
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "RTK" in content or "rtk" in content

    def test_output_hygiene_after_context_awareness(self, tmp_path):
        """Output hygiene is within the Context Awareness section."""
        self._generate_with_harness(tmp_path, "lite")
        content = (tmp_path / "agent_docs" / "harness.md").read_text()
        ctx_pos = content.index("Context Awareness")
        hygiene_pos = content.index("Output Hygiene")
        assert hygiene_pos > ctx_pos


# ── Layer 3: RTK Detection in Doctor ─────────────────────────────


class TestDoctorRtkNotInstalled:
    """When RTK is not in PATH, doctor skips silently."""

    def test_no_rtk_no_info(self, tmp_path):
        generate_project(tmp_path)
        with patch("cc_rig.doctor.shutil.which", return_value=None):
            result = run_doctor(tmp_path)
        rtk_msgs = [m for m in result.info if "rtk" in m.lower()]
        assert len(rtk_msgs) == 0

    def test_no_rtk_no_warning(self, tmp_path):
        generate_project(tmp_path)
        with patch("cc_rig.doctor.shutil.which", return_value=None):
            result = run_doctor(tmp_path)
        rtk_warns = [m for m in result.warnings if "rtk" in m.lower()]
        assert len(rtk_warns) == 0


class TestDoctorRtkInstalled:
    """When RTK is in PATH, doctor reports info-level status."""

    def test_rtk_detected_no_hook(self, tmp_path):
        """RTK installed but hook not configured."""
        from cc_rig.doctor import DoctorResult, _check_rtk

        result = DoctorResult()

        with (
            patch("cc_rig.doctor.shutil.which", return_value="/usr/local/bin/rtk"),
            patch("cc_rig.doctor.subprocess.run") as mock_run,
            patch("cc_rig.doctor._rtk_hook_configured", return_value=False),
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "rtk 0.28.2"
            _check_rtk(tmp_path, result)

        rtk_msgs = [m for m in result.info if "rtk" in m.lower()]
        assert len(rtk_msgs) == 1
        assert "0.28.2" in rtk_msgs[0]
        assert "not configured" in rtk_msgs[0]
        assert "rtk init -g" in rtk_msgs[0]

    def test_rtk_detected_with_hook(self, tmp_path):
        """RTK installed and hook configured."""
        from cc_rig.doctor import DoctorResult, _check_rtk

        result = DoctorResult()

        with (
            patch("cc_rig.doctor.shutil.which", return_value="/usr/local/bin/rtk"),
            patch("cc_rig.doctor.subprocess.run") as mock_run,
            patch("cc_rig.doctor._rtk_hook_configured", return_value=True),
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "rtk 0.28.2"
            _check_rtk(tmp_path, result)

        rtk_msgs = [m for m in result.info if "rtk" in m.lower()]
        assert len(rtk_msgs) == 1
        assert "0.28.2" in rtk_msgs[0]
        assert "active" in rtk_msgs[0]

    def test_rtk_version_timeout(self, tmp_path):
        """RTK version command times out gracefully."""
        import subprocess as subprocess_mod

        from cc_rig.doctor import DoctorResult, _check_rtk

        result = DoctorResult()

        with (
            patch("cc_rig.doctor.shutil.which", return_value="/usr/local/bin/rtk"),
            patch(
                "cc_rig.doctor.subprocess.run",
                side_effect=subprocess_mod.TimeoutExpired("rtk", 5),
            ),
            patch("cc_rig.doctor._rtk_hook_configured", return_value=False),
        ):
            _check_rtk(tmp_path, result)

        rtk_msgs = [m for m in result.info if "rtk" in m.lower()]
        assert len(rtk_msgs) == 1
        assert "unknown" in rtk_msgs[0]


class TestRtkHookConfigured:
    """Test _rtk_hook_configured helper."""

    def test_no_settings_file(self, tmp_path):
        from cc_rig.doctor import _rtk_hook_configured

        assert not _rtk_hook_configured(tmp_path)

    def test_settings_without_hooks(self, tmp_path):
        from cc_rig.doctor import _rtk_hook_configured

        settings = tmp_path / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({"permissions": {}}))
        assert not _rtk_hook_configured(tmp_path)

    def test_settings_with_rtk_hook_nested(self, tmp_path):
        """RTK hook in nested format (matcher + hooks array)."""
        from cc_rig.doctor import _rtk_hook_configured

        settings = tmp_path / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Bash",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "/home/user/.claude/hooks/rtk-rewrite.sh",
                                    }
                                ],
                            }
                        ]
                    }
                }
            )
        )
        assert _rtk_hook_configured(tmp_path)

    def test_settings_with_rtk_hook_flat(self, tmp_path):
        """RTK hook in flat format (command directly on entry)."""
        from cc_rig.doctor import _rtk_hook_configured

        settings = tmp_path / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "type": "command",
                                "command": "rtk-rewrite",
                            }
                        ]
                    }
                }
            )
        )
        assert _rtk_hook_configured(tmp_path)

    def test_settings_with_unrelated_hooks(self, tmp_path):
        """Hooks present but none are RTK."""
        from cc_rig.doctor import _rtk_hook_configured

        settings = tmp_path / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "type": "command",
                                "command": "my-lint-hook.sh",
                            }
                        ]
                    }
                }
            )
        )
        assert not _rtk_hook_configured(tmp_path)

    def test_global_settings_fallback(self, tmp_path):
        """Falls back to ~/.claude/settings.json when project settings missing."""
        from cc_rig.doctor import _rtk_hook_configured

        # No project settings, but mock the global path
        global_settings = Path.home() / ".claude" / "settings.json"
        if global_settings.exists():
            content = json.loads(global_settings.read_text())
            has_rtk = "rtk" in json.dumps(content)
            result = _rtk_hook_configured(tmp_path)
            assert result == has_rtk
        # If no global settings either, should return False
        else:
            assert not _rtk_hook_configured(tmp_path)
