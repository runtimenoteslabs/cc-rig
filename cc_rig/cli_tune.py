"""`cc-rig tune` subcommand: scored, dollar-quantified config report.

Gathers the project's on-disk Claude Code config (CLAUDE.md, settings.json,
hooks, memory), pulls realized cache economics from session JSONL via the
baseline engine, scores six weighted dimensions, and renders a graded report
with fixes ranked by impact. `--fix` applies safe auto-fixes (backed up via
FileTracker) then re-scores; `--fix-unsafe` also relocates content; `--ci`
gates on a threshold; `--badge` emits a Shields.io endpoint.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional

from cc_rig.tune.score import TuneContext, TuneReport, compute_tune_report


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the `cc-rig tune` flags on an existing parser."""
    parser.add_argument(
        "-d",
        "--dir",
        default=".",
        help="Project directory (default: current)",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit the report as JSON instead of a rendered view",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Session window for cache economics (default: 30)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply safe auto-fixes, then re-score (backs up CLAUDE.md)",
    )
    parser.add_argument(
        "--fix-unsafe",
        dest="fix_unsafe",
        action="store_true",
        help="Also apply fixes that relocate content (implies --fix)",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Exit non-zero when the score is below --min-score (for CI gates)",
    )
    parser.add_argument(
        "--min-score",
        dest="min_score",
        type=int,
        default=60,
        help="Threshold for --ci (default: 60)",
    )
    parser.add_argument(
        "--badge",
        action="store_true",
        help="Emit a Shields.io endpoint JSON for the score and exit",
    )
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,  # test-only override
    )
    parser.add_argument(
        "--cache-path",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,  # test-only override
    )


def load_context(
    project_dir: Path,
    *,
    window_days: int = 30,
    projects_dir: Optional[Path] = None,
    cache_path: Optional[Path] = None,
) -> TuneContext:
    """Gather everything the scorer needs from disk + session history.

    Degrades gracefully: missing CLAUDE.md, settings, manifest, or session
    history each just leave that part of the context empty/None.
    """
    claude_md = ""
    cm_path = project_dir / "CLAUDE.md"
    if cm_path.exists():
        try:
            claude_md = cm_path.read_text()
        except OSError:
            claude_md = ""

    settings: dict = {}
    settings_path = project_dir / ".claude" / "settings.json"
    if settings_path.exists():
        try:
            loaded = json.loads(settings_path.read_text())
            settings = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            settings = {}

    config = None
    config_path = project_dir / ".cc-rig.json"
    if config_path.exists():
        try:
            from cc_rig.config.project import ProjectConfig

            config = ProjectConfig.from_dict(json.loads(config_path.read_text()))
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            config = None

    savings = None
    sessions_seen = 0
    try:
        from cc_rig.baseline.jsonl import discover_session_files, parse_sessions
        from cc_rig.baseline.paths import (
            PARSE_CACHE_PATH,
            claude_projects_dir,
            project_path_hash,
        )
        from cc_rig.baseline.savings import compute_savings_report

        pdir = Path(projects_dir).resolve() if projects_dir else claude_projects_dir(project_dir)
        cpath = Path(cache_path) if cache_path else PARSE_CACHE_PATH
        session_files = discover_session_files(pdir)
        sessions_seen = len(session_files)
        if session_files:
            summaries = parse_sessions(session_files, cache_path=cpath)
            savings = compute_savings_report(
                summaries,
                project_hash=project_path_hash(project_dir),
                project_name=project_dir.name or "project",
                baseline=None,
                window_days=window_days,
            )
    except OSError:
        savings = None

    return TuneContext(
        project_dir=project_dir,
        claude_md=claude_md,
        settings=settings,
        config=config,
        savings=savings,
        sessions_seen=sessions_seen,
    )


def run(args: argparse.Namespace) -> int:
    """Entrypoint dispatched from cc_rig.cli.main."""
    project_dir = Path(getattr(args, "dir", ".") or ".").resolve()
    ctx_kwargs = dict(
        window_days=getattr(args, "window_days", 30),
        projects_dir=getattr(args, "projects_dir", None),
        cache_path=getattr(args, "cache_path", None),
    )
    ctx = load_context(project_dir, **ctx_kwargs)
    report = compute_tune_report(ctx)
    as_json = getattr(args, "as_json", False)

    # --badge: emit a Shields.io endpoint and stop.
    if getattr(args, "badge", False):
        print(json.dumps(_badge_payload(report)))
        return 0

    do_fix = getattr(args, "fix", False) or getattr(args, "fix_unsafe", False)
    if do_fix:
        from cc_rig.generators.fileops import FileTracker
        from cc_rig.tune.fixers import apply_fixes

        before_cm = ctx.claude_md
        before_overall = report.overall
        tracker = FileTracker(project_dir)
        results = apply_fixes(
            report, ctx, tracker, include_unsafe=getattr(args, "fix_unsafe", False)
        )
        # Re-load from disk and re-score so the report reflects the fixes.
        ctx = load_context(project_dir, **ctx_kwargs)
        report = compute_tune_report(ctx)

        if as_json:
            print(
                json.dumps(
                    {
                        "fixes": [r.__dict__ for r in results],
                        "before_overall": before_overall,
                        "report": report.to_dict(),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            from rich.console import Console

            console = Console(no_color=bool(os.environ.get("NO_COLOR")))
            _render_fix_summary(console, results, before_cm, ctx.claude_md, before_overall, report)
    elif as_json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        from rich.console import Console

        console = Console(no_color=bool(os.environ.get("NO_COLOR")))
        render_report(console, report)

    if getattr(args, "ci", False):
        return 0 if report.overall >= getattr(args, "min_score", 60) else 1
    return 0


def _badge_payload(report) -> dict:
    overall = report.overall
    color = (
        "brightgreen"
        if overall >= 80
        else "yellow"
        if overall >= 60
        else "orange"
        if overall >= 35
        else "red"
    )
    return {
        "schemaVersion": 1,
        "label": "cc-rig tune",
        "message": f"{overall}/100",
        "color": color,
    }


# ── Rendering ──────────────────────────────────────────────────────

_GRADE_STYLE = {
    "Production Ready": "bold green",
    "Getting There": "bold yellow",
    "Needs Work": "bold dark_orange",
    "Critical": "bold red",
}
_SEVERITY_STYLE = {"high": "red", "med": "yellow", "low": "dim"}


def _bar(score: int) -> str:
    filled = max(0, min(10, round(score / 10)))
    return "█" * filled + "·" * (10 - filled)


def _fmt_usd(v: float) -> str:
    return f"${v:,.2f}"


def render_report(console, report: TuneReport) -> None:
    """Render a TuneReport as a graded, ranked terminal view."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    grade_style = _GRADE_STYLE.get(report.grade, "bold")

    # ── Hero panel: score + grade + cache context ──
    hero = Text()
    hero.append(f"{report.overall}", style=grade_style)
    hero.append(" / 100   ", style="bold")
    hero.append(report.grade, style=grade_style)
    sub = Text()
    if report.cache_read_ratio is not None:
        sub.append(f"cache reads {report.cache_read_ratio:.0%}", style="cyan")
        sub.append("   ·   ")
    sub.append(f"{report.sessions_seen} sessions seen", style="dim")
    if report.percentile is not None:
        sub.append(f"   ·   better than {report.percentile}% of setups", style="dim")
    body = Text()
    body.append_text(hero)
    body.append("\n")
    body.append_text(sub)
    console.print(Panel(body, title=f"cc-rig tune · {report.project_name}", expand=False))

    # ── Dimensions table ──
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Dimension")
    table.add_column("Weight", justify="right")
    table.add_column("", no_wrap=True)
    table.add_column("Score", justify="right")
    for dim in report.dimensions:
        score_style = "green" if dim.score >= 80 else "yellow" if dim.score >= 50 else "red"
        table.add_row(
            dim.label,
            f"{dim.weight:.0%}",
            Text(_bar(dim.score), style=score_style),
            Text(str(dim.score), style=score_style),
        )
    console.print(table)
    console.print()

    # ── Ranked opportunities ──
    if not report.opportunities:
        console.print(Text("No opportunities — your config is clean.", style="green"))
        return

    from cc_rig.tune.fixers import FIXERS, safe_fixable

    console.print(Text("Top opportunities (ranked by impact)", style="bold"))
    for i, opp in enumerate(report.opportunities, start=1):
        line = Text(f"  {i}. ")
        line.append(opp.title, style="bold")
        if opp.est_monthly_usd is not None:
            line.append(f"   ~{_fmt_usd(opp.est_monthly_usd)}/mo", style="bold cyan")
        else:
            line.append(f"   [{opp.severity}]", style=_SEVERITY_STYLE.get(opp.severity, "dim"))
        fixer = FIXERS.get(opp.fix_id) if opp.fix_id else None
        if fixer is not None:
            if fixer.safe:
                line.append("  [safe fix]", style="dim green")
            else:
                line.append("  [--fix-unsafe]", style="dim yellow")
        console.print(line)
        if opp.detail:
            console.print(Text(f"     {opp.detail}", style="dim"))

    safe_n = len(safe_fixable(report))
    if safe_n:
        console.print()
        console.print(Text(f"Run `cc-rig tune --fix` to apply {safe_n} safe fix(es).", style="dim"))


def _render_fix_summary(console, results, before_cm, after_cm, before_overall, report) -> None:
    """Show what --fix applied, a CLAUDE.md diff, and the score delta."""
    import difflib

    from rich.text import Text

    applied = [r for r in results if r.applied]
    if not applied:
        console.print(Text("No fixes applied — nothing safe to change.", style="yellow"))
    else:
        console.print(Text(f"Applied {len(applied)} fix(es):", style="bold"))
        for r in applied:
            tag = "safe" if r.safe else "unsafe"
            console.print(Text(f"  ✓ {r.title} ({tag})", style="green"))

        diff = list(
            difflib.unified_diff(
                before_cm.splitlines(),
                after_cm.splitlines(),
                fromfile="CLAUDE.md (before)",
                tofile="CLAUDE.md (after)",
                lineterm="",
            )
        )
        if diff:
            console.print()
            for dl in diff:
                if dl.startswith("+") and not dl.startswith("+++"):
                    console.print(Text(dl, style="green"))
                elif dl.startswith("-") and not dl.startswith("---"):
                    console.print(Text(dl, style="red"))
                elif dl.startswith("@@"):
                    console.print(Text(dl, style="cyan"))
                else:
                    console.print(Text(dl, style="dim"))

    console.print()
    delta = report.overall - before_overall
    arrow = "→"
    sign = f"+{delta}" if delta > 0 else str(delta)
    console.print(
        Text(
            f"Score: {before_overall} {arrow} {report.overall} / 100  ({sign})   {report.grade}",
            style="bold",
        )
    )
    console.print(
        Text("Backup saved to .cc-rig-backup/. Re-run cc-rig tune to verify.", style="dim")
    )


__all__ = ["add_arguments", "load_context", "run", "render_report"]
