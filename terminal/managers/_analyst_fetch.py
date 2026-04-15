"""Fetch analyst consensus data from yfinance.

Returns a dict with target prices, analyst count, and consensus
recommendation. Never raises -- returns an empty dict on failure.
"""

from __future__ import annotations

from functools import lru_cache

from terminal.data._yfinance_session import get_hardened_session


@lru_cache(maxsize=1)
def _session():
    return get_hardened_session()


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
        info = yf.Ticker(ticker, session=_session()).info or {}
    except Exception:
        return {}
    result: dict = {}
    for k in _KEYS:
        val = info.get(k)
        if val is not None:
            result[k] = val
    return result
