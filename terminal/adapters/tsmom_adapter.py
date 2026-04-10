"""TSMOM adapter (wraps P6 TSMOM Engine, signal snapshot only).

Returns the current time-series momentum signal (sign of 12-1 return)
and a vol-targeted sizing suggestion for a single ticker. No backtest,
no cost accounting.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


SOURCE_PROJECT = "P6: TSMOM Engine"
SIMPLIFICATIONS = ["Signal snapshot only", "No backtest", "No multi-asset sizing"]


def compute_signal(
    prices: pd.Series,
    target_vol: float = 0.15,
    vol_window: int = 60,
) -> dict[str, Any]:
    """Classic Moskowitz-style 12-1 momentum signal with vol targeting.

    Signal is +1 if the trailing 12m-ex-1m return is positive, -1 if
    negative, 0 if insufficient data. Position is signal scaled by the
    ratio of target vol to realized vol (capped at 2.0x gross).
    """
    if prices is None or len(prices) < 252:
        return {"status": "failed", "reason": "insufficient history", "source_project": SOURCE_PROJECT}
    t1 = float(prices.iloc[-21])
    t12 = float(prices.iloc[-252])
    if t12 == 0 or np.isnan(t12):
        return {"status": "failed", "reason": "invalid lookback price", "source_project": SOURCE_PROJECT}
    twelve_one = t1 / t12 - 1.0
    signal = 1 if twelve_one > 0 else (-1 if twelve_one < 0 else 0)
    returns = prices.pct_change().dropna().tail(vol_window)
    realized_vol = float(returns.std() * np.sqrt(252)) if not returns.empty else float("nan")
    if realized_vol and realized_vol == realized_vol and realized_vol > 0:
        position = signal * min(2.0, target_vol / realized_vol)
    else:
        position = float(signal)
    return {
        "status": "success",
        "source_project": SOURCE_PROJECT,
        "signal": signal,
        "twelve_one_return": twelve_one,
        "realized_vol": realized_vol,
        "target_vol": target_vol,
        "position": position,
    }
