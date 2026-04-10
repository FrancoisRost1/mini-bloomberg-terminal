"""Market breadth metrics.

Computes three classic breadth readings over a configurable ETF universe:
percent of constituents above their moving average, advance/decline ratio,
and net new highs/lows. Used in the Market Overview workspace.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def percent_above_ma(prices: pd.DataFrame, ma_period: int) -> float:
    """Fraction of universe whose last close sits above its N-day MA."""
    if prices is None or prices.empty:
        return float("nan")
    ma = prices.rolling(window=ma_period, min_periods=ma_period // 2).mean()
    last = prices.iloc[-1]
    last_ma = ma.iloc[-1]
    above = (last > last_ma).sum()
    valid = last_ma.notna().sum()
    if valid == 0:
        return float("nan")
    return float(above / valid)


def advance_decline_ratio(prices: pd.DataFrame) -> float:
    """Ratio of advancers to decliners on the most recent session."""
    if prices is None or len(prices) < 2:
        return float("nan")
    daily = prices.iloc[-1] - prices.iloc[-2]
    advancers = int((daily > 0).sum())
    decliners = int((daily < 0).sum())
    if decliners == 0:
        return float("inf") if advancers > 0 else float("nan")
    return float(advancers / decliners)


def net_new_highs_lows(prices: pd.DataFrame, lookback_days: int) -> dict[str, int]:
    """Count of constituents at N-day highs vs lows, latest bar."""
    if prices is None or len(prices) < lookback_days:
        return {"new_highs": 0, "new_lows": 0, "net": 0}
    window = prices.tail(lookback_days)
    last = prices.iloc[-1]
    highs = int((last >= window.max()).sum())
    lows = int((last <= window.min()).sum())
    return {"new_highs": highs, "new_lows": lows, "net": highs - lows}


def compute_breadth(prices: pd.DataFrame, breadth_cfg: dict[str, Any]) -> dict[str, Any]:
    """Bundle the three breadth readings into a single dict for the UI."""
    return {
        "pct_above_ma": percent_above_ma(prices, int(breadth_cfg["ma_period"])),
        "adv_decl_ratio": advance_decline_ratio(prices),
        "new_highs_lows": net_new_highs_lows(prices, int(breadth_cfg["lookback_days"])),
    }
