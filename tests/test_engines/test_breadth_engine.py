"""Unit tests for the breadth engine."""

from __future__ import annotations

import numpy as np
import pandas as pd

from terminal.engines.breadth_engine import (
    advance_decline_ratio,
    compute_breadth,
    net_new_highs_lows,
    percent_above_ma,
)


def _synthetic_matrix(n=300, k=5, seed=1):
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.01, (n, k))
    prices = 100 * np.cumprod(1 + returns, axis=0)
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.DataFrame(prices, index=idx, columns=[f"T{i}" for i in range(k)])


def test_percent_above_ma_range():
    df = _synthetic_matrix()
    value = percent_above_ma(df, ma_period=50)
    assert 0.0 <= value <= 1.0


def test_advance_decline_ratio_positive():
    df = _synthetic_matrix()
    ratio = advance_decline_ratio(df)
    assert ratio != ratio or ratio >= 0


def test_new_highs_lows_shape():
    df = _synthetic_matrix()
    result = net_new_highs_lows(df, lookback_days=100)
    assert set(result.keys()) == {"new_highs", "new_lows", "net"}


def test_compute_breadth_uses_config(config):
    df = _synthetic_matrix()
    breadth = compute_breadth(df, config["market"]["breadth"])
    assert "pct_above_ma" in breadth
    assert "adv_decl_ratio" in breadth
    assert "new_highs_lows" in breadth
