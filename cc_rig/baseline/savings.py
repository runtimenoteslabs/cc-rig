"""Longitudinal savings rollups for /cc-rig savings.

Takes a list of SessionSummary objects (produced by jsonl.parse_sessions)
and produces:

  - SavingsReport: aggregate metrics over a configurable window (default 30
    days), a per-week trend (default last 4 weeks, Monday-start), top cache
    breakers, and cross-project rank.

Cache breakers we report are intentionally limited to signals that show up
*reliably* in session JSONLs:

  - CLAUDE.md edits during a session (detectable via tool_use blocks)
  - Mid-session model switches (detectable via message.model transitions)

Hook toggles and plugin reconnects are not in the JSONL stream, so we do
not invent zero metrics for them -- better to omit than fake.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional

from cc_rig.baseline.jsonl import SessionSummary
from cc_rig.baseline.schema import Baseline, ProjectEntry, WeeklyRollup


def parse_iso_timestamp(s: str) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp string into a tz-aware UTC datetime.

    Accepts both 'Z' suffix and explicit offset forms. Returns None on
    malformed input; the caller decides whether to skip or default.
    """
    if not s or not isinstance(s, str):
        return None
    normalized = s.replace("Z", "+00:00") if s.endswith("Z") else s
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso_week_start(dt: datetime) -> date:
    """Return the Monday (UTC date) of the ISO week containing `dt`."""
    d = dt.astimezone(timezone.utc).date()
    return d - timedelta(days=d.weekday())


@dataclass
class CacheBreaker:
    """One named cache-breaker signal, with a count + cost estimate."""

    name: str
    session_count: int = 0
    estimated_cost_usd: float = 0.0
    detail: str = ""


@dataclass
class SavingsReport:
    """The shape /cc-rig savings renders. JSON-serializable via to_dict."""

    project_hash: str
    project_name: str
    window_days: int
    session_count: int = 0
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_create_tokens: int = 0
    cache_create_1h_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cost_uncached_usd: float = 0.0
    savings_pct: float = 0.0
    cache_read_ratio: float = 0.0
    weekly_trend: list = field(default_factory=list)  # list[WeeklyRollup]
    cache_breakers: list = field(default_factory=list)  # list[CacheBreaker]
    cross_project_rank: Optional[tuple] = None  # (rank, total) or None
    primary_family: str = ""
    primary_model: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["weekly_trend"] = [w.to_dict() for w in self.weekly_trend]
        d["cache_breakers"] = [asdict(b) for b in self.cache_breakers]
        d["cross_project_rank"] = (
            list(self.cross_project_rank) if self.cross_project_rank is not None else None
        )
        return d


def _summaries_in_window(
    summaries: Iterable[SessionSummary],
    *,
    now: datetime,
    window_days: int,
) -> list:
    """Filter summaries whose ended_at falls within the last `window_days`."""
    cutoff = now - timedelta(days=window_days)
    kept = []
    for s in summaries:
        end = parse_iso_timestamp(s.ended_at) or parse_iso_timestamp(s.started_at)
        if end is None:
            continue
        if end >= cutoff:
            kept.append(s)
    return kept


def _bucket_by_week(summaries: Iterable[SessionSummary]) -> dict:
    """Group summaries by Monday-start ISO date string."""
    buckets: dict = {}
    for s in summaries:
        end = parse_iso_timestamp(s.ended_at) or parse_iso_timestamp(s.started_at)
        if end is None:
            continue
        week = iso_week_start(end).isoformat()
        buckets.setdefault(week, []).append(s)
    return buckets


def _rollup_for_week(week_start: str, sessions: list) -> WeeklyRollup:
    """Aggregate one week's sessions into a WeeklyRollup."""
    input_tokens = sum(s.input_tokens for s in sessions)
    cache_read = sum(s.cache_read_tokens for s in sessions)
    cache_create = sum(s.cache_create_tokens for s in sessions)
    output_tokens = sum(s.output_tokens for s in sessions)
    cost = sum(s.cost_usd for s in sessions)
    uncached = sum(s.cost_uncached_usd for s in sessions)
    savings_pct = 100.0 * (1.0 - cost / uncached) if uncached > 0 else 0.0
    return WeeklyRollup(
        week_start=week_start,
        input_tokens=input_tokens,
        cache_read_tokens=cache_read,
        cache_create_tokens=cache_create,
        output_tokens=output_tokens,
        cost_usd=round(cost, 4),
        savings_pct=round(savings_pct, 2),
        session_count=len(sessions),
    )


def _weekly_trend(summaries: Iterable[SessionSummary], *, now: datetime, weeks: int) -> list:
    """Return the last `weeks` rollups, oldest-first, with zero-rollups for empty weeks."""
    buckets = _bucket_by_week(summaries)
    current_week = iso_week_start(now)
    trend = []
    for i in range(weeks - 1, -1, -1):
        week_date = current_week - timedelta(weeks=i)
        key = week_date.isoformat()
        trend.append(_rollup_for_week(key, buckets.get(key, [])))
    return trend


def _cache_breakers(summaries: Iterable[SessionSummary]) -> list:
    """Detect and quantify cache-breaker signals across the window."""
    claudemd_sessions = 0
    switch_sessions = 0
    switch_cost_estimate = 0.0

    for s in summaries:
        if s.claudemd_edits > 0:
            claudemd_sessions += 1
        if s.model_switches > 0:
            switch_sessions += 1
            # Measured by the parser: the cache re-write after each switch.
            switch_cost_estimate += s.model_switch_cost_usd

    breakers = []
    if claudemd_sessions:
        breakers.append(
            CacheBreaker(
                name="CLAUDE.md edits during session",
                session_count=claudemd_sessions,
                detail="Editing CLAUDE.md mid-session invalidates the prompt cache prefix.",
            )
        )
    if switch_sessions:
        breakers.append(
            CacheBreaker(
                name="Mid-session model switches",
                session_count=switch_sessions,
                estimated_cost_usd=round(max(0.0, switch_cost_estimate), 4),
                detail="Switching models within a session rebuilds the prompt cache.",
            )
        )
    return breakers


def _cross_project_rank(
    baseline: Optional[Baseline],
    *,
    project_hash: str,
    project_savings_pct: float,
) -> Optional[tuple]:
    """Return (rank, total_projects) or None when there is no peer to compare against.

    Rank is 1-indexed; rank 1 = highest savings_pct using the latest week
    available in each project's history. Projects with no history are excluded
    from the denominator -- they aren't comparable yet.
    """
    if baseline is None or len(baseline.projects) < 2:
        return None

    def latest_pct(entry: ProjectEntry) -> Optional[float]:
        if not entry.weekly_savings_history:
            return None
        return entry.weekly_savings_history[-1].savings_pct

    scored = []
    for h, entry in baseline.projects.items():
        pct = project_savings_pct if h == project_hash else latest_pct(entry)
        if pct is None:
            continue
        scored.append((h, pct))

    if len(scored) < 2 or project_hash not in {h for h, _ in scored}:
        return None

    scored.sort(key=lambda kv: kv[1], reverse=True)
    rank = next(i for i, (h, _) in enumerate(scored, start=1) if h == project_hash)
    return (rank, len(scored))


def compute_savings_report(
    summaries: Iterable[SessionSummary],
    *,
    project_hash: str,
    project_name: str,
    baseline: Optional[Baseline] = None,
    now: Optional[datetime] = None,
    window_days: int = 30,
    weeks: int = 4,
) -> SavingsReport:
    """Produce the report rendered by `cc-rig savings`.

    Args:
        summaries: iterable of SessionSummary, typically from parse_sessions.
        project_hash: stable hash of the current project (see paths.project_path_hash).
        project_name: human-readable project name for display.
        baseline: optional Baseline document; enables cross-project rank.
        now: optional clock override (UTC). Defaults to datetime.now(UTC).
        window_days: how far back to aggregate. Default 30.
        weeks: how many trailing weekly rollups to include. Default 4.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    all_summaries = list(summaries)
    windowed = _summaries_in_window(all_summaries, now=now, window_days=window_days)

    cost = sum(s.cost_usd for s in windowed)
    uncached = sum(s.cost_uncached_usd for s in windowed)
    input_tokens = sum(s.input_tokens for s in windowed)
    cache_read = sum(s.cache_read_tokens for s in windowed)
    cache_create = sum(s.cache_create_tokens for s in windowed)
    cache_create_1h = sum(s.cache_create_1h_tokens for s in windowed)
    output_tokens = sum(s.output_tokens for s in windowed)
    cache_total = cache_read + cache_create
    cache_read_ratio = cache_read / cache_total if cache_total else 0.0
    savings_pct = 100.0 * (1.0 - cost / uncached) if uncached > 0 else 0.0

    trend = _weekly_trend(all_summaries, now=now, weeks=weeks)
    breakers = _cache_breakers(windowed)
    rank = _cross_project_rank(baseline, project_hash=project_hash, project_savings_pct=savings_pct)

    families = [s.primary_family for s in windowed if s.primary_family]
    primary_family = max(set(families), key=families.count) if families else ""
    models = [s.primary_model for s in windowed if s.primary_model]
    primary_model = max(set(models), key=models.count) if models else ""

    return SavingsReport(
        project_hash=project_hash,
        project_name=project_name,
        window_days=window_days,
        session_count=len(windowed),
        input_tokens=input_tokens,
        cache_read_tokens=cache_read,
        cache_create_tokens=cache_create,
        cache_create_1h_tokens=cache_create_1h,
        output_tokens=output_tokens,
        cost_usd=round(cost, 4),
        cost_uncached_usd=round(uncached, 4),
        savings_pct=round(savings_pct, 2),
        cache_read_ratio=round(cache_read_ratio, 4),
        weekly_trend=trend,
        cache_breakers=breakers,
        cross_project_rank=rank,
        primary_family=primary_family,
        primary_model=primary_model,
    )


def update_baseline_with_report(
    baseline: Baseline,
    *,
    project_hash: str,
    project_name: str,
    tier: str,
    report: SavingsReport,
    now: Optional[datetime] = None,
) -> Baseline:
    """Fold a fresh report into the baseline document.

    For each week in report.weekly_trend with a non-zero session_count, we
    upsert that WeeklyRollup into the project's history. Sessions older than
    the trend window are preserved untouched, so history accumulates over
    repeated invocations.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    last_seen = now.isoformat()
    entry = baseline.projects.get(project_hash)
    if entry is None:
        entry = ProjectEntry(
            name=project_name,
            first_seen=last_seen,
            last_seen=last_seen,
            tier=tier,
            weekly_savings_history=[],
        )
    else:
        entry.name = project_name
        entry.tier = tier
        entry.last_seen = last_seen

    by_week = {w.week_start: w for w in entry.weekly_savings_history}
    for w in report.weekly_trend:
        if w.session_count > 0:
            by_week[w.week_start] = w
    entry.weekly_savings_history = sorted(by_week.values(), key=lambda w: w.week_start)

    baseline.projects[project_hash] = entry
    return baseline


__all__ = [
    "CacheBreaker",
    "SavingsReport",
    "compute_savings_report",
    "iso_week_start",
    "parse_iso_timestamp",
    "update_baseline_with_report",
]
