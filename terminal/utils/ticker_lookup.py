"""Ticker suggestion engine for the search bar.

Lightweight edit-distance + name-substring matching against a static
S&P 500 / NASDAQ 100 ticker list. No external packages required.
"""

from __future__ import annotations

from ._ticker_symbols import TICKERS


def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein distance between two strings."""
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def suggest_ticker(query: str, max_results: int = 3) -> list[str]:
    """Return up to *max_results* ticker suggestions for *query*.

    Matching strategy (scored by priority):
    1. Exact ticker match (query is already valid).
    2. Ticker prefix match (query is a prefix of a known ticker).
    3. Edit distance <= 2 on the ticker symbol.
    4. Case-insensitive substring on company name.
    """
    if not query or not query.strip():
        return []
    q = query.strip().upper()
    q_lower = query.strip().lower()

    # Exact match: no suggestions needed.
    if q in TICKERS:
        return []

    scored: list[tuple[int, int, str]] = []
    for ticker, name in TICKERS.items():
        # Tiebreaker: more shared characters = better match.
        common = -len(set(q) & set(ticker))
        # Priority 1: prefix match on ticker symbol.
        if ticker.startswith(q):
            scored.append((0, common, ticker))
            continue
        # Priority 2: edit distance on ticker.
        dist = _levenshtein(q, ticker)
        if dist <= 2:
            scored.append((dist, common, ticker))
            continue
        # Priority 3: substring match on company name.
        if q_lower in name.lower():
            scored.append((3, common, ticker))

    scored.sort()
    return [s[2] for s in scored[:max_results]]
