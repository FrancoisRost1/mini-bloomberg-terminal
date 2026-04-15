"""Fetch analyst consensus data from yfinance.

Returns a dict with target prices, analyst count, and consensus
recommendation. Never raises -- returns an empty dict on failure.
"""

from __future__ import annotations

_KEYS = (
    "targetMeanPrice",
    "targetMedianPrice",
    "targetHighPrice",
    "targetLowPrice",
    "numberOfAnalystOpinions",
    "recommendationKey",
    "recommendationMean",
)


def fetch_analyst_data(ticker: str) -> dict:
    """Pull analyst consensus fields from yfinance info dict."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return {}
    result: dict = {}
    for k in _KEYS:
        val = info.get(k)
        if val is not None:
            result[k] = val
    return result
