"""Streaming JSONL session parser for /cc-rig savings.

Reads Claude Code session logs from ~/.claude/projects/<encoded-cwd>/*.jsonl
and produces a per-session SessionSummary. Designed to stay under 2 seconds
for ~100 session files (50 MB total) by streaming line-by-line and caching
parsed summaries by file mtime in ~/.cc-rig/parse-cache.json.

Only fields we depend on are read: message.usage.* (token counts),
message.model (pricing family), message.content (tool_use blocks for cache
breaker detection), timestamp (session boundaries). Missing fields default
to zero rather than raising -- the JSONL schema drifts across CC versions
and we want graceful degradation, not crashes.

Pricing table is per-million dollars: (input, output, cache_create, cache_read).
Source: Anthropic public pricing as of 2026-05; bump when prices change.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from cc_rig.baseline.paths import PARSE_CACHE_PATH

PRICING_PER_MILLION = {
    # (input, output, cache_create, cache_read) in USD per million tokens.
    # cache_create uses the 5-minute write rate. Verified against
    # platform.claude.com/docs/en/about-claude/pricing.
    "opus": (5.0, 25.0, 6.25, 0.50),
    "sonnet": (3.0, 15.0, 3.75, 0.30),
    "haiku": (1.0, 5.0, 1.25, 0.10),
}
DEFAULT_FAMILY = "sonnet"

# Pricing table last verified on this date; bump when Anthropic prices change.
PRICING_VERIFIED_DATE = "2026-05-25"


def model_family(model_id: str) -> str:
    """Map a Claude model id to its pricing family.

    Examples: 'claude-opus-4-7' -> 'opus', 'claude-sonnet-4-6' -> 'sonnet',
    'claude-haiku-4-5-20251001' -> 'haiku'. Unknown ids fall back to sonnet
    (the safe middle); we log this case by leaving the family literal there.
    """
    if not model_id:
        return DEFAULT_FAMILY
    m = model_id.lower()
    if "opus" in m:
        return "opus"
    if "haiku" in m:
        return "haiku"
    if "sonnet" in m:
        return "sonnet"
    return DEFAULT_FAMILY


def compute_cost(
    input_tokens: int,
    output_tokens: int,
    cache_create_tokens: int,
    cache_read_tokens: int,
    family: str,
) -> float:
    """Estimate USD cost given token counts and a pricing family."""
    p_in, p_out, p_cc, p_cr = PRICING_PER_MILLION.get(family, PRICING_PER_MILLION[DEFAULT_FAMILY])
    total = (
        input_tokens * p_in
        + output_tokens * p_out
        + cache_create_tokens * p_cc
        + cache_read_tokens * p_cr
    )
    return total / 1_000_000.0


@dataclass
class SessionSummary:
    """Aggregated metrics for one .jsonl session file."""

    session_id: str
    file_path: str
    file_mtime: float
    started_at: str = ""
    ended_at: str = ""
    primary_family: str = DEFAULT_FAMILY
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_create_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cost_uncached_usd: float = 0.0
    claudemd_edits: int = 0
    model_switches: int = 0
    assistant_turns: int = 0
    models_seen: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SessionSummary:
        allowed = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**allowed)

    @property
    def total_input_with_cache(self) -> int:
        return self.input_tokens + self.cache_read_tokens + self.cache_create_tokens

    @property
    def cache_read_ratio(self) -> float:
        denom = self.cache_read_tokens + self.cache_create_tokens
        if denom == 0:
            return 0.0
        return self.cache_read_tokens / denom

    @property
    def savings_pct(self) -> float:
        """How much cheaper this session was than fully-uncached equivalent."""
        if self.cost_uncached_usd <= 0:
            return 0.0
        return 100.0 * (1.0 - self.cost_usd / self.cost_uncached_usd)


def _extract_usage(message: dict) -> dict:
    """Pull the usage block. Returns {} if missing/malformed."""
    usage = message.get("usage")
    return usage if isinstance(usage, dict) else {}


def _iter_tool_uses(message: dict) -> Iterable[dict]:
    """Yield each tool_use content block from an assistant message."""
    content = message.get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            yield block


def _is_claudemd_edit(tool_use: dict) -> bool:
    """True if this tool_use targets CLAUDE.md (Edit / Write / NotebookEdit)."""
    if tool_use.get("name") not in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        return False
    target = (tool_use.get("input") or {}).get("file_path", "")
    return isinstance(target, str) and target.endswith("CLAUDE.md")


def parse_session(path: Path) -> SessionSummary:
    """Parse one .jsonl session file and return its aggregate summary.

    Streams line-by-line so a 100 MB file does not blow memory. Malformed
    lines are skipped silently rather than failing the whole session.
    """
    path = Path(path)
    stat = path.stat()
    summary = SessionSummary(
        session_id=path.stem,
        file_path=str(path),
        file_mtime=stat.st_mtime,
    )

    last_family: Optional[str] = None
    cost_uncached_acc = 0.0

    with path.open("r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue

            ts = event.get("timestamp")
            if isinstance(ts, str):
                if not summary.started_at or ts < summary.started_at:
                    summary.started_at = ts
                if ts > summary.ended_at:
                    summary.ended_at = ts

            if event.get("type") != "assistant":
                continue

            message = event.get("message")
            if not isinstance(message, dict):
                continue

            model_id = message.get("model") or ""
            family = model_family(model_id)
            if model_id and model_id not in summary.models_seen:
                summary.models_seen.append(model_id)
            if last_family is not None and family != last_family:
                summary.model_switches += 1
            last_family = family

            usage = _extract_usage(message)
            t_in = int(usage.get("input_tokens") or 0)
            t_out = int(usage.get("output_tokens") or 0)
            t_cc = int(usage.get("cache_creation_input_tokens") or 0)
            t_cr = int(usage.get("cache_read_input_tokens") or 0)

            if t_in or t_out or t_cc or t_cr:
                summary.assistant_turns += 1
                summary.input_tokens += t_in
                summary.output_tokens += t_out
                summary.cache_create_tokens += t_cc
                summary.cache_read_tokens += t_cr
                summary.cost_usd += compute_cost(t_in, t_out, t_cc, t_cr, family)
                # Uncached baseline: every cache_read counts as fresh input.
                cost_uncached_acc += compute_cost(t_in + t_cr + t_cc, t_out, 0, 0, family)

            for tu in _iter_tool_uses(message):
                if _is_claudemd_edit(tu):
                    summary.claudemd_edits += 1

    summary.cost_uncached_usd = cost_uncached_acc
    summary.primary_family = last_family or DEFAULT_FAMILY
    return summary


# ---------- parse cache ---------------------------------------------------


def _load_parse_cache(path: Optional[Path] = None) -> dict:
    target = Path(path) if path is not None else PARSE_CACHE_PATH
    if not target.exists():
        return {}
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _save_parse_cache(cache: dict, path: Optional[Path] = None) -> None:
    target = Path(path) if path is not None else PARSE_CACHE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(target)


def parse_sessions(
    paths: Iterable[Path],
    cache_path: Optional[Path] = None,
    use_cache: bool = True,
) -> list:
    """Parse a batch of .jsonl files, using mtime cache to skip unchanged ones.

    Cache layout (~/.cc-rig/parse-cache.json):
        { "<abs path>": { "mtime": <float>, "summary": <SessionSummary dict> }, ... }

    A file whose on-disk mtime matches its cached mtime is reused directly.
    Files missing from the cache, or whose mtime changed, are reparsed.
    """
    cache = _load_parse_cache(cache_path) if use_cache else {}
    summaries = []
    dirty = False

    for p in paths:
        p = Path(p)
        try:
            mtime = p.stat().st_mtime
        except FileNotFoundError:
            continue
        key = str(p)
        cached = cache.get(key) if use_cache else None
        if cached and cached.get("mtime") == mtime and "summary" in cached:
            try:
                summaries.append(SessionSummary.from_dict(cached["summary"]))
                continue
            except (TypeError, ValueError):
                pass  # stale cache entry shape; fall through to reparse
        summary = parse_session(p)
        summaries.append(summary)
        cache[key] = {"mtime": mtime, "summary": summary.to_dict()}
        dirty = True

    if use_cache and dirty:
        _save_parse_cache(cache, cache_path)
    return summaries


def discover_session_files(projects_dir: Path) -> list:
    """Return sorted list of *.jsonl files for one project directory."""
    projects_dir = Path(projects_dir)
    if not projects_dir.is_dir():
        return []
    return sorted(projects_dir.glob("*.jsonl"))


__all__ = [
    "DEFAULT_FAMILY",
    "PRICING_PER_MILLION",
    "PRICING_VERIFIED_DATE",
    "SessionSummary",
    "compute_cost",
    "discover_session_files",
    "model_family",
    "parse_session",
    "parse_sessions",
]
