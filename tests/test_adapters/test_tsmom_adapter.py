"""Unit tests for the TSMOM adapter (P6 wrapper)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from terminal.adapters.tsmom_adapter import compute_signal


def _prices(trend: float, n: int = 300) -> pd.Series:
    rng = np.random.default_rng(1)
    returns = rng.normal(trend, 0.01, n)
    prices = 100 * np.cumprod(1 + returns)
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.Series(prices, index=idx, name="close")


def test_signal_positive_on_uptrend():
    result = compute_signal(_prices(trend=0.002))
    assert result["status"] == "success"
    assert result["signal"] == 1
    assert result["twelve_one_return"] > 0


def test_signal_negative_on_downtrend():
    result = compute_signal(_prices(trend=-0.002))
    assert result["signal"] == -1
    assert result["twelve_one_return"] < 0


def test_insufficient_history_fails():
    result = compute_signal(_prices(0.001, n=100))
    assert result["status"] == "failed"
    assert "history" in result["reason"]


def test_position_capped_at_2x():
    result = compute_signal(_prices(trend=0.002), target_vol=0.5)
    # High target vol could push position above 2.0 without the cap.
    assert abs(result["position"]) <= 2.0
