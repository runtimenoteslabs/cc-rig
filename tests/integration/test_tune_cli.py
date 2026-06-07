"""Integration tests for `cc-rig tune` against generated projects."""

from __future__ import annotations

import argparse
import json

from cc_rig.cli_tune import load_context, run
from cc_rig.tune.score import compute_tune_report
from tests.conftest import generate_project


def _args(tmp_path, **over):
    # projects_dir points at a dir with no session JSONL -> savings stays None,
    # making the score deterministic regardless of the host's ~/.claude.
    base = dict(
        dir=str(tmp_path),
        as_json=False,
        window_days=30,
        projects_dir=tmp_path / "no-sessions",
        cache_path=tmp_path / "parse-cache.json",
        fix=False,
        fix_unsafe=False,
        ci=False,
        min_score=60,
        badge=False,
    )
    base.update(over)
    return argparse.Namespace(**base)


_SPARSE_CM = "# proj\n\nA small project.\n\n## Current Context\n- task: none\n"


class TestTuneOnGeneratedProject:
    def test_fresh_project_scores_high(self, tmp_path):
        generate_project(tmp_path)
        ctx = load_context(tmp_path, projects_dir=tmp_path / "no-sessions")
        report = compute_tune_report(ctx)
        assert report.overall >= 90
        assert report.grade == "Production Ready"
        # cc-rig's own leaned output should not indict itself.
        assert report.opportunities == []

    def test_run_json_returns_zero_and_parses(self, tmp_path, capsys):
        generate_project(tmp_path)
        rc = run(_args(tmp_path, as_json=True))
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["overall"] >= 90
        assert {d["key"] for d in data["dimensions"]} == {
            "cache_hygiene",
            "safety_guards",
            "context_discipline",
            "workflow_fit",
            "verification",
            "currency",
        }

    def test_run_rendered_returns_zero(self, tmp_path, capsys):
        generate_project(tmp_path)
        rc = run(_args(tmp_path, as_json=False))
        assert rc == 0
        out = capsys.readouterr().out
        assert "cc-rig tune" in out
        assert "/ 100" in out
        assert "Cache hygiene" in out


class TestTuneDegradesGracefully:
    def test_empty_dir_low_score_with_opportunities(self, tmp_path):
        ctx = load_context(tmp_path, projects_dir=tmp_path / "no-sessions")
        report = compute_tune_report(ctx)
        assert report.overall < 100
        assert report.opportunities  # missing safety/verification/commands surface

    def test_run_on_empty_dir_returns_zero(self, tmp_path, capsys):
        rc = run(_args(tmp_path, as_json=True))
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert 0 <= data["overall"] <= 100


class TestTuneFix:
    def test_fix_improves_score_and_backs_up(self, tmp_path, capsys):
        (tmp_path / "CLAUDE.md").write_text(_SPARSE_CM)
        before = compute_tune_report(load_context(tmp_path, projects_dir=tmp_path / "no-sessions"))
        rc = run(_args(tmp_path, fix=True))
        assert rc == 0
        out = capsys.readouterr().out
        assert "Applied" in out and "Score:" in out
        after = compute_tune_report(load_context(tmp_path, projects_dir=tmp_path / "no-sessions"))
        assert after.overall > before.overall
        assert "## Guardrails" in (tmp_path / "CLAUDE.md").read_text()
        assert (tmp_path / ".cc-rig-backup" / "CLAUDE.md.bak").exists()

    def test_fix_json_reports_fixes(self, tmp_path, capsys):
        (tmp_path / "CLAUDE.md").write_text(_SPARSE_CM)
        rc = run(_args(tmp_path, fix=True, as_json=True))
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert "fixes" in data and "report" in data
        assert any(f["applied"] for f in data["fixes"])
        assert data["report"]["overall"] > data["before_overall"]

    def test_unsafe_fix_relocates_date(self, tmp_path, capsys):
        cm = "# proj\n\nLast updated: 2026-05-01\n\n## Current Context\n- t\n"
        (tmp_path / "CLAUDE.md").write_text(cm)
        rc = run(_args(tmp_path, fix_unsafe=True))
        assert rc == 0
        new = (tmp_path / "CLAUDE.md").read_text()
        cc = new.index("## Current Context")
        assert "2026-05-01" not in new[:cc]


class TestTuneCiAndBadge:
    def test_ci_fails_below_threshold(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text(_SPARSE_CM)
        rc = run(_args(tmp_path, ci=True, min_score=90))
        assert rc == 1

    def test_ci_passes_for_clean_project(self, tmp_path):
        generate_project(tmp_path)
        rc = run(_args(tmp_path, ci=True, min_score=90))
        assert rc == 0

    def test_badge_emits_shields_json(self, tmp_path, capsys):
        generate_project(tmp_path)
        rc = run(_args(tmp_path, badge=True))
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["schemaVersion"] == 1
        assert data["label"] == "cc-rig tune"
        assert "/100" in data["message"]
        assert data["color"] == "brightgreen"
