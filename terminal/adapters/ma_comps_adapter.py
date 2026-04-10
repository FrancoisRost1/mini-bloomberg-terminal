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


def _normalize_real_deals(df: pd.DataFrame) -> pd.DataFrame:
    """Map the P4 (ma-database) schema onto the terminal's canonical columns.

    The real_deals CSV from Project 4 uses target_name / acquirer_name /
    sector_name / announcement_date / ev_to_ebitda / enterprise_value /
    acquirer_type etc. The terminal comps table expects target, acquirer,
    sector, year, ev_ebitda, ev_usd, deal_type. This function is a pure
    projection + rename so the adapter stays agnostic of Project 4's
    storage format.
    """
    if "target_name" in df.columns and "target" not in df.columns:
        df = df.rename(columns={"target_name": "target"})
    if "acquirer_name" in df.columns and "acquirer" not in df.columns:
        df = df.rename(columns={"acquirer_name": "acquirer"})
    if "sector_name" in df.columns and "sector" not in df.columns:
        df = df.rename(columns={"sector_name": "sector"})
    if "ev_to_ebitda" in df.columns and "ev_ebitda" not in df.columns:
        df = df.rename(columns={"ev_to_ebitda": "ev_ebitda"})
    if "enterprise_value" in df.columns and "ev_usd" not in df.columns:
        # ma-database stores EV in USD millions; terminal expects USD. Scale up.
        df = df.rename(columns={"enterprise_value": "ev_usd"})
        df["ev_usd"] = pd.to_numeric(df["ev_usd"], errors="coerce") * 1e6
    if "announcement_date" in df.columns and "year" not in df.columns:
        years = pd.to_datetime(df["announcement_date"], errors="coerce").dt.year
        df["year"] = years.fillna(0).astype(int)
    if "deal_type" not in df.columns and "acquirer_type" in df.columns:
        df["deal_type"] = df["acquirer_type"]
    if "synthetic" not in df.columns:
        df["synthetic"] = False
    return df


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
                df = _normalize_real_deals(df)
                return df, "csv"
            except Exception:
                pass
    if allow_synthetic:
        return pd.DataFrame(SEED_DEALS), "synthetic"
    return pd.DataFrame(), "missing"


_DISPLAY_COLS = ["year", "target", "acquirer", "sector", "deal_type", "ev_usd", "ev_ebitda"]


def query_sector_comps(deals: pd.DataFrame, sector: str, max_rows: int = 10) -> pd.DataFrame:
    """Return the most recent deals in the given sector, sorted by year.

    Only the small projection of columns the terminal UI actually
    renders is returned, so the page stays focused (year, target,
    acquirer, sector, deal_type, EV $, EV/EBITDA).
    """
    if deals.empty:
        return deals
    if sector:
        filtered = deals[deals["sector"].str.lower() == sector.lower()]
        if filtered.empty:
            filtered = deals
    else:
        filtered = deals
    filtered = filtered.sort_values("year", ascending=False).head(max_rows).reset_index(drop=True)
    cols = [c for c in _DISPLAY_COLS if c in filtered.columns]
    return filtered[cols]


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


def _coverage(table: pd.DataFrame, column: str) -> float:
    """Fraction of rows in ``table`` with a non-null, non-zero value
    in ``column``. Returns 0.0 if the column is missing entirely."""
    if table.empty or column not in table.columns:
        return 0.0
    s = pd.to_numeric(table[column], errors="coerce")
    present = s.notna() & (s != 0)
    return float(present.sum()) / float(len(table))


def run_comps(
    sector: str,
    project_root: Path | None = None,
    max_rows: int = 10,
    allow_synthetic: bool = False,
) -> dict[str, Any]:
    """Adapter entry point. Returns standardized status dict.

    Also reports coverage of the EV/EBITDA column on the returned
    slice so the UI can warn when most deals lack the metric (the
    public M&A dataset often does not disclose it).
    """
    deals, source = load_deals(project_root, allow_synthetic)
    if source == "missing":
        return {
            "status": "data_unavailable",
            "source_project": SOURCE_PROJECT,
            "reason": "ma_deals.csv not present and synthetic data is disabled",
            "comps_table": pd.DataFrame(),
            "sector_summary": {},
            "data_source": source,
            "coverage": {"ev_ebitda": 0.0},
        }
    comps_table = query_sector_comps(deals, sector, max_rows)
    return {
        "status": "success",
        "source_project": SOURCE_PROJECT,
        "comps_table": comps_table,
        "sector_summary": sector_summary(deals),
        "data_source": source,
        "coverage": {"ev_ebitda": _coverage(comps_table, "ev_ebitda")},
    }
