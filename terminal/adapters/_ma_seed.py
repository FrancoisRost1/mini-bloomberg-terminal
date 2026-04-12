"""Synthetic M&A seed deals. Dev mode only, gated by config."""

from __future__ import annotations

from typing import Any


def seed_deals() -> list[dict[str, Any]]:
    """8 synthetic deals for development mode demo."""
    _s = True
    return [
        {"target": "SYNTHETIC A", "sector": "Technology", "year": 2024, "ev_usd": 1.2e9, "ev_ebitda": 14.5, "sponsor": "SponsorX", "synthetic": _s},
        {"target": "SYNTHETIC B", "sector": "Technology", "year": 2023, "ev_usd": 850e6, "ev_ebitda": 12.0, "sponsor": "SponsorY", "synthetic": _s},
        {"target": "SYNTHETIC C", "sector": "Industrials", "year": 2024, "ev_usd": 2.4e9, "ev_ebitda": 9.1, "sponsor": "StrategicZ", "synthetic": _s},
        {"target": "SYNTHETIC D", "sector": "Healthcare", "year": 2023, "ev_usd": 1.8e9, "ev_ebitda": 13.8, "sponsor": "SponsorX", "synthetic": _s},
        {"target": "SYNTHETIC E", "sector": "Consumer", "year": 2024, "ev_usd": 600e6, "ev_ebitda": 10.5, "sponsor": "SponsorW", "synthetic": _s},
        {"target": "SYNTHETIC F", "sector": "Technology", "year": 2022, "ev_usd": 3.1e9, "ev_ebitda": 16.2, "sponsor": "StrategicZ", "synthetic": _s},
        {"target": "SYNTHETIC G", "sector": "Financials", "year": 2024, "ev_usd": 950e6, "ev_ebitda": 8.4, "sponsor": "SponsorY", "synthetic": _s},
        {"target": "SYNTHETIC H", "sector": "Industrials", "year": 2023, "ev_usd": 1.5e9, "ev_ebitda": 10.2, "sponsor": "SponsorW", "synthetic": _s},
    ]
