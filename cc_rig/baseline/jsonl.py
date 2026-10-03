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

Costs come from cc_rig.pricing, priced per model id with 1-hour cache writes
split out from 5-minute ones.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from cc_rig.baseline.paths import PARSE_CACHE_PATH
from cc_rig.pricing import (
    DEFAULT_FAMILY,
    PRICING_VERIFIED_DATE,
    compute_cost,
    model_family,
    split_cache_writes,
)

# Bumped with pricing so cached summaries priced at old rates get reparsed.
_PARSE_CACHE_PRICING_KEY = "pricing"
# Bump when parse_session's output changes, so cached summaries get reparsed.
_PARSE_CACHE_PARSER_KEY = "parser"
_PARSER_VERSION = 2


@dataclass
class SessionSummary:
    """Aggregated metrics for one .jsonl session file."""

    session_id: str
    file_path: str
    file_mtime: float
    started_at: str = ""
    ended_at: str = ""
    primary_family: str = DEFAULT_FAMILY
    primary_model: str = ""
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_create_tokens: int = 0
    cache_create_1h_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cost_uncached_usd: float = 0.0
    claudemd_edits: int = 0
    model_switches: int = 0
    model_switch_cost_usd: float = 0.0
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


def _real_model(message: dict) -> str:
    """The message's model id, or "" when it carries no model information.

    Claude Code logs interrupts ("No response requested.") and API errors as
    assistant messages with model "<synthetic>" and zero usage. They say
    nothing about which model the session runs on.
    """
    model_id = message.get("model")
    if not isinstance(model_id, str) or model_id.startswith("<"):
        return ""
    return model_id


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
    last_model = ""
    # Claude Code writes one line per content block, each repeating the
    # message's usage. Keep the last usage per message id so a message is
    # counted once; lines without an id are counted as they come.
    usage_by_message: dict = {}
    anonymous_usage: list = []
    # The first usage after each model switch, kept by message id like above.
    switch_ids: set = set()
    switch_anonymous: list = []
    pending_switch = False

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

            model_id = _real_model(message)
            if model_id:
                family = model_family(model_id)
                if model_id not in summary.models_seen:
                    summary.models_seen.append(model_id)
                if last_family is not None and family != last_family:
                    summary.model_switches += 1
                    pending_switch = True
                last_family = family
                last_model = model_id

            usage = _extract_usage(message)
            if usage:
                entry = (model_id or last_model or last_family or DEFAULT_FAMILY, usage)
                msg_id = message.get("id")
                if isinstance(msg_id, str) and msg_id:
                    usage_by_message[msg_id] = entry
                    if pending_switch:
                        switch_ids.add(msg_id)
                else:
                    anonymous_usage.append(entry)
                    if pending_switch:
                        switch_anonymous.append(entry)
                pending_switch = False

            for tu in _iter_tool_uses(message):
                if _is_claudemd_edit(tu):
                    summary.claudemd_edits += 1

    cost_uncached_acc = 0.0
    for priced_as, usage in list(usage_by_message.values()) + anonymous_usage:
        t_in = int(usage.get("input_tokens") or 0)
        t_out = int(usage.get("output_tokens") or 0)
        t_cc = int(usage.get("cache_creation_input_tokens") or 0)
        t_cr = int(usage.get("cache_read_input_tokens") or 0)
        if not (t_in or t_out or t_cc or t_cr):
            continue
        w5m, w1h = split_cache_writes(usage)
        summary.assistant_turns += 1
        summary.input_tokens += t_in
        summary.output_tokens += t_out
        summary.cache_create_tokens += t_cc
        summary.cache_create_1h_tokens += w1h
        summary.cache_read_tokens += t_cr
        summary.cost_usd += compute_cost(t_in, t_out, w5m, t_cr, priced_as, w1h)
        # Uncached baseline: every cache read and write counts as fresh input.
        cost_uncached_acc += compute_cost(t_in + t_cr + t_cc, t_out, 0, 0, priced_as)

    summary.cost_uncached_usd = cost_uncached_acc

    # The new model has no cache yet, so its first turn writes the prefix
    # instead of reading it. That write, less what reading the same tokens
    # would have cost, is the switch's price. It runs slightly high: the
    # write also holds the turn's own new content. A switch back to a model
    # whose cache is still warm writes nothing and costs nothing.
    for priced_as, usage in [usage_by_message[i] for i in switch_ids] + switch_anonymous:
        w5m, w1h = split_cache_writes(usage)
        written = compute_cost(0, 0, w5m, 0, priced_as, w1h)
        summary.model_switch_cost_usd += written - compute_cost(0, 0, 0, w5m + w1h, priced_as)

    summary.primary_family = last_family or DEFAULT_FAMILY
    summary.primary_model = last_model
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
        if (
            cached
            and cached.get("mtime") == mtime
            and cached.get(_PARSE_CACHE_PRICING_KEY) == PRICING_VERIFIED_DATE
            and cached.get(_PARSE_CACHE_PARSER_KEY) == _PARSER_VERSION
            and "summary" in cached
        ):
            try:
                summaries.append(SessionSummary.from_dict(cached["summary"]))
                continue
            except (TypeError, ValueError):
                pass  # stale cache entry shape; fall through to reparse
        summary = parse_session(p)
        summaries.append(summary)
        cache[key] = {
            "mtime": mtime,
            _PARSE_CACHE_PRICING_KEY: PRICING_VERIFIED_DATE,
            _PARSE_CACHE_PARSER_KEY: _PARSER_VERSION,
            "summary": summary.to_dict(),
        }
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
    "PRICING_VERIFIED_DATE",
    "SessionSummary",
    "compute_cost",
    "discover_session_files",
    "model_family",
    "parse_session",
    "parse_sessions",
]
