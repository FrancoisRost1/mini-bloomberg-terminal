"""Fetch short interest data from yfinance ticker.info.

Returns shortPercentOfFloat, shortRatio (days to cover), and
sharesShort. Never raises.
"""

from __future__ import annotations

import math
from functools import lru_cache

from terminal.data._yfinance_session import get_hardened_session


@lru_cache(maxsize=1)
def _session():
    return get_hardened_session()


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
        info = yf.Ticker(ticker, session=_session()).info or {}
    except Exception:
        return {}
    return {
        "short_pct_float": _safe_float(info.get("shortPercentOfFloat")),
        "short_ratio": _safe_float(info.get("shortRatio")),
        "shares_short": _safe_float(info.get("sharesShort")),
    }
