"""M&A comps adapter (wraps P4 M&A Database).

v1 provides a lightweight in-memory query interface over a small synthetic
deal table. No full DB rebuild. The Comps & Relative Value workspace
uses this to surface relevant deal multiples in a sector.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


SOURCE_PROJECT = "P4: M&A Database"
SIMPLIFICATIONS = ["Query interface only", "No full DB rebuild", "Embedded synthetic seed when no DB present"]


# Minimal embedded seed so the page renders with no external DB file.
SEED_DEALS: list[dict[str, Any]] = [
    {"target": "ExampleCo A", "sector": "Technology", "year": 2024, "ev_usd": 1.2e9, "ev_ebitda": 14.5, "sponsor": "SponsorX"},
    {"target": "ExampleCo B", "sector": "Technology", "year": 2023, "ev_usd": 850e6, "ev_ebitda": 12.0, "sponsor": "SponsorY"},
    {"target": "ExampleCo C", "sector": "Industrials", "year": 2024, "ev_usd": 2.4e9, "ev_ebitda": 9.1, "sponsor": "StrategicZ"},
    {"target": "ExampleCo D", "sector": "Healthcare", "year": 2023, "ev_usd": 1.8e9, "ev_ebitda": 13.8, "sponsor": "SponsorX"},
    {"target": "ExampleCo E", "sector": "Consumer", "year": 2024, "ev_usd": 600e6, "ev_ebitda": 10.5, "sponsor": "SponsorW"},
    {"target": "ExampleCo F", "sector": "Technology", "year": 2022, "ev_usd": 3.1e9, "ev_ebitda": 16.2, "sponsor": "StrategicZ"},
    {"target": "ExampleCo G", "sector": "Financials", "year": 2024, "ev_usd": 950e6, "ev_ebitda": 8.4, "sponsor": "SponsorY"},
    {"target": "ExampleCo H", "sector": "Industrials", "year": 2023, "ev_usd": 1.5e9, "ev_ebitda": 10.2, "sponsor": "SponsorW"},
]


def load_deals(project_root: Path | None = None) -> pd.DataFrame:
    """Load the deal table from CSV if present, else fall back to seed data."""
    if project_root is not None:
        csv_path = project_root / "data" / "raw" / "ma_deals.csv"
        if csv_path.exists():
            try:
                return pd.read_csv(csv_path)
            except Exception:
                pass
    return pd.DataFrame(SEED_DEALS)


def query_sector_comps(deals: pd.DataFrame, sector: str, max_rows: int = 10) -> pd.DataFrame:
    """Return the most recent deals in the given sector, sorted by year."""
    if deals.empty:
        return deals
    if sector:
        filtered = deals[deals["sector"].str.lower() == sector.lower()]
        if filtered.empty:
            filtered = deals
    else:
        filtered = deals
    return filtered.sort_values("year", ascending=False).head(max_rows).reset_index(drop=True)


def sector_summary(deals: pd.DataFrame) -> dict[str, Any]:
    """Median EV/EBITDA and deal count per sector for the page header."""
    if deals.empty:
        return {}
    by_sector = deals.groupby("sector").agg(
        median_ev_ebitda=("ev_ebitda", "median"),
        deal_count=("target", "count"),
        median_ev_usd=("ev_usd", "median"),
    ).reset_index()
    return {row["sector"]: row.to_dict() for _, row in by_sector.iterrows()}


def run_comps(sector: str, project_root: Path | None = None, max_rows: int = 10) -> dict[str, Any]:
    deals = load_deals(project_root)
    return {
        "status": "success",
        "source_project": SOURCE_PROJECT,
        "comps_table": query_sector_comps(deals, sector, max_rows),
        "sector_summary": sector_summary(deals),
    }
