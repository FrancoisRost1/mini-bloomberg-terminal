"""Unit tests for the factor exposure adapter (P3 wrapper)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from terminal.adapters.factor_adapter import FACTOR_KEYS, compute_factor_snapshot


def _synth_prices(n=400, trend=0.0005, seed=1) -> pd.Series:
    rng = np.random.default_rng(seed)
    returns = rng.normal(trend, 0.01, n)
    prices = 100 * np.cumprod(1 + returns)
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.Series(prices, index=idx, name="close")


def test_snapshot_returns_five_factors():
    ratios = {"pe_ratio": 15, "roic": 0.18, "market_cap": 5e9}
    result = compute_factor_snapshot(ratios, _synth_prices())
    assert result["status"] == "success"
    assert set(result["factor_scores"].keys()) == set(FACTOR_KEYS)


def test_momentum_positive_for_uptrend():
    ratios = {"pe_ratio": 15, "roic": 0.15, "market_cap": 1e10}
    up = compute_factor_snapshot(ratios, _synth_prices(trend=0.002))
    down = compute_factor_snapshot(ratios, _synth_prices(trend=-0.002))
    assert up["factor_scores"]["momentum"] > down["factor_scores"]["momentum"]


def test_value_inverse_of_pe():
    cheap = compute_factor_snapshot({"pe_ratio": 8, "roic": 0.1, "market_cap": 1e9}, _synth_prices())
    rich = compute_factor_snapshot({"pe_ratio": 40, "roic": 0.1, "market_cap": 1e9}, _synth_prices())
    assert cheap["factor_scores"]["value"] > rich["factor_scores"]["value"]


def test_quality_increases_with_roic():
    low = compute_factor_snapshot({"pe_ratio": 15, "roic": 0.05, "market_cap": 1e9}, _synth_prices())
    high = compute_factor_snapshot({"pe_ratio": 15, "roic": 0.35, "market_cap": 1e9}, _synth_prices())
    assert high["factor_scores"]["quality"] > low["factor_scores"]["quality"]


def test_short_history_yields_nan_momentum():
    short = _synth_prices(n=100)
    result = compute_factor_snapshot({"pe_ratio": 15, "roic": 0.1, "market_cap": 1e9}, short)
    assert result["factor_scores"]["momentum"] != result["factor_scores"]["momentum"]  # NaN


def test_confidence_higher_with_peers():
    ratios = {"pe_ratio": 15, "roic": 0.18, "market_cap": 5e9}
    no_peers = compute_factor_snapshot(ratios, _synth_prices())
    peers = pd.DataFrame({"value": [0.1, 0.2, 0.3], "quality": [0.4, 0.5, 0.6]})
    with_peers = compute_factor_snapshot(ratios, _synth_prices(), peer_ratios=peers)
    assert with_peers["confidence"] > no_peers["confidence"]
