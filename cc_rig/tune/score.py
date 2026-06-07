"""Scoring model for `cc-rig tune`.

Pure data + aggregation: dimensions are scored by functions in
`cc_rig.tune.dimensions` against a `TuneContext` (on-disk artifacts plus an
optional savings report). This module owns the dataclasses, the grade bands,
the opportunity ranking, and the weighted composite. Keeping it free of I/O
makes every dimension trivially unit-testable from a hand-built context.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:  # avoid import cost / cycles at runtime
    from cc_rig.baseline.savings import SavingsReport
    from cc_rig.config.project import ProjectConfig


# ── Grade bands (cc-health-check style; calibrated thresholds come later) ──

_GRADE_BANDS = (
    (80, "Production Ready"),
    (60, "Getting There"),
    (35, "Needs Work"),
    (0, "Critical"),
)


def grade_for(score: int) -> str:
    """Map a 0-100 composite score to a human grade band."""
    for floor, label in _GRADE_BANDS:
        if score >= floor:
            return label
    return "Critical"


# ── Findings + dimensions ──────────────────────────────────────────

_SEVERITY_RANK = {"high": 0, "med": 1, "low": 2}


@dataclass
class Opportunity:
    """One ranked, actionable finding.

    `est_monthly_usd` is set only when we can honestly quantify the dollar
    impact from real session history (cache findings); structural findings
    carry a `severity` instead. `fixable` flags whether a later `--fix` pass
    can apply it automatically.
    """

    title: str
    dimension: str
    detail: str = ""
    severity: str = "med"  # high | med | low
    est_monthly_usd: Optional[float] = None
    fixable: bool = False
    fix_id: Optional[str] = None  # key into cc_rig.tune.fixers.FIXERS, when auto-fixable

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DimensionScore:
    """A single weighted dimension's 0-100 sub-score and its findings."""

    key: str
    label: str
    weight: float
    score: int
    opportunities: list = field(default_factory=list)  # list[Opportunity]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["opportunities"] = [o.to_dict() for o in self.opportunities]
        return d


@dataclass
class TuneContext:
    """Everything a dimension needs to score, gathered once.

    Built by the CLI layer (`cli_tune.load_context`) so the scoring code
    stays pure and testable. `config`/`savings` are optional: tune degrades
    gracefully on a project without a manifest or without session history.
    """

    project_dir: Path
    claude_md: str = ""
    settings: dict = field(default_factory=dict)
    config: Optional["ProjectConfig"] = None
    savings: Optional["SavingsReport"] = None
    sessions_seen: int = 0


@dataclass
class TuneReport:
    """The shape `cc-rig tune` renders. JSON-serializable via to_dict."""

    project_name: str
    overall: int
    grade: str
    dimensions: list = field(default_factory=list)  # list[DimensionScore]
    opportunities: list = field(default_factory=list)  # list[Opportunity], ranked
    cache_read_ratio: Optional[float] = None
    sessions_seen: int = 0
    percentile: Optional[int] = None  # "better than N% of setups"; None until corpus exists

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "overall": self.overall,
            "grade": self.grade,
            "cache_read_ratio": self.cache_read_ratio,
            "sessions_seen": self.sessions_seen,
            "percentile": self.percentile,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "opportunities": [o.to_dict() for o in self.opportunities],
        }


def rank_opportunities(opportunities: list) -> list:
    """Rank findings: dollar-quantified first (largest savings), then by
    severity, then alphabetically for stable output."""

    def key(o: Opportunity):
        has_dollar = o.est_monthly_usd is not None
        dollar = -(o.est_monthly_usd or 0.0)
        return (0 if has_dollar else 1, dollar, _SEVERITY_RANK.get(o.severity, 1), o.title)

    return sorted(opportunities, key=key)


def compute_tune_report(
    ctx: TuneContext,
    dimensions: Optional[list] = None,
) -> TuneReport:
    """Score every dimension against `ctx` and assemble the composite report.

    Args:
        ctx: gathered project context.
        dimensions: optional list of dimension scorer callables (defaults to
            `cc_rig.tune.dimensions.ALL_DIMENSIONS`); injectable for tests.
    """
    if dimensions is None:
        from cc_rig.tune.dimensions import ALL_DIMENSIONS

        dimensions = ALL_DIMENSIONS

    dim_scores: list = [fn(ctx) for fn in dimensions]
    total_weight = sum(d.weight for d in dim_scores) or 1.0
    overall = round(sum(d.score * d.weight for d in dim_scores) / total_weight)

    all_opps = rank_opportunities([o for d in dim_scores for o in d.opportunities])

    return TuneReport(
        project_name=ctx.project_dir.name or "project",
        overall=overall,
        grade=grade_for(overall),
        dimensions=dim_scores,
        opportunities=all_opps,
        cache_read_ratio=(ctx.savings.cache_read_ratio if ctx.savings else None),
        sessions_seen=ctx.sessions_seen,
    )


# Type alias for a dimension scorer: takes a context, returns a DimensionScore.
DimensionFn = Callable[[TuneContext], DimensionScore]


__all__ = [
    "DimensionFn",
    "DimensionScore",
    "Opportunity",
    "TuneContext",
    "TuneReport",
    "compute_tune_report",
    "grade_for",
    "rank_opportunities",
]
