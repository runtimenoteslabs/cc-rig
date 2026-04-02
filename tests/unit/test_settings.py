"""Tests for settings.json generator: valid JSON, hook schema, no Node.js."""

import json
import subprocess

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.config.schema import VALID_CC_EVENTS
from cc_rig.generators.settings import (
    _HOOK_REGISTRY,
    _PROMPT_TEXTS,
    generate_settings,
)
from cc_rig.presets.manager import BUILTIN_TEMPLATES, BUILTIN_WORKFLOWS


def _generate_settings(template, workflow, tmp_path):
    config = compute_defaults(template, workflow, project_name="test-project")
    generate_settings(config, tmp_path)
    return config


def _get_scripts(tmp_path):
    hooks_dir = tmp_path / ".claude" / "hooks"
    return list(hooks_dir.glob("*.sh")) if hooks_dir.exists() else []


class TestSettingsJson:
    def test_valid_json(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        path = tmp_path / ".claude" / "settings.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert isinstance(data, dict)

    def test_has_hooks_key(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert "hooks" in data

    def test_has_permissions_key(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert "permissions" in data


class TestHookSchema:
    def test_all_events_valid(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        for event in data.get("hooks", {}):
            assert event in VALID_CC_EVENTS, f"Invalid event: {event}"

    def test_hook_types_valid(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        for event, matchers in data.get("hooks", {}).items():
            for matcher in matchers:
                for hook in matcher.get("hooks", []):
                    assert hook["type"] in ("command", "prompt", "agent"), (
                        f"Invalid type {hook['type']} in {event}"
                    )

    def test_command_hooks_have_command(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        for event, matchers in data.get("hooks", {}).items():
            for matcher in matchers:
                for hook in matcher.get("hooks", []):
                    if hook["type"] == "command":
                        assert "command" in hook
                    elif hook["type"] == "prompt":
                        assert "prompt" in hook


class TestHookScripts:
    def test_hook_scripts_generated(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        hooks_dir = tmp_path / ".claude" / "hooks"
        assert hooks_dir.exists()
        scripts = list(hooks_dir.glob("*.sh"))
        assert len(scripts) > 0

    def test_no_nodejs_in_scripts(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        for script in _get_scripts(tmp_path):
            content = script.read_text()
            assert "node -e" not in content, f"Node.js in {script.name}"
            assert "node --eval" not in content

    def test_scripts_have_shebang(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        for script in _get_scripts(tmp_path):
            content = script.read_text()
            assert content.startswith("#!/"), f"{script.name} missing shebang"

    def test_scripts_not_empty(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        for script in _get_scripts(tmp_path):
            assert script.stat().st_size > 10, f"{script.name} is too small"


class TestPermissions:
    def test_permissive_mode(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        perms = data.get("permissions", {})
        assert "allow" in perms

    def test_default_mode(self, tmp_path):
        _generate_settings("fastapi", "speedrun", tmp_path)
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        perms = data.get("permissions", {})
        # Default mode should NOT allow Bash (unlike permissive mode)
        assert "Bash" not in perms.get("allow", [])


class TestMultipleTemplates:
    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_settings_valid_for_all_templates(self, template, tmp_path):
        _generate_settings(template, "standard", tmp_path)
        path = tmp_path / ".claude" / "settings.json"
        data = json.loads(path.read_text())
        assert "hooks" in data


# ── Hook script semantic tests ────────────────────────────────────────


class TestHookScriptSyntax:
    """Verify generated hook scripts pass bash -n syntax check."""

    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_all_scripts_pass_bash_syntax_check(self, template, tmp_path):
        _generate_settings(template, "standard", tmp_path)
        for script in _get_scripts(tmp_path):
            result = subprocess.run(
                ["bash", "-n", str(script)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"{script.name} has syntax errors:\n{result.stderr}"

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_all_workflows_pass_bash_syntax(self, workflow, tmp_path):
        _generate_settings("fastapi", workflow, tmp_path)
        for script in _get_scripts(tmp_path):
            result = subprocess.run(
                ["bash", "-n", str(script)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"{script.name} ({workflow}) has syntax errors:\n{result.stderr}"
            )


class TestHookScriptExecutable:
    """Verify hook scripts are chmod 755."""

    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_scripts_are_executable(self, template, tmp_path):
        _generate_settings(template, "standard", tmp_path)
        for script in _get_scripts(tmp_path):
            mode = script.stat().st_mode
            assert mode & 0o755 == 0o755, f"{script.name} not executable (mode={oct(mode)})"


class TestHookScriptContent:
    """Verify hook scripts contain framework-specific commands."""

    def test_format_hook_uses_config_command(self, tmp_path):
        """Format hook should embed the template's formatter."""
        _generate_settings("fastapi", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "format.sh").read_text()
        # fastapi uses "ruff format ." → stripped to "ruff format"
        assert "ruff format" in script

    def test_format_hook_nextjs_uses_prettier(self, tmp_path):
        _generate_settings("nextjs", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "format.sh").read_text()
        assert "prettier" in script

    def test_lint_hook_uses_config_command(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "lint.sh").read_text()
        assert "ruff check" in script

    def test_lint_hook_nextjs_uses_npm(self, tmp_path):
        _generate_settings("nextjs", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "lint.sh").read_text()
        assert "npm run lint" in script

    def test_lint_hook_go_uses_golangci(self, tmp_path):
        _generate_settings("gin", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "lint.sh").read_text()
        assert "golangci-lint" in script

    def test_typecheck_hook_uses_config_command(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "typecheck.sh").read_text()
        assert "mypy" in script

    def test_typecheck_hook_nextjs_uses_tsc(self, tmp_path):
        _generate_settings("nextjs", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "typecheck.sh").read_text()
        assert "tsc" in script

    def test_typecheck_hook_go_uses_vet(self, tmp_path):
        _generate_settings("gin", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "typecheck.sh").read_text()
        assert "go vet" in script

    def test_stop_validator_uses_test_command(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "stop-validator.sh").read_text()
        assert "pytest" in script

    def test_stop_validator_nextjs_uses_npm_test(self, tmp_path):
        _generate_settings("nextjs", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "stop-validator.sh").read_text()
        assert "npm test" in script

    def test_stop_validator_go_uses_go_test(self, tmp_path):
        _generate_settings("gin", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "stop-validator.sh").read_text()
        assert "go test" in script

    def test_lint_hook_axum_uses_clippy(self, tmp_path):
        _generate_settings("rust-web", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "lint.sh").read_text()
        assert "clippy" in script

    def test_format_hook_axum_uses_cargo_fmt(self, tmp_path):
        _generate_settings("rust-web", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "format.sh").read_text()
        assert "cargo fmt" in script

    def test_lint_hook_rails_uses_rubocop(self, tmp_path):
        _generate_settings("rails", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "lint.sh").read_text()
        assert "rubocop" in script

    def test_format_hook_rails_uses_rubocop(self, tmp_path):
        _generate_settings("rails", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "format.sh").read_text()
        assert "rubocop" in script

    def test_no_typecheck_hook_for_rails(self, tmp_path):
        """Rails has no typecheck command — hook should not be generated."""
        _generate_settings("rails", "standard", tmp_path)
        typecheck = tmp_path / ".claude" / "hooks" / "typecheck.sh"
        assert not typecheck.exists()

    def test_lint_hook_spring_uses_checkstyle(self, tmp_path):
        _generate_settings("spring", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "lint.sh").read_text()
        assert "checkstyle" in script

    def test_format_hook_spring_uses_spotless(self, tmp_path):
        _generate_settings("spring", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "format.sh").read_text()
        assert "spotless" in script

    def test_no_typecheck_hook_for_spring(self, tmp_path):
        """Spring Boot (compiled) has no typecheck command — hook should not be generated."""
        _generate_settings("spring", "standard", tmp_path)
        typecheck = tmp_path / ".claude" / "hooks" / "typecheck.sh"
        assert not typecheck.exists()

    def test_lint_hook_dotnet_uses_dotnet_format(self, tmp_path):
        _generate_settings("dotnet", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "lint.sh").read_text()
        assert "dotnet format" in script

    def test_format_hook_dotnet_uses_dotnet_format(self, tmp_path):
        _generate_settings("dotnet", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "format.sh").read_text()
        assert "dotnet format" in script

    def test_no_typecheck_hook_for_dotnet(self, tmp_path):
        """ASP.NET (compiled) has no typecheck command — hook should not be generated."""
        _generate_settings("dotnet", "standard", tmp_path)
        typecheck = tmp_path / ".claude" / "hooks" / "typecheck.sh"
        assert not typecheck.exists()

    def test_lint_hook_laravel_uses_pint(self, tmp_path):
        _generate_settings("laravel", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "lint.sh").read_text()
        assert "pint" in script

    def test_format_hook_laravel_uses_pint(self, tmp_path):
        _generate_settings("laravel", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "format.sh").read_text()
        assert "pint" in script

    def test_no_typecheck_hook_for_laravel(self, tmp_path):
        """Laravel (PHP) has no typecheck command — hook should not be generated."""
        _generate_settings("laravel", "standard", tmp_path)
        typecheck = tmp_path / ".claude" / "hooks" / "typecheck.sh"
        assert not typecheck.exists()

    def test_lint_hook_express_uses_npm(self, tmp_path):
        _generate_settings("express", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "lint.sh").read_text()
        assert "npm run lint" in script

    def test_format_hook_express_uses_prettier(self, tmp_path):
        _generate_settings("express", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "format.sh").read_text()
        assert "prettier" in script

    def test_typecheck_hook_express_uses_tsc(self, tmp_path):
        _generate_settings("express", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "typecheck.sh").read_text()
        assert "tsc" in script

    def test_lint_hook_phoenix_uses_credo(self, tmp_path):
        _generate_settings("phoenix", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "lint.sh").read_text()
        assert "credo" in script

    def test_format_hook_phoenix_uses_mix_format(self, tmp_path):
        _generate_settings("phoenix", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "format.sh").read_text()
        assert "mix format" in script

    def test_no_typecheck_hook_for_phoenix(self, tmp_path):
        """Phoenix (Elixir) has no typecheck command — hook should not be generated."""
        _generate_settings("phoenix", "standard", tmp_path)
        typecheck = tmp_path / ".claude" / "hooks" / "typecheck.sh"
        assert not typecheck.exists()

    def test_lint_hook_go_std_uses_golangci(self, tmp_path):
        _generate_settings("go-std", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "lint.sh").read_text()
        assert "golangci-lint" in script

    def test_typecheck_hook_go_std_uses_vet(self, tmp_path):
        _generate_settings("go-std", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "typecheck.sh").read_text()
        assert "go vet" in script


class TestGenericTemplateHooks:
    """Verify generic template generates no format/lint/typecheck hooks."""

    def test_no_format_hook(self, tmp_path):
        _generate_settings("generic", "standard", tmp_path)
        assert not (tmp_path / ".claude" / "hooks" / "format.sh").exists()

    def test_no_lint_hook(self, tmp_path):
        _generate_settings("generic", "standard", tmp_path)
        assert not (tmp_path / ".claude" / "hooks" / "lint.sh").exists()

    def test_no_typecheck_hook(self, tmp_path):
        _generate_settings("generic", "standard", tmp_path)
        assert not (tmp_path / ".claude" / "hooks" / "typecheck.sh").exists()

    def test_safety_hooks_still_present(self, tmp_path):
        _generate_settings("generic", "standard", tmp_path)
        hooks_dir = tmp_path / ".claude" / "hooks"
        assert (hooks_dir / "block-rm-rf.sh").exists()
        assert (hooks_dir / "block-env.sh").exists()
        assert (hooks_dir / "block-main.sh").exists()


class TestCustomHarnessHooks:
    """Verify custom harness hook generation."""

    def test_custom_autonomy_has_session_tasks_not_commit_gate(self, tmp_path):
        """Custom autonomy-only gets session-tasks but not commit-gate."""
        from cc_rig.config.project import HarnessConfig

        config = compute_defaults("fastapi", "standard", project_name="test")
        config.harness = HarnessConfig(level="custom", autonomy_loop=True)
        generate_settings(config, tmp_path)
        assert (tmp_path / ".claude" / "hooks" / "session-tasks.sh").exists()
        assert not (tmp_path / ".claude" / "hooks" / "commit-gate.sh").exists()
        assert not (tmp_path / ".claude" / "hooks" / "budget-reminder.sh").exists()

    def test_custom_budget_only(self, tmp_path):
        """Custom budget-only gets budget-reminder but not session-tasks."""
        from cc_rig.config.project import HarnessConfig

        config = compute_defaults("fastapi", "standard", project_name="test")
        config.harness = HarnessConfig(level="custom", budget_awareness=True)
        generate_settings(config, tmp_path)
        assert (tmp_path / ".claude" / "hooks" / "budget-reminder.sh").exists()
        assert not (tmp_path / ".claude" / "hooks" / "session-tasks.sh").exists()
        assert not (tmp_path / ".claude" / "hooks" / "commit-gate.sh").exists()

    def test_custom_gates_only(self, tmp_path):
        """Custom gates-only gets commit-gate but not budget or session-tasks."""
        from cc_rig.config.project import HarnessConfig

        config = compute_defaults("fastapi", "standard", project_name="test")
        config.harness = HarnessConfig(level="custom", verification_gates=True)
        generate_settings(config, tmp_path)
        assert (tmp_path / ".claude" / "hooks" / "commit-gate.sh").exists()
        assert not (tmp_path / ".claude" / "hooks" / "budget-reminder.sh").exists()
        assert not (tmp_path / ".claude" / "hooks" / "session-tasks.sh").exists()


class TestHookScriptStructure:
    """Verify hook scripts follow expected patterns."""

    def test_all_scripts_have_set_euo_pipefail(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        for script in _get_scripts(tmp_path):
            content = script.read_text()
            assert "set -euo pipefail" in content, f"{script.name} missing 'set -euo pipefail'"

    def test_all_scripts_end_with_exit(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        for script in _get_scripts(tmp_path):
            content = script.read_text().rstrip()
            assert content.endswith("exit 0") or content.endswith("exit $?"), (
                f"{script.name} doesn't end with explicit exit"
            )

    def test_all_scripts_have_comment_header(self, tmp_path):
        """Each script should have a comment describing which hook it is."""
        _generate_settings("fastapi", "standard", tmp_path)
        for script in _get_scripts(tmp_path):
            content = script.read_text()
            assert "# cc-rig hook:" in content, f"{script.name} missing cc-rig hook comment"

    def test_blocking_hooks_use_exit_2(self, tmp_path):
        """Safety hooks (block-*) should use exit 2 to block tool use."""
        _generate_settings("fastapi", "standard", tmp_path)
        blocking = ["block-rm-rf.sh", "block-env.sh", "block-main.sh"]
        for name in blocking:
            script = tmp_path / ".claude" / "hooks" / name
            if script.exists():
                content = script.read_text()
                assert "exit 2" in content, f"{name} should use exit 2 to block tool use"

    def test_non_blocking_hooks_dont_use_exit_2(self, tmp_path):
        """Non-safety hooks should never exit 2 (which blocks tool use)."""
        _generate_settings("fastapi", "standard", tmp_path)
        non_blocking = [
            "format.sh",
            "lint.sh",
            "typecheck.sh",
            "session-context.sh",
            "stop-validator.sh",
            "memory-precompact.sh",
        ]
        for name in non_blocking:
            script = tmp_path / ".claude" / "hooks" / name
            if script.exists():
                content = script.read_text()
                assert "exit 2" not in content, f"{name} should not block tool use (exit 2)"


class TestHookScriptSafetyContent:
    """Verify safety hook scripts block the right things."""

    def test_block_rm_rf_catches_root_delete(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "block-rm-rf.sh").read_text()
        assert "rm" in script
        assert "BLOCKED" in script

    def test_block_rm_rf_catches_drop_table(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "block-rm-rf.sh").read_text()
        assert "DROP" in script

    def test_block_env_catches_sensitive_files(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "block-env.sh").read_text()
        for pattern in [".env", "credentials", "secrets", ".pem", ".key", "id_rsa"]:
            assert pattern in script, f"block-env.sh should block '{pattern}' files"

    def test_block_main_catches_push_to_main(self, tmp_path):
        _generate_settings("fastapi", "standard", tmp_path)
        script = (tmp_path / ".claude" / "hooks" / "block-main.sh").read_text()
        assert "main" in script
        assert "master" in script
        assert "git push" in script


class TestHookRegistryConsistency:
    """Verify _HOOK_REGISTRY is consistent with generated output."""

    def test_all_command_hooks_have_script_generator(self, tmp_path):
        """Every command-type hook in registry should produce a script file."""
        _generate_settings("fastapi", "verify-heavy", tmp_path)
        config = compute_defaults("fastapi", "verify-heavy", project_name="test")
        for hook_name in config.hooks:
            meta = _HOOK_REGISTRY.get(hook_name)
            if meta is None:
                continue
            _, _, hook_type, _ = meta
            if hook_type == "command":
                script = tmp_path / ".claude" / "hooks" / f"{hook_name}.sh"
                assert script.exists(), f"Command hook '{hook_name}' has no generated script"

    def test_prompt_and_agent_hooks_have_prompt_text(self):
        """Every prompt/agent hook should have non-empty prompt text."""
        for name, (_, _, hook_type, _) in _HOOK_REGISTRY.items():
            if hook_type in ("prompt", "agent"):
                assert name in _PROMPT_TEXTS, (
                    f"Hook '{name}' (type={hook_type}) missing prompt text"
                )
                assert len(_PROMPT_TEXTS[name]) > 10, f"Hook '{name}' prompt text too short"

    def test_hook_event_types_are_valid(self):
        for name, (event, _, _, _) in _HOOK_REGISTRY.items():
            assert event in VALID_CC_EVENTS, f"Hook '{name}' uses invalid event '{event}'"

    def test_hook_types_are_valid(self):
        valid_types = {"command", "prompt", "agent"}
        for name, (_, _, hook_type, _) in _HOOK_REGISTRY.items():
            assert hook_type in valid_types, f"Hook '{name}' has invalid type '{hook_type}'"

    def test_hook_count(self):
        """Guard against accidental additions/removals."""
        assert len(_HOOK_REGISTRY) == 18


class TestTeamMemoryPromptTexts:
    """Verify prompt texts reference team memory correctly."""

    def test_memory_precompact_says_team_memory(self):
        assert "team memory" in _PROMPT_TEXTS["memory-precompact"]

    def test_session_context_says_auto_memory(self):
        assert "Auto-memory" in _PROMPT_TEXTS["session-context"]

    def test_session_context_says_team_context(self):
        assert "team context" in _PROMPT_TEXTS["session-context"]


class TestShellInjectionProtection:
    """Verify _safe_cmd rejects dangerous input."""

    def test_safe_cmd_rejects_semicolons(self, tmp_path):
        from cc_rig.generators.settings import _safe_cmd

        assert _safe_cmd("echo; rm -rf /") == "echo 'No command configured'"

    def test_safe_cmd_rejects_pipes(self, tmp_path):
        from cc_rig.generators.settings import _safe_cmd

        assert _safe_cmd("cat | bash") == "echo 'No command configured'"

    def test_safe_cmd_rejects_backticks(self, tmp_path):
        from cc_rig.generators.settings import _safe_cmd

        assert _safe_cmd("echo `whoami`") == "echo 'No command configured'"

    def test_safe_cmd_rejects_path_traversal(self, tmp_path):
        from cc_rig.generators.settings import _safe_cmd

        assert _safe_cmd("cat ../../../etc/passwd") == "echo 'No command configured'"

    def test_safe_cmd_allows_legitimate_commands(self, tmp_path):
        from cc_rig.generators.settings import _safe_cmd

        assert _safe_cmd("ruff check .") == "ruff check ."
        assert _safe_cmd("npm run lint") == "npm run lint"
        assert _safe_cmd("go test ./...") == "go test ./..."
        assert _safe_cmd("pytest") == "pytest"

    def test_safe_cmd_empty_returns_fallback(self, tmp_path):
        from cc_rig.generators.settings import _safe_cmd

        assert _safe_cmd("") == "echo 'No command configured'"


class TestBudgetReminderHook:
    """Verify budget-reminder hook is generated for B1+ harness levels."""

    def _generate_with_harness(self, tmp_path, level, budget_tokens=None):
        from cc_rig.config.project import HarnessConfig

        config = compute_defaults("fastapi", "standard", project_name="test")
        config.harness = HarnessConfig(
            level=level,
            budget_per_run_tokens=budget_tokens,
            budget_warn_at_percent=80,
        )
        generate_settings(config, tmp_path)
        return config

    def test_not_generated_for_b0(self, tmp_path):
        self._generate_with_harness(tmp_path, "none")
        script = tmp_path / ".claude" / "hooks" / "budget-reminder.sh"
        assert not script.exists()

    def test_generated_for_b1_lite(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite", budget_tokens=500000)
        script = tmp_path / ".claude" / "hooks" / "budget-reminder.sh"
        assert script.exists()

    def test_generated_for_b2_standard(self, tmp_path):
        self._generate_with_harness(tmp_path, "standard", budget_tokens=500000)
        script = tmp_path / ".claude" / "hooks" / "budget-reminder.sh"
        assert script.exists()

    def test_generated_for_b3_autonomy(self, tmp_path):
        self._generate_with_harness(tmp_path, "autonomy", budget_tokens=500000)
        script = tmp_path / ".claude" / "hooks" / "budget-reminder.sh"
        assert script.exists()

    def test_shows_token_limit(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite", budget_tokens=500000)
        content = (tmp_path / ".claude" / "hooks" / "budget-reminder.sh").read_text()
        assert "BUDGET=500000" in content
        assert "80" in content

    def test_shows_unlimited_when_no_limit(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite", budget_tokens=None)
        content = (tmp_path / ".claude" / "hooks" / "budget-reminder.sh").read_text()
        assert "unlimited" in content

    def test_script_passes_bash_syntax(self, tmp_path):
        import subprocess

        self._generate_with_harness(tmp_path, "lite", budget_tokens=500000)
        script = tmp_path / ".claude" / "hooks" / "budget-reminder.sh"
        result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error:\n{result.stderr}"

    def test_script_passes_bash_syntax_unlimited(self, tmp_path):
        import subprocess

        self._generate_with_harness(tmp_path, "lite", budget_tokens=None)
        script = tmp_path / ".claude" / "hooks" / "budget-reminder.sh"
        result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error:\n{result.stderr}"

    def test_script_is_executable(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite", budget_tokens=500000)
        script = tmp_path / ".claude" / "hooks" / "budget-reminder.sh"
        mode = script.stat().st_mode
        assert mode & 0o755 == 0o755

    def test_script_has_standard_structure(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite", budget_tokens=500000)
        content = (tmp_path / ".claude" / "hooks" / "budget-reminder.sh").read_text()
        assert content.startswith("#!/usr/bin/env bash\n")
        assert "# cc-rig hook: budget-reminder" in content
        assert "set -euo pipefail" in content
        assert content.rstrip().endswith("exit 0")

    def test_hook_in_settings_json(self, tmp_path):
        import json

        self._generate_with_harness(tmp_path, "lite", budget_tokens=500000)
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        stop_hooks = data.get("hooks", {}).get("Stop", [])
        commands = [
            h["command"]
            for entry in stop_hooks
            for h in entry.get("hooks", [])
            if h.get("type") == "command"
        ]
        assert any("budget-reminder" in c for c in commands)

    def test_hook_not_in_settings_json_for_b0(self, tmp_path):
        import json

        self._generate_with_harness(tmp_path, "none")
        data = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        all_commands = []
        for event_hooks in data.get("hooks", {}).values():
            for entry in event_hooks:
                for h in entry.get("hooks", []):
                    if h.get("type") == "command" and "command" in h:
                        all_commands.append(h["command"])
        assert not any("budget-reminder" in c for c in all_commands)

    def test_script_has_session_cost_parsing(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite", budget_tokens=500000)
        content = (tmp_path / ".claude" / "hooks" / "budget-reminder.sh").read_text()
        assert "python3" in content
        assert "jsonl" in content.lower()

    def test_script_has_graceful_degradation(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite", budget_tokens=500000)
        content = (tmp_path / ".claude" / "hooks" / "budget-reminder.sh").read_text()
        assert "command -v python3" in content
        assert "unavailable" in content

    def test_script_has_estimated_cost_display(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite", budget_tokens=500000)
        content = (tmp_path / ".claude" / "hooks" / "budget-reminder.sh").read_text()
        assert "Est. cost" in content

    def test_script_has_session_tokens_display(self, tmp_path):
        self._generate_with_harness(tmp_path, "lite", budget_tokens=500000)
        content = (tmp_path / ".claude" / "hooks" / "budget-reminder.sh").read_text()
        assert "Session tokens" in content


# ---------------------------------------------------------------------------
# enabledPlugins in settings.json
# ---------------------------------------------------------------------------


class TestEnabledPlugins:
    """Verify enabledPlugins section in settings.json."""

    def _make_config(self):
        return compute_defaults("fastapi", "standard", project_name="test-project")

    def test_plugins_present_when_config_has_plugins(self, tmp_path):
        from cc_rig.config.project import PluginRecommendation

        config = self._make_config()
        config.recommended_plugins = [
            PluginRecommendation(name="pyright-lsp", category="lsp"),
            PluginRecommendation(name="github", category="integration"),
        ]
        generate_settings(config, tmp_path)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert "enabledPlugins" in settings
        assert settings["enabledPlugins"]["pyright-lsp@claude-plugins-official"] is True
        assert settings["enabledPlugins"]["github@claude-plugins-official"] is True

    def test_no_plugins_key_when_empty(self, tmp_path):
        config = self._make_config()
        config.recommended_plugins = []
        generate_settings(config, tmp_path)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert "enabledPlugins" not in settings

    def test_plugin_key_format(self, tmp_path):
        from cc_rig.config.project import PluginRecommendation

        config = self._make_config()
        config.recommended_plugins = [
            PluginRecommendation(
                name="commit-commands",
                marketplace="claude-plugins-official",
                category="workflow",
            ),
        ]
        generate_settings(config, tmp_path)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        plugins = settings["enabledPlugins"]
        assert len(plugins) == 1
        key = list(plugins.keys())[0]
        assert key == "commit-commands@claude-plugins-official"
        assert plugins[key] is True

    def test_multiple_plugins(self, tmp_path):
        from cc_rig.config.project import PluginRecommendation

        config = self._make_config()
        config.recommended_plugins = [
            PluginRecommendation(name="pyright-lsp", category="lsp"),
            PluginRecommendation(name="github", category="integration"),
            PluginRecommendation(name="commit-commands", category="workflow"),
            PluginRecommendation(name="code-review", category="workflow"),
        ]
        generate_settings(config, tmp_path)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert len(settings["enabledPlugins"]) == 4

    def test_ralph_loop_plugin_in_settings(self, tmp_path):
        from cc_rig.config.project import PluginRecommendation

        config = self._make_config()
        config.recommended_plugins = [
            PluginRecommendation(name="ralph-loop", category="autonomy"),
        ]
        generate_settings(config, tmp_path)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert "ralph-loop@claude-plugins-official" in settings["enabledPlugins"]

    def test_generated_plugins_from_compute_defaults(self, tmp_path):
        """Verify compute_defaults output produces enabledPlugins in settings."""
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_settings(config, tmp_path)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        assert "enabledPlugins" in settings
        assert "pyright-lsp@claude-plugins-official" in settings["enabledPlugins"]
        assert "github@claude-plugins-official" in settings["enabledPlugins"]

    def test_enabled_plugins_values_are_boolean(self, tmp_path):
        """enabledPlugins values must be boolean True, not strings or ints."""
        config = self._make_config()
        generate_settings(config, tmp_path)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        for key, val in settings.get("enabledPlugins", {}).items():
            assert val is True, f"{key} value is {val!r}, expected True (boolean)"


class TestV21SettingsFields:
    """V2.1: effortLevel and includeGitInstructions in settings.json."""

    def _settings(self, template, workflow, tmp_path):
        config = compute_defaults(template, workflow, project_name="test")
        generate_settings(config, tmp_path)
        return json.loads((tmp_path / ".claude" / "settings.json").read_text())

    def test_effort_level_present(self, tmp_path):
        settings = self._settings("fastapi", "standard", tmp_path)
        assert "effortLevel" in settings

    def test_speedrun_has_low_effort(self, tmp_path):
        settings = self._settings("fastapi", "speedrun", tmp_path)
        assert settings["effortLevel"] == "low"

    def test_standard_has_medium_effort(self, tmp_path):
        settings = self._settings("fastapi", "standard", tmp_path)
        assert settings["effortLevel"] == "medium"

    def test_superpowers_has_high_effort(self, tmp_path):
        settings = self._settings("fastapi", "superpowers", tmp_path)
        assert settings["effortLevel"] == "high"

    def test_spec_driven_has_high_effort(self, tmp_path):
        settings = self._settings("fastapi", "spec-driven", tmp_path)
        assert settings["effortLevel"] == "high"

    def test_gstack_has_medium_effort(self, tmp_path):
        settings = self._settings("fastapi", "gstack", tmp_path)
        assert settings["effortLevel"] == "medium"

    def test_include_git_instructions_false_for_superpowers(self, tmp_path):
        settings = self._settings("fastapi", "superpowers", tmp_path)
        assert settings["includeGitInstructions"] is False

    def test_include_git_instructions_false_for_verify_heavy(self, tmp_path):
        settings = self._settings("fastapi", "verify-heavy", tmp_path)
        assert settings["includeGitInstructions"] is False

    def test_include_git_instructions_false_for_spec_driven(self, tmp_path):
        settings = self._settings("fastapi", "spec-driven", tmp_path)
        assert settings["includeGitInstructions"] is False

    def test_include_git_instructions_absent_for_standard(self, tmp_path):
        settings = self._settings("fastapi", "standard", tmp_path)
        assert "includeGitInstructions" not in settings

    def test_include_git_instructions_absent_for_speedrun(self, tmp_path):
        settings = self._settings("fastapi", "speedrun", tmp_path)
        assert "includeGitInstructions" not in settings
