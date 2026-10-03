"""cc-rig tune: scored, dollar-quantified configuration report.

`cc-rig tune` grades a project's Claude Code configuration across weighted
dimensions (cache hygiene flagship), attributes a dollar cost to the cache
findings using real session history, and ranks fixes by impact. Phase 1 is
read-only; `--fix` and the CI gate arrive in later phases.
"""

from __future__ import annotations

from cc_rig.tune.score import (
    DimensionScore,
    Opportunity,
    TuneContext,
    TuneReport,
    compute_tune_report,
    grade_for,
)

__all__ = [
    "DimensionScore",
    "Opportunity",
    "TuneContext",
    "TuneReport",
    "compute_tune_report",
    "grade_for",
]
