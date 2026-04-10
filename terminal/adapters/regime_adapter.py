"""Regime adapter (wraps P5 Volatility Regime Engine, rule-based only).

Thin wrapper that calls into the regime engine so the UI can consume a
standardized output dict. No HMM retraining at runtime.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..engines.regime_engine import classify_regime


SOURCE_PROJECT = "P5: Volatility Regime Engine"
SIMPLIFICATIONS = ["Rule-based composite only", "No HMM retraining at runtime"]


def run_regime(
    spy_prices: pd.Series,
    hy_spread: pd.Series | None,
    regime_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Invoke the rule-based regime classifier and tag the response."""
    result = classify_regime(spy_prices, hy_spread, regime_cfg)
    result["source_project"] = SOURCE_PROJECT
    result["status"] = "success"
    return result
