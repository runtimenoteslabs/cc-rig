"""Tests for cc_rig.pricing: per-model rates, cache-write TTLs, hook source."""

from __future__ import annotations

import pytest

from cc_rig.pricing import (
    DEFAULT_FAMILY,
    FAMILY_PRICING,
    MODEL_PRICING,
    compute_cost,
    hook_pricing_source,
    model_family,
    prices_for,
    split_cache_writes,
)

M = 1_000_000


# ---------- prices_for -----------------------------------------------------


@pytest.mark.parametrize(
    "model_id, expected",
    [
        ("claude-opus-5-5", (4.0, 20.0, 0.20)),
        ("claude-opus-5", (5.0, 25.0, 0.50)),
        ("claude-opus-4-8", (5.0, 25.0, 0.50)),
        ("claude-opus-4-5-20251101", (5.0, 25.0, 0.50)),
        ("claude-opus-4-1-20250805", (15.0, 75.0, 1.50)),
        ("claude-opus-4-20250514", (15.0, 75.0, 1.50)),
        ("claude-sonnet-5-5", (2.0, 10.0, 0.20)),
        ("claude-sonnet-4-6", (3.0, 15.0, 0.30)),
        ("claude-haiku-4-5-20251001", (1.0, 5.0, 0.10)),
        ("claude-fable-5-1", (10.0, 50.0, 0.25)),
        ("claude-fable-5", (10.0, 50.0, 1.00)),
        ("claude-mythos-5-1", (10.0, 50.0, 0.25)),
    ],
)
def test_prices_for_matches_longest_prefix(model_id, expected):
    assert prices_for(model_id) == expected


def test_prices_for_accepts_bedrock_and_vertex_ids():
    assert prices_for("anthropic.claude-opus-5-5") == MODEL_PRICING["claude-opus-5-5"]
    assert prices_for("claude-opus-4-5@20251101") == MODEL_PRICING["claude-opus-4"]


def test_prices_for_accepts_family_names():
    assert prices_for("opus") == FAMILY_PRICING["opus"]
    assert prices_for("fable") == FAMILY_PRICING["fable"]


def test_prices_for_unknown_falls_back_to_family_then_default():
    assert prices_for("some-future-opus") == FAMILY_PRICING["opus"]
    assert prices_for("gpt-something") == FAMILY_PRICING[DEFAULT_FAMILY]
    assert prices_for("") == FAMILY_PRICING[DEFAULT_FAMILY]


def test_model_family_counts_mythos_as_fable():
    assert model_family("claude-mythos-5-1") == "fable"
    assert model_family("claude-fable-5-1") == "fable"


# ---------- cache writes -----------------------------------------------------


def test_split_cache_writes_without_breakdown_counts_all_as_5m():
    assert split_cache_writes({"cache_creation_input_tokens": 500}) == (500, 0)


def test_split_cache_writes_uses_ttl_breakdown():
    usage = {
        "cache_creation_input_tokens": 500,
        "cache_creation": {"ephemeral_1h_input_tokens": 300, "ephemeral_5m_input_tokens": 200},
    }
    assert split_cache_writes(usage) == (200, 300)


def test_split_cache_writes_clamps_inconsistent_breakdown():
    usage = {
        "cache_creation_input_tokens": 100,
        "cache_creation": {"ephemeral_1h_input_tokens": 400},
    }
    assert split_cache_writes(usage) == (0, 100)


def test_compute_cost_prices_write_ttls_and_reads_per_model():
    # Opus 5.5: input $4, so a 5-minute write is $5 and a 1-hour write is $8.
    assert compute_cost(0, 0, M, 0, "claude-opus-5-5") == pytest.approx(5.0)
    assert compute_cost(0, 0, 0, 0, "claude-opus-5-5", cache_write_1h_tokens=M) == pytest.approx(
        8.0
    )
    assert compute_cost(0, 0, 0, M, "claude-opus-5-5") == pytest.approx(0.20)
    assert compute_cost(0, 0, 0, M, "claude-fable-5-1") == pytest.approx(0.25)


# ---------- hook_pricing_source --------------------------------------------


def _hook_namespace() -> dict:
    ns: dict = {}
    exec(hook_pricing_source(), ns)  # noqa: S102 - testing generated source
    return ns


def test_hook_source_is_safe_inside_double_quoted_bash():
    src = hook_pricing_source()
    for ch in ('"', "$", "`", "\\"):
        assert ch not in src, f"{ch!r} would break the loop.sh python -c string"


@pytest.mark.parametrize("model_id", [*MODEL_PRICING, "anthropic.claude-opus-5-5", "mystery"])
def test_hook_source_agrees_with_compute_cost(model_id):
    usage = {
        "input_tokens": 1_234,
        "output_tokens": 5_678,
        "cache_creation_input_tokens": 90_000,
        "cache_creation": {"ephemeral_1h_input_tokens": 60_000},
        "cache_read_input_tokens": 400_000,
    }
    expected = compute_cost(1_234, 5_678, 30_000, 400_000, model_id, 60_000)
    assert _hook_namespace()["usage_cost"](usage, model_id) == pytest.approx(expected)


def test_hook_source_savings_nets_out_the_write_premium():
    ns = _hook_namespace()
    # Opus 5.5: reading 1M saves $3.80; a 1M 1-hour write costs $4 over input.
    usage = {
        "cache_read_input_tokens": M,
        "cache_creation_input_tokens": M,
        "cache_creation": {"ephemeral_1h_input_tokens": M},
    }
    assert ns["usage_savings"](usage, "claude-opus-5-5") == pytest.approx(3.80 - 4.0)
