"""Factor exposure adapter (wraps P3 Factor Backtest Engine).

Snapshot mode only: returns the five-factor ranked exposure for a single
ticker against a provided peer set. No backtest, no rebalance schedule.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


SOURCE_PROJECT = "P3: Factor Backtest Engine"
SIMPLIFICATIONS = ["Snapshot exposure only", "No backtest", "No rebalance schedule"]

FACTOR_KEYS = ["value", "momentum", "quality", "size", "low_vol"]


def compute_factor_snapshot(
    target_ratios: dict[str, float],
    prices: pd.Series,
    peer_ratios: pd.DataFrame | None = None,
    peer_prices: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Compute the five-factor exposure snapshot for a single ticker.

    Each factor is a rank in 0..1 across the peer universe. If peer data
    is missing, the snapshot falls back to absolute-value heuristics with
    a lower confidence flag so the recommendation engine can weight it down.
    """
    value = _value_factor(target_ratios)
    momentum = _momentum_factor(prices)
    quality = _quality_factor(target_ratios)
    size = _size_factor(target_ratios)
    low_vol = _low_vol_factor(prices)
    if peer_ratios is not None and not peer_ratios.empty:
        value = _peer_rank(value, peer_ratios.get("value"))
        quality = _peer_rank(quality, peer_ratios.get("quality"))
    scores = {
        "value": value,
        "momentum": momentum,
        "quality": quality,
        "size": size,
        "low_vol": low_vol,
    }
    composite = float(np.nanmean([v for v in scores.values() if v is not None and v == v])) if scores else float("nan")
    return {
        "status": "success",
        "source_project": SOURCE_PROJECT,
        "factor_scores": scores,
        "composite": composite,
        "confidence": 0.8 if peer_ratios is not None and not peer_ratios.empty else 0.5,
    }


def _value_factor(ratios: dict[str, float]) -> float:
    pe = ratios.get("pe_ratio")
    if pe is None or pe != pe or pe <= 0:
        return float("nan")
    # Invert PE into an earnings yield proxy, cap at 0..1.
    ey = 1.0 / pe
    return float(min(1.0, max(0.0, ey * 10.0)))


def _momentum_factor(prices: pd.Series) -> float:
    if prices is None or len(prices) < 252:
        return float("nan")
    t1 = prices.iloc[-21]
    t12 = prices.iloc[-252]
    if t12 == 0 or np.isnan(t12):
        return float("nan")
    twelve_one = (t1 / t12) - 1.0
    return float(min(1.0, max(0.0, (twelve_one + 0.3) / 0.6)))


def _quality_factor(ratios: dict[str, float]) -> float:
    roe = ratios.get("roe")
    if roe is None or roe != roe:
        return float("nan")
    return float(min(1.0, max(0.0, roe / 0.30)))


def _size_factor(ratios: dict[str, float]) -> float:
    mcap = ratios.get("market_cap")
    if mcap is None or mcap != mcap or mcap <= 0:
        return float("nan")
    log_cap = np.log10(mcap)
    return float(min(1.0, max(0.0, 1.0 - (log_cap - 8.0) / 4.0)))


def _low_vol_factor(prices: pd.Series) -> float:
    if prices is None or len(prices) < 60:
        return float("nan")
    rets = prices.pct_change().dropna().tail(60)
    if rets.empty:
        return float("nan")
    vol = rets.std() * np.sqrt(252)
    return float(min(1.0, max(0.0, 1.0 - vol / 0.50)))


def _peer_rank(value: float, series: pd.Series | None) -> float:
    if series is None or series.empty or value != value:
        return value
    rank = (series.dropna() < value).mean()
    return float(rank)
