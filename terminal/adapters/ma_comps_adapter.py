"""M&A comps adapter (wraps P4 M&A Database).

v1 provides a query interface over a CSV deal table at
``data/raw/ma_deals.csv``. If the CSV is missing, the adapter returns
``status="data_unavailable"`` so the UI surfaces an explicit
DATA UNAVAILABLE state. Synthetic seed data is gated behind
``comps.allow_synthetic_demo: true`` (development only) and is always
labelled SYNTHETIC so the page can warn the user.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


SOURCE_PROJECT = "P4: M&A Database"
SIMPLIFICATIONS = ["Query interface only", "No full DB rebuild"]


# Synthetic seed dataset, used ONLY in dev mode when explicitly
# allowed by config. Every row is labelled SYNTHETIC so the UI can
# warn the user. Production never serves this.
SEED_DEALS: list[dict[str, Any]] = [
    {"target": "SYNTHETIC ExampleCo A", "sector": "Technology", "year": 2024, "ev_usd": 1.2e9, "ev_ebitda": 14.5, "sponsor": "SponsorX", "synthetic": True},
    {"target": "SYNTHETIC ExampleCo B", "sector": "Technology", "year": 2023, "ev_usd": 850e6, "ev_ebitda": 12.0, "sponsor": "SponsorY", "synthetic": True},
    {"target": "SYNTHETIC ExampleCo C", "sector": "Industrials", "year": 2024, "ev_usd": 2.4e9, "ev_ebitda": 9.1, "sponsor": "StrategicZ", "synthetic": True},
    {"target": "SYNTHETIC ExampleCo D", "sector": "Healthcare", "year": 2023, "ev_usd": 1.8e9, "ev_ebitda": 13.8, "sponsor": "SponsorX", "synthetic": True},
    {"target": "SYNTHETIC ExampleCo E", "sector": "Consumer", "year": 2024, "ev_usd": 600e6, "ev_ebitda": 10.5, "sponsor": "SponsorW", "synthetic": True},
    {"target": "SYNTHETIC ExampleCo F", "sector": "Technology", "year": 2022, "ev_usd": 3.1e9, "ev_ebitda": 16.2, "sponsor": "StrategicZ", "synthetic": True},
    {"target": "SYNTHETIC ExampleCo G", "sector": "Financials", "year": 2024, "ev_usd": 950e6, "ev_ebitda": 8.4, "sponsor": "SponsorY", "synthetic": True},
    {"target": "SYNTHETIC ExampleCo H", "sector": "Industrials", "year": 2023, "ev_usd": 1.5e9, "ev_ebitda": 10.2, "sponsor": "SponsorW", "synthetic": True},
]


def load_deals(project_root: Path | None, allow_synthetic: bool) -> tuple[pd.DataFrame, str]:
    """Return ``(deals_df, source)`` where source is ``csv``, ``synthetic``, or ``missing``.

    The caller decides what to do with each source. Production calls
    with ``allow_synthetic=False`` and treats ``missing`` as a hard
    DATA UNAVAILABLE state.
    """
    if project_root is not None:
        csv_path = project_root / "data" / "raw" / "ma_deals.csv"
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                if "synthetic" not in df.columns:
                    df["synthetic"] = False
                return df, "csv"
            except Exception:
                pass
    if allow_synthetic:
        return pd.DataFrame(SEED_DEALS), "synthetic"
    return pd.DataFrame(), "missing"


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


def run_comps(
    sector: str,
    project_root: Path | None = None,
    max_rows: int = 10,
    allow_synthetic: bool = False,
) -> dict[str, Any]:
    """Adapter entry point. Returns standardized status dict."""
    deals, source = load_deals(project_root, allow_synthetic)
    if source == "missing":
        return {
            "status": "data_unavailable",
            "source_project": SOURCE_PROJECT,
            "reason": "ma_deals.csv not present and synthetic data is disabled",
            "comps_table": pd.DataFrame(),
            "sector_summary": {},
            "data_source": source,
        }
    return {
        "status": "success",
        "source_project": SOURCE_PROJECT,
        "comps_table": query_sector_comps(deals, sector, max_rows),
        "sector_summary": sector_summary(deals),
        "data_source": source,
    }
