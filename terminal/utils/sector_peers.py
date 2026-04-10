"""Hardcoded sector to peer map for the Comps page.

The user requested either an FMP stock-peers fetch or a hardcoded
top-5 by market cap per sector. Hardcoding is preferable here: it
avoids an extra FMP call per render, it stays stable across rate
limit windows, and the relevant universe of mega caps changes slowly.

Sector keys match the strings FMP returns in ``profile.sector``.
"""

from __future__ import annotations


SECTOR_PEERS: dict[str, list[str]] = {
    "Technology":              ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "Communication Services":  ["GOOGL", "META", "NFLX", "DIS", "CMCSA"],
    "Consumer Cyclical":       ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "Consumer Defensive":      ["WMT", "PG", "KO", "PEP", "COST"],
    "Healthcare":              ["UNH", "JNJ", "LLY", "MRK", "ABBV"],
    "Health Care":             ["UNH", "JNJ", "LLY", "MRK", "ABBV"],
    "Financial Services":      ["JPM", "BAC", "WFC", "GS", "MS"],
    "Financials":              ["JPM", "BAC", "WFC", "GS", "MS"],
    "Energy":                  ["XOM", "CVX", "COP", "EOG", "SLB"],
    "Industrials":             ["GE", "CAT", "BA", "HON", "UNP"],
    "Basic Materials":         ["LIN", "SHW", "FCX", "NEM", "DOW"],
    "Materials":               ["LIN", "SHW", "FCX", "NEM", "DOW"],
    "Real Estate":             ["PLD", "AMT", "EQIX", "WELL", "SPG"],
    "Utilities":               ["NEE", "DUK", "SO", "AEP", "D"],
}


def peers_for(sector: str | None, active_ticker: str, limit: int = 5) -> list[str]:
    """Return up to ``limit`` peers for the given sector, including the
    active ticker as the first entry. Falls back to the Technology
    bucket if the sector is unknown so the page never renders empty.
    """
    base = SECTOR_PEERS.get((sector or "").strip(), SECTOR_PEERS["Technology"])
    out: list[str] = [active_ticker.upper()]
    for t in base:
        if t.upper() == active_ticker.upper():
            continue
        out.append(t)
        if len(out) >= limit:
            break
    return out
