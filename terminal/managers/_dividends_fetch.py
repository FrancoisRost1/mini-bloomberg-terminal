"""Fetch dividend history and stats from yfinance. Never raises."""

from __future__ import annotations

import math

import pandas as pd


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
        tk = yf.Ticker(ticker)
        divs = tk.dividends
        info = tk.info or {}
    except Exception:
        return {"dividends": pd.Series(dtype=float), "stats": {}}
    # Fallback: if the dividends shortcut returned nothing or very little,
    # try pulling the full price history and extracting the Dividends column.
    # Some yfinance builds return stale/truncated series via tk.dividends
    # but give full history via tk.history(period="max").
    if divs is None or divs.empty or len(divs) < 8:
        try:
            hist = tk.history(period="max", auto_adjust=False)
            if hist is not None and "Dividends" in hist.columns:
                full = hist["Dividends"]
                full = full[full > 0]
                if not full.empty and (divs is None or len(full) > len(divs)):
                    divs = full
        except Exception:
            pass
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
