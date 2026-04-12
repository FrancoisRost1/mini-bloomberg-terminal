"""Fetch short interest data from yfinance ticker.info.

Returns shortPercentOfFloat, shortRatio (days to cover), and
sharesShort. Never raises.
"""

from __future__ import annotations

import math


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


def fetch_short_interest(ticker: str) -> dict:
    """Return short interest metrics for *ticker*."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return {}
    return {
        "short_pct_float": _safe_float(info.get("shortPercentOfFloat")),
        "short_ratio": _safe_float(info.get("shortRatio")),
        "shares_short": _safe_float(info.get("sharesShort")),
    }
