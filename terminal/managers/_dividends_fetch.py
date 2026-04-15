"""Fetch dividend history and stats from yfinance. Never raises."""

from __future__ import annotations

import math
from functools import lru_cache

import pandas as pd

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


def fetch_dividends(ticker: str) -> dict:
    """Return dividend history Series and key stats for *ticker*."""
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker, session=_session())
        divs = tk.dividends
        info = tk.info or {}
    except Exception:
        return {"dividends": pd.Series(dtype=float), "stats": {}}
    if divs is None or divs.empty:
        return {"dividends": pd.Series(dtype=float), "stats": {}}
    ex_date = info.get("exDividendDate")
    ex_str = ""
    if ex_date is not None:
        try:
            from datetime import datetime
            ex_str = datetime.fromtimestamp(int(ex_date)).strftime("%Y-%m-%d")
        except Exception:
            ex_str = str(ex_date)[:10]
    stats = {
        "dividend_yield": _safe_float(info.get("dividendYield")),
        "payout_ratio": _safe_float(info.get("payoutRatio")),
        "ex_dividend_date": ex_str,
    }
    return {"dividends": divs, "stats": stats}
