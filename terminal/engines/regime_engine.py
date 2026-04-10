"""Rule-based market regime classifier (from P5, simplified).

Produces a composite RISK_ON / NEUTRAL / RISK_OFF label from four signals:
trend direction, vol stress, drawdown depth, and credit spread stress.
No HMM retraining at runtime; this is the live-path classifier only.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _annualized_vol(returns: pd.Series, window: int = 21) -> float:
    if returns is None or returns.empty:
        return float("nan")
    recent = returns.tail(window).dropna()
    if recent.empty:
        return float("nan")
    return float(recent.std() * np.sqrt(252))


def _drawdown(prices: pd.Series, lookback: int) -> float:
    if prices is None or prices.empty or lookback <= 0:
        return float("nan")
    window = prices.tail(lookback)
    peak = window.cummax()
    dd = (window / peak - 1.0).min()
    return float(dd)


def _trend_signal(prices: pd.Series, lookback: int) -> float:
    if prices is None or len(prices) < lookback + 1:
        return 0.0
    recent = prices.iloc[-1]
    earlier = prices.iloc[-lookback - 1]
    if earlier == 0 or np.isnan(earlier):
        return 0.0
    return float(recent / earlier - 1.0)


def classify_regime(
    spy_prices: pd.Series,
    hy_spread: pd.Series | None,
    regime_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Composite regime classifier.

    Signals are each scored in {-1, 0, +1}; the sum maps to a regime
    label via symmetric thresholds. Returns the label, a decomposition
    dict, and a simple confidence proxy based on agreement strength.
    """
    returns = spy_prices.pct_change().dropna() if spy_prices is not None else pd.Series(dtype=float)
    trend_lookback = int(regime_cfg["trend_lookback"])
    trend_threshold = float(regime_cfg["trend_score_threshold"])
    dd_lookback = trend_lookback * int(regime_cfg["drawdown_lookback_multiplier"])
    trend = _trend_signal(spy_prices, trend_lookback)
    vol = _annualized_vol(returns, 21)
    dd = _drawdown(spy_prices, dd_lookback)
    credit = float(hy_spread.dropna().iloc[-1]) if hy_spread is not None and not hy_spread.dropna().empty else float("nan")

    trend_score = 1 if trend > trend_threshold else (-1 if trend < -trend_threshold else 0)
    vol_score = -1 if (vol == vol and vol > regime_cfg["vol_stress_threshold"]) else 0
    dd_score = -1 if (dd == dd and dd < regime_cfg["drawdown_threshold"]) else 0
    credit_score = -1 if (credit == credit and credit > regime_cfg["credit_spread_threshold"]) else 0

    total = trend_score + vol_score + dd_score + credit_score
    if total >= 1:
        label = "RISK_ON"
    elif total <= -1:
        label = "RISK_OFF"
    else:
        label = "NEUTRAL"

    confidence = min(1.0, abs(total) / 4.0 + 0.25)
    return {
        "regime": label,
        "confidence": confidence,
        "signals": {
            "trend_return_pct": trend,
            "annualized_vol": vol,
            "drawdown_pct": dd,
            "hy_spread": credit,
        },
        "scores": {
            "trend": trend_score,
            "vol_stress": vol_score,
            "drawdown": dd_score,
            "credit": credit_score,
            "composite": total,
        },
    }
