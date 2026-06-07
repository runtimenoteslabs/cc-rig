"""Auto-fixers for `cc-rig tune --fix`.

Each fixer is a pure text transform on CLAUDE.md: `(text, ctx) -> new_text`
(or None when there's nothing to change). They are registered with a safety
flag: SAFE fixers are additive and meaning-preserving (add a missing guardrail,
pin the version); UNSAFE fixers relocate user-authored content and are gated
behind `--fix-unsafe`. All writes go through FileTracker, which backs up the
original to .cc-rig-backup/ so a fix is always reversible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from cc_rig.tune.dimensions import _DATE_RE, _TS_MARKER_RE
from cc_rig.tune.score import TuneContext

# A text fixer: (claude_md, ctx) -> new text, or None if no change applies.
TextFix = Callable[[str, TuneContext], Optional[str]]


@dataclass
class Fixer:
    fix_id: str
    safe: bool
    title: str
    apply: TextFix


@dataclass
class FixResult:
    fix_id: str
    title: str
    applied: bool
    safe: bool


# ── Text helpers ───────────────────────────────────────────────────


def _join(original: str, lines: list) -> str:
    out = "\n".join(lines)
    if original.endswith("\n"):
        out += "\n"
    return out


def _find(lines: list, predicate: Callable[[str], bool]) -> Optional[int]:
    for i, line in enumerate(lines):
        if predicate(line):
            return i
    return None


def _add_bullet_to_section(cm: str, header: str, bullet: str) -> str:
    """Insert *bullet* as the last bullet of *header*'s section, creating the
    section before '## Current Context' (or at EOF) if it does not exist."""
    lines = cm.splitlines()
    start = _find(lines, lambda line: line.strip() == header)

    if start is None:
        ctx_i = _find(lines, lambda line: line.strip().startswith("## Current Context"))
        if ctx_i is not None:
            lines[ctx_i:ctx_i] = [header, "", bullet, ""]
        else:
            if lines and lines[-1].strip() != "":
                lines.append("")
            lines += [header, "", bullet]
        return _join(cm, lines)

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break

    insert_at = None
    for j in range(start + 1, end):
        if lines[j].startswith("- "):
            insert_at = j + 1
    if insert_at is None:
        insert_at = start + 1
        if insert_at < end and lines[insert_at].strip() == "":
            insert_at += 1

    lines.insert(insert_at, bullet)
    return _join(cm, lines)


# ── Safe fixers (additive, meaning-preserving) ─────────────────────


def _fix_pin_version(cm: str, ctx: TuneContext) -> Optional[str]:
    if "claude code" in cm.lower():
        return None
    from cc_rig.config.cc_version import PINNED_CC_VERSION_STR

    bullet = f"- **Claude Code**: v{PINNED_CC_VERSION_STR} (cc-rig pinned)"
    lines = cm.splitlines()
    last_identity = None
    for i, line in enumerate(lines[:20]):
        if line.startswith("- **"):
            last_identity = i
    if last_identity is not None:
        lines.insert(last_identity + 1, bullet)
    else:
        insert_at = next((i + 1 for i, line in enumerate(lines) if line.startswith("# ")), 0)
        # keep a blank line between the heading and the inserted bullet
        if insert_at < len(lines) and lines[insert_at].strip() == "":
            insert_at += 1
        lines.insert(insert_at, bullet)
    return _join(cm, lines)


def _fix_add_secrets(cm: str, ctx: TuneContext) -> Optional[str]:
    low = cm.lower()
    if "never read, output, or log api keys" in low or "credentials, or secrets" in low:
        return None
    return _add_bullet_to_section(
        cm,
        "## Guardrails",
        "- Never read, output, or log API keys, private keys, tokens, or seed phrases.",
    )


def _fix_add_destructive(cm: str, ctx: TuneContext) -> Optional[str]:
    if "never run destructive commands" in cm.lower():
        return None
    return _add_bullet_to_section(
        cm, "## Guardrails", "- Never run destructive commands (rm -rf /, DROP TABLE)."
    )


def _fix_add_block_main(cm: str, ctx: TuneContext) -> Optional[str]:
    if "never push directly to main" in cm.lower():
        return None
    return _add_bullet_to_section(cm, "## Guardrails", "- Never push directly to main/master.")


def _fix_add_verification(cm: str, ctx: TuneContext) -> Optional[str]:
    if "run tests before committing" in cm.lower():
        return None
    return _add_bullet_to_section(
        cm, "## Guardrails", "- Run tests before committing. Run lint before pushing."
    )


def _fix_add_commands(cm: str, ctx: TuneContext) -> Optional[str]:
    if "## Commands" in cm or ctx.config is None:
        return None
    from cc_rig.generators.claude_md import _section_commands

    section = _section_commands(ctx.config).rstrip("\n")
    if not section.strip() or "- " not in section:
        return None  # nothing useful to add (e.g. generic template, no commands)

    lines = cm.splitlines()
    anchor = _find(lines, lambda line: line.strip().startswith("## Guardrails"))
    if anchor is None:
        anchor = _find(lines, lambda line: line.strip().startswith("## Current Context"))
    block = section.splitlines() + [""]
    if anchor is not None:
        lines[anchor:anchor] = block
    else:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines += section.splitlines()
    return _join(cm, lines)


# ── Unsafe fixers (relocate user-authored content; opt-in) ─────────


def _fix_move_date(cm: str, ctx: TuneContext) -> Optional[str]:
    lines = cm.splitlines()
    boundary = next(
        (i for i, line in enumerate(lines) if line.strip().startswith("## Current Context")),
        len(lines),
    )
    target = None
    for i in range(boundary):
        if _DATE_RE.search(lines[i]) or _TS_MARKER_RE.search(lines[i]):
            target = i
            break
    if target is None:
        return None

    moved = lines.pop(target).strip()
    cc_i = next(
        (i for i, line in enumerate(lines) if line.strip().startswith("## Current Context")),
        None,
    )
    relocated = moved if moved.startswith("-") else f"- {moved}"
    if cc_i is not None:
        lines.insert(cc_i + 1, relocated)
    else:
        lines.append(relocated)
    return _join(cm, lines)


# ── Registry + driver ──────────────────────────────────────────────

FIXERS: dict = {
    "currency.pin_version": Fixer(
        "currency.pin_version", True, "Pin Claude Code version", _fix_pin_version
    ),
    "safety.add_secrets_guardrail": Fixer(
        "safety.add_secrets_guardrail", True, "Add secrets guardrail", _fix_add_secrets
    ),
    "safety.add_destructive_guardrail": Fixer(
        "safety.add_destructive_guardrail",
        True,
        "Add destructive-command guardrail",
        _fix_add_destructive,
    ),
    "safety.add_block_main_guardrail": Fixer(
        "safety.add_block_main_guardrail",
        True,
        "Add block-push-to-main guardrail",
        _fix_add_block_main,
    ),
    "verification.add_gate": Fixer(
        "verification.add_gate", True, "Add verification gate", _fix_add_verification
    ),
    "workflow.add_commands": Fixer(
        "workflow.add_commands", True, "Add Commands section", _fix_add_commands
    ),
    "cache.move_date": Fixer(
        "cache.move_date", False, "Move stray date out of static zone", _fix_move_date
    ),
}


def safe_fixable(report) -> list:
    """Opportunities with a registered SAFE fixer, deduped by fix_id."""
    seen: set = set()
    out: list = []
    for opp in report.opportunities:
        fid = opp.fix_id
        if fid and fid not in seen and fid in FIXERS and FIXERS[fid].safe:
            seen.add(fid)
            out.append(opp)
    return out


def apply_fixes(report, ctx: TuneContext, tracker, *, include_unsafe: bool = False) -> list:
    """Apply registered fixers for the report's opportunities.

    Fixers run in opportunity order against the evolving CLAUDE.md text; the
    result is written once via *tracker* (which backs up the original). Returns
    a list of FixResult. The caller re-loads context and re-scores afterward.
    """
    cm = ctx.claude_md
    if not cm:
        cm_path = ctx.project_dir / "CLAUDE.md"
        cm = cm_path.read_text() if cm_path.exists() else ""

    results: list = []
    seen: set = set()
    changed = False
    for opp in report.opportunities:
        fid = opp.fix_id
        if not fid or fid in seen or fid not in FIXERS:
            continue
        fixer = FIXERS[fid]
        if not fixer.safe and not include_unsafe:
            continue
        seen.add(fid)
        new = fixer.apply(cm, ctx)
        applied = new is not None and new != cm
        if applied:
            cm = new
            changed = True
        results.append(FixResult(fid, fixer.title, applied, fixer.safe))

    if changed:
        tracker.write_text("CLAUDE.md", cm, preserve_on_clean=True)
    return results


__all__ = ["FIXERS", "Fixer", "FixResult", "apply_fixes", "safe_fixable"]
