"""Fetch ticker news from yfinance.

Returns a normalized list of dicts with keys: title, publisher, link,
published. Never raises -- returns an empty list on any failure.
"""

from __future__ import annotations


def _extract_url(content: dict) -> str:
    """Pull a usable URL from the nested yfinance news content dict."""
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
    """Fetch recent news articles for *ticker* via yfinance."""
    try:
        import yfinance as yf
        raw = yf.Ticker(ticker).news or []
    except Exception:
        return []
    articles: list[dict] = []
    for item in raw[:count]:
        c = item.get("content") or item
        provider = c.get("provider") or {}
        pub_name = provider.get("displayName", "") if isinstance(provider, dict) else str(provider)
        articles.append({
            "title": c.get("title", ""),
            "publisher": pub_name,
            "link": _extract_url(c),
            "published": c.get("pubDate", ""),
        })
    return articles
