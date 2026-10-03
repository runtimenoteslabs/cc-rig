"""Claude API pricing: the single source for every cost estimate cc-rig makes.

Prices are USD per million tokens. Cache writes are priced from the input
rate (1.25x for the 5-minute TTL, 2x for the 1-hour TTL); cache reads have
their own per-model rate because the read discount differs by model.

Generated hook scripts can't import cc-rig, so they carry a copy of this
table built by ``hook_pricing_source()``. Never hand-edit those copies.
"""

from __future__ import annotations

from typing import Dict, Tuple

# Bump when Anthropic prices change.
# Source: platform.claude.com/docs/en/about-claude/pricing
PRICING_VERIFIED_DATE = "2026-10-02"

# (input, output, cache_read) keyed by model-id prefix. The longest matching
# prefix wins, so "claude-opus-5-5" beats "claude-opus-5".
MODEL_PRICING: Dict[str, Tuple[float, float, float]] = {
    "claude-fable-5-1": (10.0, 50.0, 0.25),
    "claude-mythos-5-1": (10.0, 50.0, 0.25),
    "claude-fable-5": (10.0, 50.0, 1.00),
    "claude-mythos-5": (10.0, 50.0, 1.00),
    "claude-opus-5-5": (4.0, 20.0, 0.20),
    "claude-opus-5": (5.0, 25.0, 0.50),
    "claude-opus-4": (5.0, 25.0, 0.50),  # Opus 4.5 through 4.8
    "claude-opus-4-0": (15.0, 75.0, 1.50),
    "claude-opus-4-1": (15.0, 75.0, 1.50),
    "claude-opus-4-2025": (15.0, 75.0, 1.50),  # Opus 4.0 dated id
    "claude-sonnet-5": (2.0, 10.0, 0.20),  # Sonnet 5 and 5.5
    "claude-sonnet-4": (3.0, 15.0, 0.30),
    "claude-haiku-4": (1.0, 5.0, 0.10),
    "claude-3-5-haiku": (0.80, 4.0, 0.08),
}

# Fallback for ids no prefix matches: the current model of each line.
FAMILY_PRICING: Dict[str, Tuple[float, float, float]] = {
    "fable": MODEL_PRICING["claude-fable-5-1"],
    "opus": MODEL_PRICING["claude-opus-5-5"],
    "sonnet": MODEL_PRICING["claude-sonnet-5"],
    "haiku": MODEL_PRICING["claude-haiku-4"],
}
DEFAULT_FAMILY = "sonnet"

CACHE_WRITE_5M = 1.25
CACHE_WRITE_1H = 2.0


def model_family(model_id: str) -> str:
    """Map a Claude model id to its line: fable, opus, sonnet, or haiku.

    Mythos ids count as fable (same tier and price). Unknown ids fall back
    to sonnet, the middle of the range.
    """
    m = (model_id or "").lower()
    if "fable" in m or "mythos" in m:
        return "fable"
    for family in ("opus", "haiku", "sonnet"):
        if family in m:
            return family
    return DEFAULT_FAMILY


def prices_for(model: str) -> Tuple[float, float, float]:
    """Return (input, output, cache_read) for a model id or a family name.

    Accepts dated ids, Bedrock ids ("anthropic.claude-opus-5-5"), and Vertex
    ids ("claude-opus-4-5@20251101").
    """
    if model in FAMILY_PRICING:
        return FAMILY_PRICING[model]
    m = (model or "").lower()
    start = m.find("claude-")
    if start >= 0:
        m = m[start:]
        matches = [p for p in MODEL_PRICING if m.startswith(p)]
        if matches:
            return MODEL_PRICING[max(matches, key=len)]
    return FAMILY_PRICING[model_family(model)]


def split_cache_writes(usage: dict) -> Tuple[int, int]:
    """Split a usage block's cache writes into (5-minute, 1-hour) tokens.

    Claude Code reports the TTL breakdown under ``usage.cache_creation``.
    Older logs lack it, so every write counts as 5-minute there.
    """
    total = int(usage.get("cache_creation_input_tokens") or 0)
    breakdown = usage.get("cache_creation")
    if not isinstance(breakdown, dict):
        return total, 0
    one_hour = min(total, int(breakdown.get("ephemeral_1h_input_tokens") or 0))
    return total - one_hour, one_hour


def compute_cost(
    input_tokens: int,
    output_tokens: int,
    cache_write_5m_tokens: int,
    cache_read_tokens: int,
    model: str,
    cache_write_1h_tokens: int = 0,
) -> float:
    """Estimate USD cost for token counts on a model id or family name."""
    p_in, p_out, p_read = prices_for(model)
    total = (
        input_tokens * p_in
        + output_tokens * p_out
        + cache_write_5m_tokens * p_in * CACHE_WRITE_5M
        + cache_write_1h_tokens * p_in * CACHE_WRITE_1H
        + cache_read_tokens * p_read
    )
    return total / 1_000_000.0


def hook_pricing_source() -> str:
    """Python source that generated hook scripts embed to price usage.

    Defines ``price(model_id)``, ``usage_cost(usage, model_id)`` and
    ``usage_savings(usage, model_id)``. Uses only single quotes and no
    ``$`` or backslashes, so it is safe inside a double-quoted bash string.
    """
    rows = "".join(f"    {k!r}: {v!r},\n" for k, v in MODEL_PRICING.items())
    families = "".join(f"    {k!r}: {v!r},\n" for k, v in FAMILY_PRICING.items())
    return (
        f"# Generated from cc_rig/pricing.py (verified {PRICING_VERIFIED_DATE}).\n"
        "# Per million tokens: (input, output, cache_read).\n"
        "PRICES = {\n" + rows + "}\n"
        "FAMILY = {\n" + families + "}\n"
        "\n"
        "def model_family(model_id):\n"
        "    m = (model_id or '').lower()\n"
        "    if 'fable' in m or 'mythos' in m:\n"
        "        return 'fable'\n"
        "    for fam in ('opus', 'haiku', 'sonnet'):\n"
        "        if fam in m:\n"
        "            return fam\n"
        f"    return {DEFAULT_FAMILY!r}\n"
        "\n"
        "def price(model_id):\n"
        "    m = (model_id or '').lower()\n"
        "    start = m.find('claude-')\n"
        "    if start >= 0:\n"
        "        m = m[start:]\n"
        "        hits = [p for p in PRICES if m.startswith(p)]\n"
        "        if hits:\n"
        "            return PRICES[max(hits, key=len)]\n"
        "    return FAMILY[model_family(model_id)]\n"
        "\n"
        "def cache_writes(u):\n"
        "    total = u.get('cache_creation_input_tokens', 0) or 0\n"
        "    cc = u.get('cache_creation') or {}\n"
        "    one_hour = min(total, cc.get('ephemeral_1h_input_tokens', 0) or 0)\n"
        "    return total - one_hour, one_hour\n"
        "\n"
        "def usage_cost(u, model_id):\n"
        "    p_in, p_out, p_read = price(model_id)\n"
        "    w5m, w1h = cache_writes(u)\n"
        "    return ((u.get('input_tokens', 0) or 0) * p_in\n"
        "            + (u.get('output_tokens', 0) or 0) * p_out\n"
        f"            + w5m * p_in * {CACHE_WRITE_5M!r} + w1h * p_in * {CACHE_WRITE_1H!r}\n"
        "            + (u.get('cache_read_input_tokens', 0) or 0) * p_read) / 1000000\n"
        "\n"
        "def usage_savings(u, model_id):\n"
        "    # Read discount minus the premium paid to write the cache.\n"
        "    p_in, p_out, p_read = price(model_id)\n"
        "    w5m, w1h = cache_writes(u)\n"
        "    gain = (u.get('cache_read_input_tokens', 0) or 0) * (p_in - p_read)\n"
        f"    premium = (w5m * {CACHE_WRITE_5M - 1:.2f} + w1h * {CACHE_WRITE_1H - 1:.2f}) * p_in\n"
        "    return (gain - premium) / 1000000\n"
    )


__all__ = [
    "CACHE_WRITE_1H",
    "CACHE_WRITE_5M",
    "DEFAULT_FAMILY",
    "FAMILY_PRICING",
    "MODEL_PRICING",
    "PRICING_VERIFIED_DATE",
    "compute_cost",
    "hook_pricing_source",
    "model_family",
    "prices_for",
    "split_cache_writes",
]
