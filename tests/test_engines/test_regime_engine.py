"""Unit tests for the rule-based regime engine."""

from __future__ import annotations

import numpy as np
import pandas as pd

from terminal.engines.regime_engine import classify_regime


def test_risk_on_when_trend_up_and_vol_normal(config):
    idx = pd.date_range("2023-01-01", periods=300, freq="B")
    trend = np.linspace(100, 140, 300)
    prices = pd.Series(trend, index=idx)
    result = classify_regime(prices, hy_spread=None, regime_cfg=config["market"]["regime"])
    assert result["regime"] in {"RISK_ON", "NEUTRAL"}
    assert result["signals"]["trend_return_pct"] > 0


def test_risk_off_when_drawdown_and_crash(config):
    idx = pd.date_range("2023-01-01", periods=300, freq="B")
    rng = np.random.default_rng(3)
    shocks = rng.normal(0, 0.02, 300)
    path = 100 * np.cumprod(1 + shocks)
    path[-30:] *= np.linspace(1.0, 0.75, 30)
    prices = pd.Series(path, index=idx)
    result = classify_regime(prices, hy_spread=None, regime_cfg=config["market"]["regime"])
    assert result["regime"] in {"RISK_OFF", "NEUTRAL"}
    assert result["signals"]["drawdown_pct"] < 0


def test_composite_score_within_bounds(config):
    idx = pd.date_range("2023-01-01", periods=300, freq="B")
    prices = pd.Series(np.linspace(100, 110, 300), index=idx)
    result = classify_regime(prices, None, config["market"]["regime"])
    assert -4 <= result["scores"]["composite"] <= 4
    assert 0 <= result["confidence"] <= 1
