"""Fetch ticker news from Finnhub (primary) or yfinance (fallback).

Finnhub returns higher-quality, ticker-specific articles. Falls back
to yfinance when FINNHUB_API_KEY is not set (dev mode). Returns a
normalized list of dicts: {title, publisher, link, published}.
Never raises.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from functools import lru_cache

from terminal.data._yfinance_session import get_hardened_session


@lru_cache(maxsize=1)
def _session():
    return get_hardened_session()


def _finnhub_fetch(ticker: str, count: int) -> list[dict] | None:
    """Try Finnhub company-news endpoint. Returns None if unavailable."""
    key = os.environ.get("FINNHUB_API_KEY", "")
    if not key:
        return None
    try:
        import requests
        to_date = date.today()
        from_date = to_date - timedelta(days=7)
        url = (
            f"https://finnhub.io/api/v1/company-news"
            f"?symbol={ticker}&from={from_date}&to={to_date}&token={key}"
        )
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return None
        raw = r.json()
        if not isinstance(raw, list):
            return None
    except Exception:
        return None
    articles: list[dict] = []
    for item in raw[:count]:
        articles.append({
            "title": item.get("headline", ""),
            "publisher": item.get("source", ""),
            "link": item.get("url", ""),
            "published": _epoch_to_iso(item.get("datetime")),
        })
    return articles


def _epoch_to_iso(epoch) -> str:
    """Convert a Unix timestamp to ISO-8601 string."""
    if not epoch:
        return ""
    try:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()
    except Exception:
        return ""


def _yfinance_fallback(ticker: str, count: int) -> list[dict]:
    """Fallback to yfinance news when Finnhub key is absent."""
    try:
        import yfinance as yf
        raw = yf.Ticker(ticker, session=_session()).news or []
    except Exception:
        return []
    articles: list[dict] = []
    for item in raw[:count]:
        c = item.get("content") or item
        provider = c.get("provider") or {}
        pub = provider.get("displayName", "") if isinstance(provider, dict) else str(provider)
        link = _extract_yf_url(c)
        articles.append({
            "title": c.get("title", ""),
            "publisher": pub,
            "link": link,
            "published": c.get("pubDate", ""),
        })
    return articles


def _extract_yf_url(content: dict) -> str:
    for key in ("canonicalUrl", "clickThroughUrl"):
        val = content.get(key)
        if isinstance(val, dict):
            url = val.get("url", "")
            if url:
                return url
        elif isinstance(val, str) and val:
            return val
    return ""


def fetch_news(ticker: str, count: int = 8) -> list[dict]:
    """Fetch recent news. Finnhub first, yfinance fallback."""
    result = _finnhub_fetch(ticker, count)
    if result is not None:
        return result
    return _yfinance_fallback(ticker, count)
