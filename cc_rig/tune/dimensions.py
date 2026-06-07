"""The six scored dimensions for `cc-rig tune`.

Each dimension is a pure function `(TuneContext) -> DimensionScore`. Scores
start at 100 and lose points for concrete, observed gaps; every deduction
produces a ranked Opportunity. Cache findings carry a dollar estimate derived
from real session history (see `_every_session_break_cost`); structural
findings carry a severity instead. Cache hygiene is the flagship (30%).
"""

from __future__ import annotations

import re
from typing import Optional

from cc_rig.baseline.jsonl import DEFAULT_FAMILY, PRICING_PER_MILLION
from cc_rig.tune.score import DimensionScore, Opportunity, TuneContext

# A bare ISO date or a "last updated / as of" marker in the static prefix
# rebuilds the prompt cache every session.
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_TS_MARKER_RE = re.compile(r"(?i)\b(last updated|updated:|as of|timestamp)\b")


def _clamp(score: float) -> int:
    return max(0, min(100, round(score)))


# ── Hook-scanning helpers (settings.json hooks -> command strings) ──


def _extract_cmds(entries: object) -> list:
    out: list = []
    if not isinstance(entries, list):
        return out
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for h in entry.get("hooks") or []:
            if isinstance(h, dict) and isinstance(h.get("command"), str):
                out.append(h["command"])
    return out


def _all_hook_commands(settings: dict) -> str:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return ""
    cmds: list = []
    for entries in hooks.values():
        cmds.extend(_extract_cmds(entries))
    return "\n".join(cmds).lower()


def _hook_scripts_text(project_dir) -> str:
    """Concatenated contents of .claude/hooks/* scripts, lowercased.

    cc-rig wires tools via hook scripts (settings.json references
    `bash .claude/hooks/format.sh`; the formatter lives inside the script),
    so signal detection must look at script bodies, not just the commands.
    """
    hooks_dir = project_dir / ".claude" / "hooks"
    if not hooks_dir.is_dir():
        return ""
    parts: list = []
    for path in sorted(hooks_dir.glob("*")):
        if path.is_file():
            try:
                parts.append(path.read_text())
            except OSError:
                continue
    return "\n".join(parts).lower()


def _static_zone(claude_md: str) -> list:
    """Lines above the dynamic '## Current Context' section."""
    lines = claude_md.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("## Current Context"):
            return lines[:i]
    return lines


def _every_session_break_cost(ctx: TuneContext, prefix_tokens: int) -> Optional[float]:
    """Estimated monthly cost of a finding that breaks the cache every session.

    A break re-creates the cached prefix (5-min write, 1.25x base input)
    instead of reading it (0.1x), so the extra cost per break is
    prefix_tokens * 1.15 * base_input. Multiplied by the sessions observed in
    the savings window (~30 days). Returns None when there's no session
    history to ground the estimate, so we never fabricate a number.
    """
    sv = ctx.savings
    if sv is None or sv.session_count <= 0:
        return None
    family = sv.primary_family or DEFAULT_FAMILY
    base_in = PRICING_PER_MILLION.get(family, PRICING_PER_MILLION[DEFAULT_FAMILY])[0]
    per_break = prefix_tokens * 1.15 * base_in / 1_000_000.0
    return round(per_break * sv.session_count, 2)


# ── Dimensions ─────────────────────────────────────────────────────


def cache_hygiene(ctx: TuneContext) -> DimensionScore:
    """Flagship (30%): is the cached prefix stable, and are reads landing?"""
    opps: list = []
    score = 100.0
    cm = ctx.claude_md
    prefix_tokens = max(1, len(cm) // 4)
    static = _static_zone(cm)

    # 1. Date / timestamp in the static (cached) zone -> breaks every session.
    bad_line = 0
    for i, line in enumerate(static, start=1):
        if _DATE_RE.search(line) or _TS_MARKER_RE.search(line):
            bad_line = i
            break
    if bad_line:
        score -= 25
        opps.append(
            Opportunity(
                title="Remove the date/timestamp from CLAUDE.md's static section",
                dimension="cache_hygiene",
                detail=(
                    f"Line {bad_line} changes the cached prefix, re-creating it every "
                    "session. Move it below '## Current Context' or into CLAUDE.local.md."
                ),
                severity="high",
                est_monthly_usd=_every_session_break_cost(ctx, prefix_tokens),
                fixable=True,
                fix_id="cache.move_date",
            )
        )

    # 2. Agent docs inlined instead of @import.
    if cm and "@agent_docs" not in cm and ("## Agent Docs" in cm or "agent_docs" in cm):
        score -= 10
        opps.append(
            Opportunity(
                title="Reference agent docs via @import",
                dimension="cache_hygiene",
                detail=(
                    "Inlined agent docs bloat the prefix; @agent_docs/... loads them efficiently."
                ),
                severity="med",
                fixable=False,
            )
        )

    # 3. Realized cache-read ratio from session history.
    sv = ctx.savings
    if sv is not None and sv.session_count > 0:
        ratio = sv.cache_read_ratio
        if ratio < 0.40:
            score -= 30
        elif ratio < 0.70:
            score -= 12
        for breaker in sv.cache_breakers:
            est = breaker.estimated_cost_usd or None
            opps.append(
                Opportunity(
                    title=f"Reduce: {breaker.name}",
                    dimension="cache_hygiene",
                    detail=breaker.detail,
                    severity="med",
                    est_monthly_usd=est,
                    fixable=False,
                )
            )

    return DimensionScore("cache_hygiene", "Cache hygiene", 0.30, _clamp(score), opps)


def safety_guards(ctx: TuneContext) -> DimensionScore:
    """20%: destructive-command, push-to-main, and secrets protection."""
    opps: list = []
    score = 100.0
    cm = ctx.claude_md.lower()
    all_hooks = _all_hook_commands(ctx.settings)
    scripts = _hook_scripts_text(ctx.project_dir)

    has_destructive = (
        "block-rm-rf" in all_hooks or "rm -rf" in scripts or "never run destructive commands" in cm
    )
    has_block_main = "block-main" in all_hooks or "never push directly to main" in cm
    has_secrets = (
        "block-env" in all_hooks
        or "never read, output, or log api keys" in cm
        or "credentials, or secrets" in cm
    )

    if not has_destructive:
        score -= 40
        opps.append(
            Opportunity(
                title="Add destructive-command protection",
                dimension="safety_guards",
                detail="Block rm -rf, DROP TABLE, etc. via a PreToolUse hook or a guardrail.",
                severity="high",
                fixable=True,
                fix_id="safety.add_destructive_guardrail",
            )
        )
    if not has_block_main:
        score -= 20
        opps.append(
            Opportunity(
                title="Add a block-push-to-main protection",
                dimension="safety_guards",
                detail="Prevent accidental direct pushes to the default branch.",
                severity="med",
                fixable=True,
                fix_id="safety.add_block_main_guardrail",
            )
        )
    if not has_secrets:
        score -= 20
        opps.append(
            Opportunity(
                title="Add a secrets guardrail",
                dimension="safety_guards",
                detail="Tell Claude never to read, output, or log API keys, tokens, or secrets.",
                severity="med",
                fixable=True,
                fix_id="safety.add_secrets_guardrail",
            )
        )

    return DimensionScore("safety_guards", "Safety guards", 0.20, _clamp(score), opps)


def context_discipline(ctx: TuneContext) -> DimensionScore:
    """15%: keep CLAUDE.md and memory lean so the agent stays focused."""
    opps: list = []
    score = 100.0
    tokens = len(ctx.claude_md) // 4 if ctx.claude_md else 0

    if tokens > 2500:
        score -= 30
        opps.append(
            Opportunity(
                title="Trim CLAUDE.md",
                dimension="context_discipline",
                detail=(
                    f"CLAUDE.md is ~{tokens} tokens. Lean files (tooling + critical patterns "
                    "only) improve task focus; move detail into agent docs."
                ),
                severity="high",
                fixable=False,
            )
        )
    elif tokens > 1800:
        score -= 12
        opps.append(
            Opportunity(
                title="Consider trimming CLAUDE.md",
                dimension="context_discipline",
                detail=(
                    f"CLAUDE.md is ~{tokens} tokens; aim for tooling and critical patterns only."
                ),
                severity="low",
                fixable=False,
            )
        )

    # Oversized single memory file (team memory is checked into the repo).
    mem_dir = ctx.project_dir / "memory"
    if mem_dir.is_dir():
        for path in sorted(mem_dir.glob("*.md")):
            try:
                n = path.read_text().count("\n") + 1
            except OSError:
                continue
            if n > 400:
                score -= 10
                opps.append(
                    Opportunity(
                        title=f"Split oversized memory file ({path.name})",
                        dimension="context_discipline",
                        detail=(
                            f"{path.name} is {n} lines; large memory files are "
                            "slow to load on demand."
                        ),
                        severity="low",
                        fixable=False,
                    )
                )
                break

    return DimensionScore("context_discipline", "Context discipline", 0.15, _clamp(score), opps)


def workflow_fit(ctx: TuneContext) -> DimensionScore:
    """15%: do the generated hooks and commands match this stack?"""
    opps: list = []
    score = 100.0
    cm = ctx.claude_md
    all_hooks = _all_hook_commands(ctx.settings)

    if "## Commands" not in cm:
        score -= 30
        opps.append(
            Opportunity(
                title="Add a Commands section to CLAUDE.md",
                dimension="workflow_fit",
                detail="List build/test/lint commands so Claude uses the right tooling.",
                severity="med",
                fixable=True,
                fix_id="workflow.add_commands",
            )
        )

    cfg = ctx.config
    if cfg is not None:
        fmt = (getattr(cfg, "format_cmd", "") or "").strip()
        if fmt:
            tool = fmt.split()[0].lower()
            scripts = _hook_scripts_text(ctx.project_dir)
            if tool not in all_hooks and tool not in scripts:
                score -= 20
                opps.append(
                    Opportunity(
                        title="Wire your formatter into a hook",
                        dimension="workflow_fit",
                        detail=f"`{fmt}` is your format command but no hook runs it automatically.",
                        severity="med",
                        fixable=False,
                    )
                )

    return DimensionScore("workflow_fit", "Workflow fit", 0.15, _clamp(score), opps)


def verification(ctx: TuneContext) -> DimensionScore:
    """10%: is there a test/lint gate before code lands?"""
    opps: list = []
    score = 100.0
    cm = ctx.claude_md.lower()
    all_hooks = _all_hook_commands(ctx.settings)

    gate_in_guardrail = "run tests before committing" in cm or "lint must pass" in cm
    gate_in_hook = "verify" in all_hooks or "test" in all_hooks or "lint" in all_hooks
    if not (gate_in_guardrail or gate_in_hook):
        score -= 50
        opps.append(
            Opportunity(
                title="Add a verification gate",
                dimension="verification",
                detail="Require tests/lint to pass before committing (guardrail or commit hook).",
                severity="high",
                fixable=True,
                fix_id="verification.add_gate",
            )
        )

    return DimensionScore("verification", "Verification", 0.10, _clamp(score), opps)


def currency(ctx: TuneContext) -> DimensionScore:
    """10%: is the config aligned to the pinned Claude Code version?"""
    opps: list = []
    score = 100.0

    # Settings keys valid for the pinned CC schema (single source of truth).
    from cc_rig.doctor import _VALID_SETTINGS_KEYS_V2_1_150

    unknown = sorted(k for k in ctx.settings if k not in _VALID_SETTINGS_KEYS_V2_1_150)
    if unknown:
        score -= 25
        opps.append(
            Opportunity(
                title="Resolve unknown settings.json keys",
                dimension="currency",
                detail=(
                    "Keys not in the pinned CC schema: "
                    + ", ".join(unknown[:5])
                    + (" ..." if len(unknown) > 5 else "")
                    + ". Typos, deprecated, or newer than cc-rig's alignment."
                ),
                severity="med",
                fixable=False,
            )
        )

    # Pinned CC version line present (drift signal).
    if ctx.claude_md and "claude code" not in ctx.claude_md.lower():
        score -= 15
        opps.append(
            Opportunity(
                title="Pin the Claude Code version in CLAUDE.md",
                dimension="currency",
                detail="A pinned version line makes drift visible after a CC upgrade.",
                severity="low",
                fixable=True,
                fix_id="currency.pin_version",
            )
        )

    return DimensionScore("currency", "Currency", 0.10, _clamp(score), opps)


# Ordered by weight (flagship first) for stable display.
ALL_DIMENSIONS = [
    cache_hygiene,
    safety_guards,
    context_discipline,
    workflow_fit,
    verification,
    currency,
]


__all__ = ["ALL_DIMENSIONS"]
