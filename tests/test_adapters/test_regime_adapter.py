"""Unit tests for the regime adapter (P5 wrapper)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from terminal.adapters.regime_adapter import SOURCE_PROJECT, run_regime


def test_adapter_tags_source_project(config):
    idx = pd.date_range("2023-01-01", periods=300, freq="B")
    prices = pd.Series(np.linspace(100, 120, 300), index=idx)
    result = run_regime(prices, None, config["market"]["regime"])
    assert result["source_project"] == SOURCE_PROJECT
    assert result["status"] == "success"
    assert result["regime"] in {"RISK_ON", "NEUTRAL", "RISK_OFF"}


def test_adapter_forwards_signals(config):
    idx = pd.date_range("2023-01-01", periods=300, freq="B")
    prices = pd.Series(np.linspace(100, 120, 300), index=idx)
    result = run_regime(prices, None, config["market"]["regime"])
    assert "trend_return_pct" in result["signals"]
    assert "annualized_vol" in result["signals"]


def test_adapter_with_credit_spread(config):
    idx = pd.date_range("2023-01-01", periods=300, freq="B")
    prices = pd.Series(np.linspace(100, 110, 300), index=idx)
    hy = pd.Series([6.5] * 10, index=pd.date_range("2024-01-01", periods=10))
    result = run_regime(prices, hy, config["market"]["regime"])
    assert result["signals"]["hy_spread"] == 6.5
    assert result["scores"]["credit"] == -1  # above the configured stress threshold
