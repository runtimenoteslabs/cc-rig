"""Unit tests for the six cc-rig tune dimensions."""

from __future__ import annotations

from cc_rig.baseline.savings import CacheBreaker, SavingsReport
from cc_rig.tune.dimensions import (
    cache_hygiene,
    context_discipline,
    currency,
    safety_guards,
    verification,
    workflow_fit,
)
from cc_rig.tune.score import TuneContext

# A clean, lean CLAUDE.md that should score 100 on every dimension.
_CLEAN_CM = """# proj

- **Claude Code**: v2.1.150 (cc-rig pinned)

## Commands
- **Test**: `pytest`
- **Format**: `ruff format .`

## Guardrails
- Run tests before committing. Run lint before pushing.
- Never read, output, or log API keys, private keys, tokens, or seed phrases.
- Never push directly to main/master.
- Never run destructive commands (rm -rf /, DROP TABLE).

## Agent Docs
Read @agent_docs/cache-friendly-workflow.md

## Current Context
- updated 2026-05-01
"""


def _ctx(tmp_path, cm=_CLEAN_CM, settings=None, savings=None, config=None):
    return TuneContext(
        project_dir=tmp_path,
        claude_md=cm,
        settings=settings or {},
        config=config,
        savings=savings,
    )


def _savings(ratio=0.8, family="sonnet", sessions=10, breakers=None):
    return SavingsReport(
        project_hash="x",
        project_name="p",
        window_days=30,
        session_count=sessions,
        cache_read_ratio=ratio,
        primary_family=family,
        cache_breakers=breakers or [],
    )


class TestCacheHygiene:
    def test_clean_scores_full(self, tmp_path):
        d = cache_hygiene(_ctx(tmp_path))
        assert d.score == 100
        assert d.opportunities == []

    def test_date_below_current_context_not_penalized(self, tmp_path):
        # The "updated 2026-05-01" lives under ## Current Context (dynamic zone).
        assert cache_hygiene(_ctx(tmp_path)).score == 100

    def test_date_in_static_zone_penalized(self, tmp_path):
        cm = _CLEAN_CM.replace("## Commands", "Last updated: 2026-05-01\n\n## Commands", 1)
        d = cache_hygiene(_ctx(tmp_path, cm=cm))
        assert d.score < 100
        assert any("static section" in o.title.lower() for o in d.opportunities)

    def test_dollar_estimate_present_with_savings(self, tmp_path):
        cm = _CLEAN_CM.replace("## Commands", "As of 2026-05-01\n\n## Commands", 1)
        d = cache_hygiene(_ctx(tmp_path, cm=cm, savings=_savings(family="opus")))
        dollar = [o for o in d.opportunities if o.est_monthly_usd is not None]
        assert dollar and dollar[0].est_monthly_usd > 0

    def test_no_dollar_without_savings(self, tmp_path):
        cm = _CLEAN_CM.replace("## Commands", "As of 2026-05-01\n\n## Commands", 1)
        d = cache_hygiene(_ctx(tmp_path, cm=cm, savings=None))
        assert all(o.est_monthly_usd is None for o in d.opportunities)

    def test_low_cache_ratio_penalized(self, tmp_path):
        assert cache_hygiene(_ctx(tmp_path, savings=_savings(ratio=0.30))).score < 100

    def test_breaker_becomes_dollar_opportunity(self, tmp_path):
        sv = _savings(
            breakers=[CacheBreaker("Mid-session model switches", 3, 9.0, "d")],
        )
        d = cache_hygiene(_ctx(tmp_path, savings=sv))
        assert any(o.est_monthly_usd == 9.0 for o in d.opportunities)


class TestSafetyGuards:
    def test_clean_full(self, tmp_path):
        assert safety_guards(_ctx(tmp_path)).score == 100

    def test_missing_all_three(self, tmp_path):
        d = safety_guards(_ctx(tmp_path, cm="# proj\n## Commands\n"))
        assert d.score <= 20
        assert len(d.opportunities) == 3

    def test_hook_scripts_credit_destructive_and_main(self, tmp_path):
        hooks = tmp_path / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "block-rm-rf.sh").write_text("# guard\nrm -rf protection\n")
        settings = {
            "hooks": {
                "PreToolUse": [
                    {"hooks": [{"type": "command", "command": "bash .claude/hooks/block-main.sh"}]}
                ]
            }
        }
        d = safety_guards(_ctx(tmp_path, cm="# proj\n", settings=settings))
        titles = " ".join(o.title.lower() for o in d.opportunities)
        assert "destructive" not in titles  # credited via script
        assert "block-push" not in titles  # credited via hook command
        assert "secret" in titles  # still missing


class TestContextDiscipline:
    def test_small_full(self, tmp_path):
        assert context_discipline(_ctx(tmp_path)).score == 100

    def test_large_penalized(self, tmp_path):
        big = "# proj\n" + ("padding " * 1600)  # > 2500 tokens
        d = context_discipline(_ctx(tmp_path, cm=big))
        assert d.score <= 70
        assert any("trim" in o.title.lower() for o in d.opportunities)

    def test_oversized_memory_file(self, tmp_path):
        mem = tmp_path / "memory"
        mem.mkdir()
        (mem / "big.md").write_text("\n".join("line" for _ in range(450)))
        d = context_discipline(_ctx(tmp_path))
        assert any("memory" in o.title.lower() for o in d.opportunities)


class TestWorkflowFit:
    def test_commands_section_required(self, tmp_path):
        d = workflow_fit(_ctx(tmp_path, cm="# proj\n"))
        assert any("commands" in o.title.lower() for o in d.opportunities)

    def test_commands_fix_offered_only_with_config(self, tmp_path):
        """The fixer writes commands from .cc-rig.json; without it, no fix."""
        from cc_rig.config.defaults import compute_defaults

        def commands_opp(ctx):
            return next(o for o in workflow_fit(ctx).opportunities if "Commands" in o.title)

        bare = commands_opp(_ctx(tmp_path, cm="# proj\n"))
        assert bare.fix_id is None and not bare.fixable
        cfg = compute_defaults("fastapi", "standard", project_name="p")
        configured = commands_opp(_ctx(tmp_path, cm="# proj\n", config=cfg))
        assert configured.fix_id == "workflow.add_commands" and configured.fixable

    def test_format_hook_via_script_credited(self, tmp_path):
        from cc_rig.config.defaults import compute_defaults

        cfg = compute_defaults("fastapi", "standard", project_name="p")
        hooks = tmp_path / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "format.sh").write_text("ruff format $FILE\n")
        d = workflow_fit(_ctx(tmp_path, config=cfg))
        assert not any("formatter" in o.title.lower() for o in d.opportunities)

    def test_missing_format_hook_flagged(self, tmp_path):
        from cc_rig.config.defaults import compute_defaults

        cfg = compute_defaults("fastapi", "standard", project_name="p")
        d = workflow_fit(_ctx(tmp_path, config=cfg))  # no hooks dir
        assert any("formatter" in o.title.lower() for o in d.opportunities)


class TestVerification:
    def test_guardrail_credit(self, tmp_path):
        assert verification(_ctx(tmp_path)).score == 100

    def test_missing_gate_penalized(self, tmp_path):
        d = verification(_ctx(tmp_path, cm="# proj\n## Commands\n"))
        assert d.score < 100
        assert d.opportunities


class TestCurrency:
    def test_clean(self, tmp_path):
        assert currency(_ctx(tmp_path)).score == 100

    def test_unknown_key_flagged(self, tmp_path):
        d = currency(_ctx(tmp_path, settings={"totallyMadeUpKey": 1}))
        assert d.score < 100
        assert any("unknown" in o.title.lower() for o in d.opportunities)

    def test_valid_v2_1_150_keys_pass(self, tmp_path):
        d = currency(_ctx(tmp_path, settings={"model": "x", "skillOverrides": {}}))
        assert not any("unknown" in o.title.lower() for o in d.opportunities)

    def test_missing_version_pin_flagged(self, tmp_path):
        d = currency(_ctx(tmp_path, cm="# proj\n## Commands\n"))
        assert any("pin" in o.title.lower() for o in d.opportunities)
