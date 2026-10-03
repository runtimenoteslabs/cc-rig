"""Unit tests for cc-rig tune auto-fixers."""

from __future__ import annotations

from cc_rig.config.cc_version import PINNED_CC_VERSION_STR
from cc_rig.generators.fileops import FileTracker
from cc_rig.tune.fixers import (
    FIXERS,
    _add_bullet_to_section,
    _fix_add_commands,
    _fix_add_secrets,
    _fix_move_date,
    _fix_pin_version,
    apply_fixes,
)
from cc_rig.tune.score import TuneContext, compute_tune_report


def _ctx(tmp_path, cm="", config=None):
    return TuneContext(project_dir=tmp_path, claude_md=cm, config=config)


class TestAddBulletToSection:
    def test_appends_to_existing_section(self):
        cm = "# t\n\n## Guardrails\n\n- a\n\n## Current Context\n- x\n"
        out = _add_bullet_to_section(cm, "## Guardrails", "- b")
        assert "- a" in out and "- b" in out
        assert out.index("## Guardrails") < out.index("- b") < out.index("## Current Context")

    def test_creates_missing_section_before_current_context(self):
        cm = "# t\n\n## Current Context\n- x\n"
        out = _add_bullet_to_section(cm, "## Guardrails", "- b")
        assert out.index("## Guardrails") < out.index("## Current Context")

    def test_preserves_trailing_newline(self):
        assert _add_bullet_to_section("# t\n## Guardrails\n- a\n", "## Guardrails", "- b").endswith(
            "\n"
        )


class TestPinVersion:
    def test_adds_when_missing(self, tmp_path):
        out = _fix_pin_version("# t\n\n- **Stack**: py\n\n## X\n", _ctx(tmp_path))
        assert "Claude Code" in out and PINNED_CC_VERSION_STR in out

    def test_idempotent_when_present(self, tmp_path):
        assert _fix_pin_version("# t\n- **Claude Code**: v2.1.150\n", _ctx(tmp_path)) is None


class TestGuardrailFixers:
    def test_add_secrets(self, tmp_path):
        out = _fix_add_secrets("# t\n\n## Guardrails\n\n- x\n", _ctx(tmp_path))
        assert "API keys" in out

    def test_secrets_idempotent(self, tmp_path):
        cm = "# t\n- Never read, output, or log API keys, tokens.\n"
        assert _fix_add_secrets(cm, _ctx(tmp_path)) is None


class TestAddCommands:
    def test_noop_without_config(self, tmp_path):
        assert _fix_add_commands("# t\n", _ctx(tmp_path, config=None)) is None

    def test_adds_with_config(self, tmp_path):
        from cc_rig.config.defaults import compute_defaults

        cfg = compute_defaults("fastapi", "standard", project_name="p")
        cm = "# t\n\n## Guardrails\n- x\n\n## Current Context\n"
        out = _fix_add_commands(cm, _ctx(tmp_path, config=cfg))
        assert "## Commands" in out
        assert out.index("## Commands") < out.index("## Guardrails")

    def test_noop_when_commands_present(self, tmp_path):
        from cc_rig.config.defaults import compute_defaults

        cfg = compute_defaults("fastapi", "standard", project_name="p")
        assert _fix_add_commands("# t\n## Commands\n- t\n", _ctx(tmp_path, config=cfg)) is None


class TestMoveDate:
    def test_moves_date_below_current_context(self, tmp_path):
        cm = "# t\n\nLast updated: 2026-05-01\n\n## Commands\n- t\n\n## Current Context\n- task\n"
        out = _fix_move_date(cm, _ctx(tmp_path))
        cc = out.index("## Current Context")
        assert "2026-05-01" not in out[:cc]
        assert "2026-05-01" in out[cc:]

    def test_noop_when_no_date_in_static(self, tmp_path):
        assert _fix_move_date("# t\n## Commands\n## Current Context\n", _ctx(tmp_path)) is None


class TestApplyFixes:
    def _sparse(self, tmp_path, cm):
        (tmp_path / "CLAUDE.md").write_text(cm)
        ctx = TuneContext(project_dir=tmp_path, claude_md=cm)
        return ctx, compute_tune_report(ctx)

    def test_safe_fixes_applied_and_backed_up(self, tmp_path):
        ctx, report = self._sparse(tmp_path, "# myproj\n\nA project.\n\n## Current Context\n- t\n")
        results = apply_fixes(report, ctx, FileTracker(tmp_path), include_unsafe=False)
        assert [r for r in results if r.applied]
        assert all(r.safe for r in results)  # unsafe never reaches results without the flag
        new = (tmp_path / "CLAUDE.md").read_text()
        assert "## Guardrails" in new and "Claude Code" in new
        assert (tmp_path / ".cc-rig-backup" / "CLAUDE.md.bak").exists()

    def test_unsafe_skipped_by_default(self, tmp_path):
        cm = "# myproj\n\nLast updated: 2026-05-01\n\n## Current Context\n- t\n"
        ctx, report = self._sparse(tmp_path, cm)
        results = apply_fixes(report, ctx, FileTracker(tmp_path), include_unsafe=False)
        assert not any(r.fix_id == "cache.move_date" for r in results)

    def test_unsafe_applied_with_flag(self, tmp_path):
        cm = "# myproj\n\nLast updated: 2026-05-01\n\n## Current Context\n- t\n"
        ctx, report = self._sparse(tmp_path, cm)
        results = apply_fixes(report, ctx, FileTracker(tmp_path), include_unsafe=True)
        assert any(r.fix_id == "cache.move_date" and r.applied for r in results)

    def test_registry_safety_split(self):
        assert FIXERS["currency.pin_version"].safe is True
        assert FIXERS["cache.move_date"].safe is False
