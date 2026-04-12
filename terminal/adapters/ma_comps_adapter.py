"""M&A comps adapter. Query interface over data/raw/ma_deals.csv (P4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


SOURCE_PROJECT = "P4: M&A Database"
SIMPLIFICATIONS = ["Query interface only", "No full DB rebuild"]


_P4_RENAMES = {
    "target_name": "target", "acquirer_name": "acquirer",
    "sector_name": "sector", "ev_to_ebitda": "ev_ebitda",
}


def _normalize_real_deals(df: pd.DataFrame) -> pd.DataFrame:
    """Map P4 schema onto the terminal's canonical columns."""
    rn = {k: v for k, v in _P4_RENAMES.items() if k in df.columns and v not in df.columns}
    df = df.rename(columns=rn)
    if "enterprise_value" in df.columns and "ev_usd" not in df.columns:
        df = df.rename(columns={"enterprise_value": "ev_usd"})
        df["ev_usd"] = pd.to_numeric(df["ev_usd"], errors="coerce") * 1e6
    if "announcement_date" in df.columns and "year" not in df.columns:
        df["year"] = pd.to_datetime(df["announcement_date"], errors="coerce").dt.year.fillna(0).astype(int)
    if "deal_type" not in df.columns and "acquirer_type" in df.columns:
        df["deal_type"] = df["acquirer_type"]
    # EV/Revenue: compute from EV / target_revenue (73% coverage vs 6% from ev_to_revenue).
    if "ev_revenue" not in df.columns:
        ev = pd.to_numeric(df.get("ev_usd", pd.Series(dtype=float)), errors="coerce")
        rev = pd.to_numeric(df.get("target_revenue", pd.Series(dtype=float)), errors="coerce")
        existing = pd.to_numeric(df.get("ev_to_revenue", pd.Series(dtype=float)), errors="coerce")
        df["ev_revenue"] = existing.combine_first(ev / (rev * 1e6))
    if "premium_pct" not in df.columns and "premium_paid_pct" in df.columns:
        df["premium_pct"] = pd.to_numeric(df["premium_paid_pct"], errors="coerce")
    if "synthetic" not in df.columns:
        df["synthetic"] = False
    return df


def load_deals(project_root: Path | None, allow_synthetic: bool) -> tuple[pd.DataFrame, str]:
    """Return (deals_df, source) where source is csv, synthetic, or missing."""
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
        from ._ma_seed import seed_deals
        return pd.DataFrame(seed_deals()), "synthetic"
    return pd.DataFrame(), "missing"


_DISPLAY_COLS = [
    "year", "target", "acquirer", "sector", "deal_type",
    "ev_usd", "ev_ebitda", "ev_revenue", "premium_pct",
]


def _sector_matches(deal_sector: str, requested: str) -> bool:
    """Strict token-subset sector match. No substring or fuzzy fallback."""
    if not deal_sector or not requested:
        return False
    a = str(deal_sector).strip().lower()
    b = str(requested).strip().lower()
    if a == b:
        return True
    a_tokens = set(a.replace("&", "and").split())
    b_tokens = set(b.replace("&", "and").split())
    if not a_tokens or not b_tokens:
        return False
    return a_tokens.issubset(b_tokens) or b_tokens.issubset(a_tokens)


def query_sector_comps(deals: pd.DataFrame, sector: str, max_rows: int = 10) -> pd.DataFrame:
    """Most recent deals in the sector, sorted by year descending."""
    if deals.empty:
        return deals
    if sector:
        mask = deals["sector"].apply(lambda s: _sector_matches(s, sector))
        filtered = deals[mask]
        # If fewer than 5 deals in the exact sector, broaden to related
        # sectors that share the first token (e.g. "Consumer" matches
        # both "Consumer Staples" and "Consumer Discretionary").
        if len(filtered) < 5:
            first_token = sector.strip().split()[0].lower() if sector.strip() else ""
            if first_token:
                broad = deals["sector"].apply(
                    lambda s: str(s).strip().split()[0].lower() == first_token
                )
                filtered = deals[broad]
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
    """Fraction of rows with a non-null, non-zero value in column."""
    if table.empty or column not in table.columns:
        return 0.0
    s = pd.to_numeric(table[column], errors="coerce")
    return float((s.notna() & (s != 0)).sum()) / float(len(table))


def run_comps(
    sector: str,
    project_root: Path | None = None,
    max_rows: int = 10,
    allow_synthetic: bool = False,
) -> dict[str, Any]:
    """Adapter entry point. Returns status dict with comps_table and coverage."""
    deals, source = load_deals(project_root, allow_synthetic)
    _zero_cov = {"ev_ebitda": 0.0, "ev_revenue": 0.0, "premium_pct": 0.0}
    if source == "missing":
        return {"status": "data_unavailable", "source_project": SOURCE_PROJECT,
                "reason": "ma_deals.csv missing", "comps_table": pd.DataFrame(),
                "sector_summary": {}, "data_source": source, "coverage": _zero_cov}
    comps_table = query_sector_comps(deals, sector, max_rows)
    cov = {f: _coverage(comps_table, f) for f in _zero_cov}
    return {"status": "success", "source_project": SOURCE_PROJECT,
            "comps_table": comps_table, "sector_summary": sector_summary(deals),
            "data_source": source, "coverage": cov}
