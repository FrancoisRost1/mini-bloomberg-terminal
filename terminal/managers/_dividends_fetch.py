"""Fetch dividend history from yfinance. Never raises."""

from __future__ import annotations

import pandas as pd


def fetch_dividends(ticker: str) -> dict:
    """Return dividend history Series for *ticker*."""
    try:
        import yfinance as yf
        divs = yf.Ticker(ticker).dividends
    except Exception:
        return {"dividends": pd.Series(dtype=float)}
    if divs is None or divs.empty:
        return {"dividends": pd.Series(dtype=float)}
    return {"dividends": divs}
