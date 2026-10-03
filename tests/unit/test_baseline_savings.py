"""Tests for the savings rollup module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cc_rig.baseline.jsonl import SessionSummary
from cc_rig.baseline.savings import (
    CacheBreaker,
    SavingsReport,
    compute_savings_report,
    iso_week_start,
    parse_iso_timestamp,
    update_baseline_with_report,
)
from cc_rig.baseline.schema import Baseline, ProjectEntry, WeeklyRollup


def _make_summary(
    *,
    ended_at: str,
    cost_usd: float = 1.0,
    cost_uncached_usd: float = 5.0,
    input_tokens: int = 100,
    cache_read_tokens: int = 1000,
    cache_create_tokens: int = 200,
    output_tokens: int = 50,
    claudemd_edits: int = 0,
    model_switches: int = 0,
    model_switch_cost_usd: float = 0.0,
    primary_family: str = "sonnet",
) -> SessionSummary:
    return SessionSummary(
        session_id=f"sess-{ended_at}",
        file_path=f"/tmp/{ended_at}.jsonl",
        file_mtime=0.0,
        started_at=ended_at,
        ended_at=ended_at,
        primary_family=primary_family,
        input_tokens=input_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_create_tokens=cache_create_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        cost_uncached_usd=cost_uncached_usd,
        claudemd_edits=claudemd_edits,
        model_switches=model_switches,
        model_switch_cost_usd=model_switch_cost_usd,
    )


# ---------- parse_iso_timestamp -------------------------------------------


def test_parse_iso_timestamp_handles_z_suffix():
    dt = parse_iso_timestamp("2026-05-04T10:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2026 and dt.month == 5 and dt.day == 4


def test_parse_iso_timestamp_handles_explicit_offset():
    dt = parse_iso_timestamp("2026-05-04T10:00:00+02:00")
    assert dt is not None
    # Converted to UTC: 08:00
    assert dt.hour == 8


def test_parse_iso_timestamp_returns_none_for_garbage():
    assert parse_iso_timestamp("") is None
    assert parse_iso_timestamp("not a timestamp") is None
    assert parse_iso_timestamp(None) is None  # type: ignore[arg-type]


# ---------- iso_week_start ------------------------------------------------


def test_iso_week_start_returns_monday():
    # 2026-05-04 is a Monday.
    monday = datetime(2026, 5, 4, 15, 0, tzinfo=timezone.utc)
    assert iso_week_start(monday).isoformat() == "2026-05-04"


def test_iso_week_start_works_across_the_week():
    # 2026-05-09 is a Saturday; Monday of that week is 2026-05-04.
    saturday = datetime(2026, 5, 9, 23, 59, tzinfo=timezone.utc)
    assert iso_week_start(saturday).isoformat() == "2026-05-04"


# ---------- window filter -------------------------------------------------


def test_compute_savings_report_filters_outside_window():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    summaries = [
        _make_summary(ended_at="2026-05-13T10:00:00Z"),  # inside 30d window
        _make_summary(ended_at="2026-03-01T10:00:00Z"),  # outside 30d
    ]
    report = compute_savings_report(
        summaries, project_hash="h", project_name="p", now=now, window_days=30
    )
    assert report.session_count == 1


def test_compute_savings_report_window_days_configurable():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    summaries = [
        _make_summary(ended_at="2026-05-10T10:00:00Z"),  # 4 days ago
        _make_summary(ended_at="2026-05-05T10:00:00Z"),  # 9 days ago
    ]
    seven_day = compute_savings_report(
        summaries, project_hash="h", project_name="p", now=now, window_days=7
    )
    assert seven_day.session_count == 1
    thirty_day = compute_savings_report(
        summaries, project_hash="h", project_name="p", now=now, window_days=30
    )
    assert thirty_day.session_count == 2


# ---------- aggregates ----------------------------------------------------


def test_compute_savings_report_aggregates_tokens_and_cost():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    summaries = [
        _make_summary(
            ended_at="2026-05-10T10:00:00Z",
            cost_usd=1.0,
            cost_uncached_usd=5.0,
            input_tokens=100,
            cache_read_tokens=1000,
        ),
        _make_summary(
            ended_at="2026-05-11T10:00:00Z",
            cost_usd=2.0,
            cost_uncached_usd=10.0,
            input_tokens=200,
            cache_read_tokens=2000,
        ),
    ]
    r = compute_savings_report(summaries, project_hash="h", project_name="p", now=now)
    assert r.session_count == 2
    assert r.input_tokens == 300
    assert r.cache_read_tokens == 3000
    assert r.cost_usd == 3.0
    assert r.cost_uncached_usd == 15.0
    # savings_pct = 100 * (1 - 3/15) = 80
    assert r.savings_pct == 80.0


def test_compute_savings_report_savings_pct_zero_when_no_uncached():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    summaries = [_make_summary(ended_at="2026-05-10T10:00:00Z", cost_uncached_usd=0.0)]
    r = compute_savings_report(summaries, project_hash="h", project_name="p", now=now)
    assert r.savings_pct == 0.0


def test_compute_savings_report_primary_family_is_mode():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    summaries = [
        _make_summary(ended_at="2026-05-10T10:00:00Z", primary_family="sonnet"),
        _make_summary(ended_at="2026-05-11T10:00:00Z", primary_family="sonnet"),
        _make_summary(ended_at="2026-05-12T10:00:00Z", primary_family="opus"),
    ]
    r = compute_savings_report(summaries, project_hash="h", project_name="p", now=now)
    assert r.primary_family == "sonnet"


# ---------- weekly trend --------------------------------------------------


def test_compute_savings_report_weekly_trend_has_requested_length():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    r = compute_savings_report(
        [_make_summary(ended_at="2026-05-12T10:00:00Z")],
        project_hash="h",
        project_name="p",
        now=now,
        weeks=4,
    )
    assert len(r.weekly_trend) == 4


def test_compute_savings_report_weekly_trend_is_oldest_first():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)  # week of 2026-05-11
    r = compute_savings_report(
        [_make_summary(ended_at="2026-05-12T10:00:00Z")],
        project_hash="h",
        project_name="p",
        now=now,
        weeks=4,
    )
    weeks = [w.week_start for w in r.weekly_trend]
    # 4 weeks ending at 2026-05-11: 2026-04-20, -04-27, -05-04, -05-11
    assert weeks == ["2026-04-20", "2026-04-27", "2026-05-04", "2026-05-11"]


def test_compute_savings_report_buckets_sessions_into_correct_week():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    summaries = [
        _make_summary(ended_at="2026-05-04T10:00:00Z"),  # week 2026-05-04
        _make_summary(ended_at="2026-05-06T10:00:00Z"),  # same week
        _make_summary(ended_at="2026-05-12T10:00:00Z"),  # week 2026-05-11
    ]
    r = compute_savings_report(summaries, project_hash="h", project_name="p", now=now, weeks=4)
    counts = {w.week_start: w.session_count for w in r.weekly_trend}
    assert counts["2026-05-04"] == 2
    assert counts["2026-05-11"] == 1
    assert counts["2026-04-27"] == 0


def test_compute_savings_report_empty_weeks_have_zero_rollups():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    r = compute_savings_report([], project_hash="h", project_name="p", now=now, weeks=4)
    assert all(w.session_count == 0 for w in r.weekly_trend)
    assert all(w.cost_usd == 0.0 for w in r.weekly_trend)


# ---------- cache breakers -----------------------------------------------


def test_cache_breakers_only_emit_when_present():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    summaries = [_make_summary(ended_at="2026-05-10T10:00:00Z")]  # no edits, no switches
    r = compute_savings_report(summaries, project_hash="h", project_name="p", now=now)
    assert r.cache_breakers == []


def test_cache_breakers_count_claudemd_edit_sessions():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    summaries = [
        _make_summary(ended_at="2026-05-10T10:00:00Z", claudemd_edits=2),
        _make_summary(ended_at="2026-05-11T10:00:00Z", claudemd_edits=0),
        _make_summary(ended_at="2026-05-12T10:00:00Z", claudemd_edits=5),
    ]
    r = compute_savings_report(summaries, project_hash="h", project_name="p", now=now)
    names = {b.name for b in r.cache_breakers}
    assert "CLAUDE.md edits during session" in names
    edit_breaker = next(b for b in r.cache_breakers if "CLAUDE.md" in b.name)
    # 2 sessions had any CLAUDE.md edits
    assert edit_breaker.session_count == 2


def test_cache_breakers_count_model_switch_sessions():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    summaries = [
        _make_summary(ended_at="2026-05-12T10:00:00Z", model_switches=2, cache_read_tokens=10000),
    ]
    r = compute_savings_report(summaries, project_hash="h", project_name="p", now=now)
    sw = next(b for b in r.cache_breakers if "switch" in b.name.lower())
    assert sw.session_count == 1


def test_model_switch_cost_is_the_measured_rewrite_not_the_sessions_reads():
    """A switch re-caches once. It must not be charged every read in the session."""
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    summaries = [
        _make_summary(
            ended_at="2026-05-12T10:00:00Z",
            cost_usd=26.0,
            cache_read_tokens=66_000_000,
            model_switches=1,
            model_switch_cost_usd=0.11,
        ),
        _make_summary(
            ended_at="2026-05-13T10:00:00Z",
            model_switches=1,
            model_switch_cost_usd=0.04,
        ),
    ]
    r = compute_savings_report(summaries, project_hash="h", project_name="p", now=now)
    sw = next(b for b in r.cache_breakers if "switch" in b.name.lower())
    assert sw.session_count == 2
    assert sw.estimated_cost_usd == pytest.approx(0.15)


# ---------- cross-project rank --------------------------------------------


def test_cross_project_rank_none_with_single_project():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    baseline = Baseline(
        schema_version=1,
        user_id_hash="u",
        projects={
            "h": ProjectEntry(
                name="solo",
                tier="standard",
                weekly_savings_history=[WeeklyRollup(week_start="2026-05-04", savings_pct=80.0)],
            ),
        },
    )
    r = compute_savings_report(
        [_make_summary(ended_at="2026-05-12T10:00:00Z")],
        project_hash="h",
        project_name="solo",
        baseline=baseline,
        now=now,
    )
    assert r.cross_project_rank is None


def test_cross_project_rank_with_multiple_projects():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    baseline = Baseline(
        schema_version=1,
        user_id_hash="u",
        projects={
            "h": ProjectEntry(
                name="this",
                tier="standard",
                weekly_savings_history=[WeeklyRollup(week_start="2026-05-04", savings_pct=70.0)],
            ),
            "other_high": ProjectEntry(
                name="other_high",
                tier="standard",
                weekly_savings_history=[WeeklyRollup(week_start="2026-05-04", savings_pct=90.0)],
            ),
            "other_low": ProjectEntry(
                name="other_low",
                tier="standard",
                weekly_savings_history=[WeeklyRollup(week_start="2026-05-04", savings_pct=40.0)],
            ),
        },
    )
    # This project's current savings_pct = 80 -> middle of three (90, 80, 40)
    summaries = [
        _make_summary(
            ended_at="2026-05-12T10:00:00Z",
            cost_usd=2.0,
            cost_uncached_usd=10.0,
        ),
    ]
    r = compute_savings_report(
        summaries, project_hash="h", project_name="this", baseline=baseline, now=now
    )
    assert r.cross_project_rank == (2, 3)


def test_cross_project_rank_skips_projects_with_no_history():
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    baseline = Baseline(
        schema_version=1,
        user_id_hash="u",
        projects={
            "h": ProjectEntry(
                name="this",
                tier="standard",
                weekly_savings_history=[WeeklyRollup(week_start="2026-05-04", savings_pct=85.0)],
            ),
            "no_data": ProjectEntry(name="no_data", tier="standard", weekly_savings_history=[]),
        },
    )
    r = compute_savings_report(
        [_make_summary(ended_at="2026-05-12T10:00:00Z", cost_usd=1.0, cost_uncached_usd=5.0)],
        project_hash="h",
        project_name="this",
        baseline=baseline,
        now=now,
    )
    # only one comparable project -> rank cannot be computed
    assert r.cross_project_rank is None


# ---------- SavingsReport.to_dict ----------------------------------------


def test_savings_report_to_dict_is_json_serializable():
    import json

    r = SavingsReport(
        project_hash="h",
        project_name="p",
        window_days=30,
        weekly_trend=[WeeklyRollup(week_start="2026-05-04", session_count=3)],
        cache_breakers=[CacheBreaker(name="x", session_count=1)],
        cross_project_rank=(1, 2),
    )
    d = r.to_dict()
    s = json.dumps(d)
    parsed = json.loads(s)
    assert parsed["cross_project_rank"] == [1, 2]
    assert parsed["weekly_trend"][0]["week_start"] == "2026-05-04"
    assert parsed["cache_breakers"][0]["name"] == "x"


# ---------- update_baseline_with_report -----------------------------------


def test_update_baseline_creates_project_entry_on_first_run():
    baseline = Baseline()
    report = SavingsReport(
        project_hash="h",
        project_name="proj",
        window_days=30,
        weekly_trend=[
            WeeklyRollup(week_start="2026-05-04", session_count=2, cost_usd=1.0, savings_pct=70.0),
            WeeklyRollup(week_start="2026-05-11", session_count=3, cost_usd=2.0, savings_pct=80.0),
        ],
    )
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    updated = update_baseline_with_report(
        baseline,
        project_hash="h",
        project_name="proj",
        tier="standard",
        report=report,
        now=now,
    )
    entry = updated.projects["h"]
    assert entry.name == "proj"
    assert entry.tier == "standard"
    assert len(entry.weekly_savings_history) == 2
    assert entry.weekly_savings_history[0].week_start == "2026-05-04"


def test_update_baseline_preserves_older_history_and_upserts_recent_weeks():
    baseline = Baseline(
        schema_version=1,
        user_id_hash="u",
        projects={
            "h": ProjectEntry(
                name="proj",
                tier="standard",
                weekly_savings_history=[
                    WeeklyRollup(week_start="2026-04-13", session_count=5, savings_pct=60.0),
                    WeeklyRollup(week_start="2026-05-04", session_count=1, savings_pct=50.0),
                ],
            ),
        },
    )
    # New report covers weeks of 2026-05-04 (with more data) and 2026-05-11 (new).
    report = SavingsReport(
        project_hash="h",
        project_name="proj",
        window_days=30,
        weekly_trend=[
            WeeklyRollup(week_start="2026-05-04", session_count=4, savings_pct=75.0),
            WeeklyRollup(week_start="2026-05-11", session_count=3, savings_pct=80.0),
        ],
    )
    now = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
    updated = update_baseline_with_report(
        baseline,
        project_hash="h",
        project_name="proj",
        tier="standard",
        report=report,
        now=now,
    )
    weeks = {w.week_start: w for w in updated.projects["h"].weekly_savings_history}
    assert set(weeks.keys()) == {"2026-04-13", "2026-05-04", "2026-05-11"}
    # 2026-05-04 must have been overwritten with the fresher data
    assert weeks["2026-05-04"].session_count == 4
    assert weeks["2026-05-04"].savings_pct == 75.0
    # Older untouched week preserved
    assert weeks["2026-04-13"].session_count == 5


def test_update_baseline_skips_empty_weeks():
    baseline = Baseline()
    report = SavingsReport(
        project_hash="h",
        project_name="proj",
        window_days=30,
        weekly_trend=[
            WeeklyRollup(week_start="2026-04-20", session_count=0),  # empty
            WeeklyRollup(week_start="2026-05-11", session_count=3, savings_pct=80.0),
        ],
    )
    updated = update_baseline_with_report(
        baseline, project_hash="h", project_name="proj", tier="standard", report=report
    )
    weeks = [w.week_start for w in updated.projects["h"].weekly_savings_history]
    assert weeks == ["2026-05-11"]
