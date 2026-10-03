"""Tests for the JSONL session parser.

Drives parsing against synthetic fixtures with hand-computed token totals.
Synthetic > anonymized real: numbers are easy to eyeball, no privacy risk,
no need to keep fixtures in sync with private session history.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cc_rig.baseline.jsonl import (
    DEFAULT_FAMILY,
    SessionSummary,
    compute_cost,
    discover_session_files,
    model_family,
    parse_session,
    parse_sessions,
)
from cc_rig.pricing import FAMILY_PRICING, PRICING_VERIFIED_DATE

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "jsonl"


# ---------- model_family ---------------------------------------------------


def test_model_family_recognizes_known_ids():
    assert model_family("claude-opus-4-6") == "opus"
    assert model_family("claude-sonnet-4-6") == "sonnet"
    assert model_family("claude-haiku-4-5-20251001") == "haiku"


def test_model_family_handles_empty_or_unknown():
    assert model_family("") == DEFAULT_FAMILY
    assert model_family("some-unknown-model") == DEFAULT_FAMILY


# ---------- compute_cost ---------------------------------------------------


def test_compute_cost_uses_family_pricing():
    cost = compute_cost(1_000_000, 0, 0, 0, "sonnet")
    assert cost == FAMILY_PRICING["sonnet"][0]


def test_compute_cost_zeros_yield_zero():
    assert compute_cost(0, 0, 0, 0, "opus") == 0.0


def test_compute_cost_unknown_family_falls_back():
    assert compute_cost(1_000_000, 0, 0, 0, "fictional") == FAMILY_PRICING[DEFAULT_FAMILY][0]


# ---------- parse_session: quick tier --------------------------------------


def test_parse_session_q1_sonnet_aggregates_correctly():
    summary = parse_session(FIXTURES / "quick" / "session_q1.jsonl")
    # q1 sums: input 100+50+30=180, output 200+150+100=450,
    # cache_create 1000, cache_read 0+1000+1000=2000.
    assert summary.input_tokens == 180
    assert summary.output_tokens == 450
    assert summary.cache_create_tokens == 1000
    assert summary.cache_read_tokens == 2000
    assert summary.assistant_turns == 3
    assert summary.primary_family == "sonnet"
    assert summary.claudemd_edits == 0
    assert summary.model_switches == 0


def test_parse_session_q1_cost_is_positive_and_below_uncached():
    summary = parse_session(FIXTURES / "quick" / "session_q1.jsonl")
    assert summary.cost_usd > 0
    assert summary.cost_uncached_usd > summary.cost_usd
    assert summary.savings_pct > 0
    assert summary.savings_pct < 100


def test_parse_session_q2_detects_haiku_family():
    summary = parse_session(FIXTURES / "quick" / "session_q2.jsonl")
    assert summary.primary_family == "haiku"
    assert summary.input_tokens == 300
    assert summary.cache_read_tokens == 3000


def test_parse_session_q3_records_model_switch():
    """sonnet -> opus is one switch (one adjacent family change)."""
    summary = parse_session(FIXTURES / "quick" / "session_q3_mixed.jsonl")
    assert summary.model_switches == 1
    # We saw both model ids
    assert any("sonnet" in m for m in summary.models_seen)
    assert any("opus" in m for m in summary.models_seen)


# ---------- parse_session: real-log shape --------------------------------


def _assistant_line(msg_id, usage, model="claude-opus-5-5"):
    message = {"role": "assistant", "model": model, "usage": usage}
    if msg_id is not None:
        message["id"] = msg_id
    return json.dumps({"type": "assistant", "message": message})


def test_parse_session_counts_each_message_once(tmp_path):
    """Claude Code repeats a message's usage on each content-block line."""
    partial = {"input_tokens": 5, "output_tokens": 1, "cache_read_input_tokens": 2000}
    final = {"input_tokens": 5, "output_tokens": 500, "cache_read_input_tokens": 2000}
    other = {"input_tokens": 10, "output_tokens": 100, "cache_creation_input_tokens": 3000}
    lines = [
        _assistant_line("msg_a", partial),
        _assistant_line("msg_a", partial),
        _assistant_line("msg_a", final),
        _assistant_line("msg_b", other),
    ]
    path = tmp_path / "s.jsonl"
    path.write_text("\n".join(lines) + "\n")

    summary = parse_session(path)

    assert summary.assistant_turns == 2
    assert summary.output_tokens == 600  # last usage of msg_a, plus msg_b
    assert summary.cache_read_tokens == 2000
    expected = compute_cost(5, 500, 0, 2000, "claude-opus-5-5") + compute_cost(
        10, 100, 3000, 0, "claude-opus-5-5"
    )
    assert summary.cost_usd == pytest.approx(expected)


def test_parse_session_prices_one_hour_cache_writes(tmp_path):
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 1_000_000,
        "cache_creation": {"ephemeral_1h_input_tokens": 1_000_000},
    }
    path = tmp_path / "s.jsonl"
    path.write_text(_assistant_line("msg_a", usage) + "\n")

    summary = parse_session(path)

    assert summary.cache_create_1h_tokens == 1_000_000
    assert summary.primary_model == "claude-opus-5-5"
    assert summary.cost_usd == pytest.approx(8.0)  # Opus 5.5 input $4 x 2


def test_parse_sessions_reparses_entries_priced_at_old_rates(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(_assistant_line("msg_a", {"input_tokens": 1_000_000}) + "\n")
    stale = SessionSummary(
        session_id="s", file_path=str(path), file_mtime=path.stat().st_mtime, cost_usd=999.0
    )
    cache_path = tmp_path / "parse-cache.json"
    cache_path.write_text(
        json.dumps({str(path): {"mtime": path.stat().st_mtime, "summary": stale.to_dict()}})
    )

    (summary,) = parse_sessions([path], cache_path=cache_path)

    assert summary.cost_usd == pytest.approx(4.0)
    saved = json.loads(cache_path.read_text())[str(path)]
    assert saved["pricing"] == PRICING_VERIFIED_DATE


def test_parse_sessions_reparses_entries_from_an_older_parser(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(_assistant_line("msg_a", {"input_tokens": 1_000_000}) + "\n")
    stale = SessionSummary(
        session_id="s", file_path=str(path), file_mtime=path.stat().st_mtime, model_switches=1
    )
    entry = {"mtime": path.stat().st_mtime, "pricing": PRICING_VERIFIED_DATE}
    cache_path = tmp_path / "parse-cache.json"
    cache_path.write_text(json.dumps({str(path): {**entry, "summary": stale.to_dict()}}))

    (summary,) = parse_sessions([path], cache_path=cache_path)

    assert summary.model_switches == 0
    assert "parser" in json.loads(cache_path.read_text())[str(path)]


# ---------- parse_session: interrupts and model switches -------------------

# Claude Code logs an interrupt or an API error as an assistant message with
# model "<synthetic>" and zero usage (shapes copied from real session logs).
_ZERO_USAGE = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0},
}


def _synthetic_line(text, api_error=False):
    message = {
        "id": f"synthetic-{len(text)}",
        "role": "assistant",
        "model": "<synthetic>",
        "content": [{"type": "text", "text": text}],
        "usage": _ZERO_USAGE,
    }
    event = {"type": "assistant", "isApiErrorMessage": api_error, "message": message}
    return json.dumps(event)


def _write_1h(tokens):
    return {
        "input_tokens": 5,
        "output_tokens": 100,
        "cache_creation_input_tokens": tokens,
        "cache_creation": {"ephemeral_1h_input_tokens": tokens},
        "cache_read_input_tokens": 0,
    }


_READ = {"input_tokens": 5, "output_tokens": 100, "cache_read_input_tokens": 30_000}


@pytest.mark.parametrize(
    "synthetic",
    [
        _synthetic_line("No response requested."),
        _synthetic_line("Login expired · Please run /login", api_error=True),
    ],
    ids=["interrupt", "api-error"],
)
def test_synthetic_message_is_not_a_model_switch(tmp_path, synthetic):
    path = tmp_path / "s.jsonl"
    path.write_text("\n".join([_assistant_line("msg_a", _write_1h(30_000)), synthetic]) + "\n")

    summary = parse_session(path)

    assert summary.model_switches == 0
    assert summary.model_switch_cost_usd == 0.0
    assert summary.models_seen == ["claude-opus-5-5"]
    assert summary.primary_model == "claude-opus-5-5"
    assert summary.primary_family == "opus"


def test_message_without_model_is_priced_at_the_session_model(tmp_path):
    no_model = json.dumps({"type": "assistant", "message": {"id": "msg_b", "usage": _READ}})
    path = tmp_path / "s.jsonl"
    path.write_text("\n".join([_assistant_line("msg_a", _write_1h(30_000)), no_model]) + "\n")

    summary = parse_session(path)

    assert summary.model_switches == 0
    expected = compute_cost(5, 100, 0, 0, "claude-opus-5-5", 30_000) + compute_cost(
        5, 100, 0, 30_000, "claude-opus-5-5"
    )
    assert summary.cost_usd == pytest.approx(expected)


def test_model_switch_is_priced_from_the_cache_rewrite_after_it(tmp_path):
    """The new model writes the 30K prefix once; later turns read it back."""
    lines = [
        _assistant_line("msg_a", _write_1h(30_000)),
        _assistant_line("msg_a", _write_1h(30_000)),
        *[_assistant_line("msg_b", _write_1h(30_000), model="claude-sonnet-5-5")] * 3,
        _assistant_line("msg_c", _READ, model="claude-sonnet-5-5"),
    ]
    path = tmp_path / "s.jsonl"
    path.write_text("\n".join(lines) + "\n")

    summary = parse_session(path)

    assert summary.model_switches == 1
    # Sonnet 5.5: a 1-hour write at $4/M instead of a read at $0.20/M.
    assert summary.model_switch_cost_usd == pytest.approx(30_000 * (4.0 - 0.20) / 1e6)


def test_switch_back_to_a_warm_cache_costs_nothing(tmp_path):
    lines = [
        _assistant_line("msg_a", _write_1h(30_000)),
        _assistant_line("msg_b", _write_1h(30_000), model="claude-sonnet-5-5"),
        _assistant_line("msg_c", _READ),
    ]
    path = tmp_path / "s.jsonl"
    path.write_text("\n".join(lines) + "\n")

    summary = parse_session(path)

    assert summary.model_switches == 2
    assert summary.model_switch_cost_usd == pytest.approx(30_000 * (4.0 - 0.20) / 1e6)


# ---------- parse_session: standard tier -----------------------------------


def test_parse_session_s1_high_cache_ratio():
    summary = parse_session(FIXTURES / "standard" / "session_s1.jsonl")
    # cache_create 10000 + cache_read (10000+10000+10500) = 40500 total cache-ish
    assert summary.cache_create_tokens == 10000
    assert summary.cache_read_tokens == 30500
    # cache_read_ratio = 30500 / (30500 + 10000) ~= 0.753
    assert 0.7 < summary.cache_read_ratio < 0.8


def test_parse_session_s2_counts_claudemd_edits():
    """Two CLAUDE.md tool_uses (one Edit, one Write) on different turns."""
    summary = parse_session(FIXTURES / "standard" / "session_s2_claudemd.jsonl")
    assert summary.claudemd_edits == 2


def test_parse_session_s3_timestamps_span_session():
    summary = parse_session(FIXTURES / "standard" / "session_s3.jsonl")
    assert summary.started_at == "2026-05-06T08:00:00.000Z"
    assert summary.ended_at == "2026-05-06T08:00:30.000Z"


# ---------- parse_session: rigorous tier + malformed input -----------------


def test_parse_session_r1_opus_pricing():
    summary = parse_session(FIXTURES / "rigorous" / "session_r1.jsonl")
    assert summary.primary_family == "opus"
    # Opus is more expensive per token; quick sanity check.
    sonnet_cost = compute_cost(
        summary.input_tokens,
        summary.output_tokens,
        summary.cache_create_tokens,
        summary.cache_read_tokens,
        "sonnet",
    )
    assert summary.cost_usd > sonnet_cost


def test_parse_session_r2_skips_malformed_lines():
    """A garbage line + an empty line + an event missing 'type' must not raise."""
    summary = parse_session(FIXTURES / "rigorous" / "session_r2_malformed.jsonl")
    # The two valid assistant turns: 800+200 input, 1500+600 output
    assert summary.input_tokens == 1000
    assert summary.output_tokens == 2100
    assert summary.assistant_turns == 2


def test_parse_session_r3_counts_family_switches():
    """sonnet -> opus -> sonnet -> haiku = three adjacent family changes."""
    summary = parse_session(FIXTURES / "rigorous" / "session_r3_switch.jsonl")
    assert summary.model_switches == 3


# ---------- robustness ----------------------------------------------------


def test_parse_session_empty_file(tmp_path):
    target = tmp_path / "empty.jsonl"
    target.write_text("", encoding="utf-8")
    summary = parse_session(target)
    assert summary.assistant_turns == 0
    assert summary.cost_usd == 0.0
    assert summary.cache_read_ratio == 0.0
    assert summary.savings_pct == 0.0


def test_parse_session_missing_usage_block_is_skipped(tmp_path):
    target = tmp_path / "no_usage.jsonl"
    target.write_text(
        '{"type":"assistant","timestamp":"2026-05-04T00:00:00Z",'
        '"message":{"role":"assistant","model":"claude-sonnet-4-6"}}\n',
        encoding="utf-8",
    )
    summary = parse_session(target)
    assert summary.assistant_turns == 0


def test_parse_session_handles_non_dict_event(tmp_path):
    target = tmp_path / "weird.jsonl"
    # Some lines are JSON but not objects -- must not raise.
    target.write_text('"a string"\n[1,2,3]\nnull\n', encoding="utf-8")
    summary = parse_session(target)
    assert summary.assistant_turns == 0


# ---------- discover_session_files ----------------------------------------


def test_discover_session_files_returns_sorted_jsonl(tmp_path):
    (tmp_path / "b.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "a.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "not_jsonl.txt").write_text("", encoding="utf-8")
    found = discover_session_files(tmp_path)
    assert [p.name for p in found] == ["a.jsonl", "b.jsonl"]


def test_discover_session_files_handles_missing_dir(tmp_path):
    assert discover_session_files(tmp_path / "nope") == []


# ---------- parse_sessions + cache ----------------------------------------


def test_parse_sessions_caches_by_mtime(tmp_path):
    """Second invocation must skip reparsing when mtime unchanged."""
    fixture = FIXTURES / "quick" / "session_q1.jsonl"
    copy = tmp_path / "q1.jsonl"
    copy.write_bytes(fixture.read_bytes())
    cache_path = tmp_path / "parse-cache.json"

    first = parse_sessions([copy], cache_path=cache_path)
    assert len(first) == 1
    assert cache_path.exists()
    cache_data = json.loads(cache_path.read_text())
    assert str(copy) in cache_data
    mtime_after_first = cache_path.stat().st_mtime

    # Sleep just long enough that a second write would have a different mtime.
    time.sleep(0.05)
    second = parse_sessions([copy], cache_path=cache_path)
    assert len(second) == 1
    assert second[0].input_tokens == first[0].input_tokens
    # Cache file was not rewritten because no entries changed.
    assert cache_path.stat().st_mtime == mtime_after_first


def test_parse_sessions_reparses_when_mtime_changes(tmp_path):
    fixture = FIXTURES / "quick" / "session_q1.jsonl"
    copy = tmp_path / "q1.jsonl"
    copy.write_bytes(fixture.read_bytes())
    cache_path = tmp_path / "parse-cache.json"

    parse_sessions([copy], cache_path=cache_path)

    # Append a new assistant turn and bump mtime.
    with copy.open("a", encoding="utf-8") as fp:
        fp.write(
            '{"type":"assistant","timestamp":"2026-05-04T10:01:00.000Z","sessionId":"q1",'
            '"message":{"role":"assistant","model":"claude-sonnet-4-6","usage":'
            '{"input_tokens":1000,"output_tokens":1000,"cache_creation_input_tokens":0,'
            '"cache_read_input_tokens":0}}}\n'
        )
    new_mtime = time.time() + 1
    import os

    os.utime(copy, (new_mtime, new_mtime))

    second = parse_sessions([copy], cache_path=cache_path)
    # Should reflect the new turn (input_tokens jumped by 1000).
    assert second[0].input_tokens == 180 + 1000


def test_parse_sessions_use_cache_false_always_reparses(tmp_path):
    fixture = FIXTURES / "quick" / "session_q1.jsonl"
    copy = tmp_path / "q1.jsonl"
    copy.write_bytes(fixture.read_bytes())
    cache_path = tmp_path / "parse-cache.json"

    parse_sessions([copy], cache_path=cache_path, use_cache=False)
    # No cache file should be written
    assert not cache_path.exists()


def test_parse_sessions_skips_missing_files(tmp_path):
    cache_path = tmp_path / "parse-cache.json"
    summaries = parse_sessions([tmp_path / "nope.jsonl"], cache_path=cache_path)
    assert summaries == []


# ---------- performance smoke test ----------------------------------------


def test_parse_sessions_under_2s_for_100_files(tmp_path):
    """Spec §Performance: <2s for 100 sessions / 50 MB total.

    We can't realistically build 50 MB of fixtures inline, but we can copy a
    representative session 100 times and require comfortably-under-2s. This
    guards against catastrophic regressions, not 50 MB scale.
    """
    fixture = FIXTURES / "standard" / "session_s1.jsonl"
    for i in range(100):
        (tmp_path / f"sess_{i:03d}.jsonl").write_bytes(fixture.read_bytes())
    files = list(tmp_path.glob("*.jsonl"))
    cache_path = tmp_path / "parse-cache.json"

    start = time.perf_counter()
    summaries = parse_sessions(files, cache_path=cache_path)
    elapsed = time.perf_counter() - start

    assert len(summaries) == 100
    assert elapsed < 2.0, f"parsing 100 files took {elapsed:.2f}s (budget 2.0s)"


# ---------- SessionSummary roundtrip --------------------------------------


def test_session_summary_roundtrip():
    s = SessionSummary(
        session_id="abc",
        file_path="/tmp/abc.jsonl",
        file_mtime=1234.0,
        input_tokens=100,
        output_tokens=200,
    )
    restored = SessionSummary.from_dict(s.to_dict())
    assert restored == s
