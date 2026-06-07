"""Unit tests for the cc-rig tune scoring engine (pure aggregation)."""

from __future__ import annotations

import json

import pytest

from cc_rig.tune.score import (
    DimensionScore,
    Opportunity,
    TuneContext,
    compute_tune_report,
    grade_for,
    rank_opportunities,
)


class TestGradeFor:
    @pytest.mark.parametrize(
        "score,grade",
        [
            (100, "Production Ready"),
            (80, "Production Ready"),
            (79, "Getting There"),
            (60, "Getting There"),
            (59, "Needs Work"),
            (35, "Needs Work"),
            (34, "Critical"),
            (0, "Critical"),
        ],
    )
    def test_bands(self, score, grade):
        assert grade_for(score) == grade


class TestRankOpportunities:
    def test_dollar_findings_first_by_amount(self):
        opps = [
            Opportunity("a", "d", severity="high"),
            Opportunity("b", "d", est_monthly_usd=5.0),
            Opportunity("c", "d", est_monthly_usd=20.0),
        ]
        assert [o.title for o in rank_opportunities(opps)] == ["c", "b", "a"]

    def test_severity_orders_non_dollar(self):
        opps = [
            Opportunity("low1", "d", severity="low"),
            Opportunity("high1", "d", severity="high"),
            Opportunity("med1", "d", severity="med"),
        ]
        assert [o.title for o in rank_opportunities(opps)] == ["high1", "med1", "low1"]


class TestCompositeAggregation:
    def test_weighted_composite(self, tmp_path):
        def d1(ctx):
            return DimensionScore("a", "A", 0.75, 100, [])

        def d2(ctx):
            return DimensionScore("b", "B", 0.25, 0, [Opportunity("x", "b", est_monthly_usd=1.0)])

        rep = compute_tune_report(TuneContext(project_dir=tmp_path), dimensions=[d1, d2])
        assert rep.overall == 75  # 100*0.75 + 0*0.25
        assert rep.grade == "Getting There"
        assert len(rep.opportunities) == 1

    def test_project_name_from_dir(self, tmp_path):
        rep = compute_tune_report(
            TuneContext(project_dir=tmp_path),
            dimensions=[lambda c: DimensionScore("a", "A", 1.0, 90, [])],
        )
        assert rep.project_name == tmp_path.name

    def test_to_dict_is_json_serializable(self, tmp_path):
        def d1(ctx):
            return DimensionScore(
                "a", "A", 1.0, 90, [Opportunity("x", "a", "why", severity="high", fixable=True)]
            )

        rep = compute_tune_report(TuneContext(project_dir=tmp_path), dimensions=[d1])
        d = rep.to_dict()
        assert d["overall"] == 90
        assert d["dimensions"][0]["opportunities"][0]["title"] == "x"
        assert d["dimensions"][0]["opportunities"][0]["fixable"] is True
        json.dumps(d)  # must not raise

    def test_cache_ratio_propagated_from_savings(self, tmp_path):
        from cc_rig.baseline.savings import SavingsReport

        sv = SavingsReport(
            project_hash="x",
            project_name="p",
            window_days=30,
            session_count=5,
            cache_read_ratio=0.66,
        )
        rep = compute_tune_report(
            TuneContext(project_dir=tmp_path, savings=sv, sessions_seen=5),
            dimensions=[lambda c: DimensionScore("a", "A", 1.0, 100, [])],
        )
        assert rep.cache_read_ratio == 0.66
        assert rep.sessions_seen == 5
