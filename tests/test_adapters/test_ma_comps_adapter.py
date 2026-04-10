"""Unit tests for the M&A comps adapter (P4 wrapper)."""

from __future__ import annotations

import pandas as pd

from terminal.adapters.ma_comps_adapter import (
    _normalize_real_deals,
    load_deals,
    query_sector_comps,
    run_comps,
    sector_summary,
)


def test_seed_deals_loaded_only_when_synthetic_allowed():
    """Bug 9 regression: production must NOT serve synthetic data."""
    deals_prod, source_prod = load_deals(project_root=None, allow_synthetic=False)
    assert deals_prod.empty
    assert source_prod == "missing"
    deals_dev, source_dev = load_deals(project_root=None, allow_synthetic=True)
    assert not deals_dev.empty
    assert source_dev == "synthetic"
    # Every synthetic row must be flagged.
    assert deals_dev["synthetic"].all()


def test_seed_target_names_flagged():
    deals, _ = load_deals(project_root=None, allow_synthetic=True)
    assert deals["target"].str.startswith("SYNTHETIC").all()


def test_query_sector_filters():
    deals, _ = load_deals(project_root=None, allow_synthetic=True)
    tech = query_sector_comps(deals, sector="Technology", max_rows=10)
    assert not tech.empty
    assert (tech["sector"].str.lower() == "technology").all()


def test_query_sector_sorted_by_year():
    deals, _ = load_deals(project_root=None, allow_synthetic=True)
    tech = query_sector_comps(deals, sector="Technology")
    years = tech["year"].tolist()
    assert years == sorted(years, reverse=True)


def test_sector_summary_structure():
    deals, _ = load_deals(project_root=None, allow_synthetic=True)
    summary = sector_summary(deals)
    for _, row in summary.items():
        assert "median_ev_ebitda" in row
        assert "deal_count" in row


def test_run_comps_production_returns_data_unavailable():
    """Production (no CSV, no synthetic) must surface data_unavailable."""
    result = run_comps(sector="Technology", project_root=None, allow_synthetic=False)
    assert result["status"] == "data_unavailable"
    assert "ma_deals.csv" in result["reason"]
    assert result["comps_table"].empty


def test_run_comps_dev_with_synthetic_returns_success():
    result = run_comps(sector="Technology", project_root=None, allow_synthetic=True)
    assert result["status"] == "success"
    assert result["data_source"] == "synthetic"
    assert not result["comps_table"].empty


def test_normalize_real_deals_maps_p4_schema():
    """Project 4 (ma-database) stores EV in USD millions with
    target_name / acquirer_name / sector_name / ev_to_ebitda. The
    normalizer must project these onto the terminal's canonical
    column names and scale the EV to full USD."""
    raw = pd.DataFrame([
        {
            "target_name": "LinkedIn",
            "acquirer_name": "Microsoft",
            "acquirer_type": "strategic",
            "announcement_date": "2016-06-13",
            "enterprise_value": 26200,  # USD millions
            "ev_to_ebitda": 15.5,
            "sector_name": "Technology",
        },
    ])
    normalized = _normalize_real_deals(raw)
    assert "target" in normalized.columns
    assert "acquirer" in normalized.columns
    assert "sector" in normalized.columns
    assert "ev_ebitda" in normalized.columns
    assert "ev_usd" in normalized.columns
    assert "year" in normalized.columns
    assert "deal_type" in normalized.columns
    row = normalized.iloc[0]
    assert row["target"] == "LinkedIn"
    assert row["acquirer"] == "Microsoft"
    assert row["sector"] == "Technology"
    assert row["year"] == 2016
    assert row["ev_ebitda"] == 15.5
    # 26200 million * 1e6 = 2.62e10 in USD
    assert row["ev_usd"] == 26200 * 1e6
    assert row["synthetic"] is False or row["synthetic"] == False  # noqa: E712


def test_query_sector_comps_returns_only_display_cols():
    raw = pd.DataFrame([
        {"target": "A", "acquirer": "B", "sector": "Technology", "year": 2024,
         "ev_usd": 1.0e9, "ev_ebitda": 12.0, "deal_type": "strategic",
         "notes": "should not appear", "synthetic": False},
    ])
    out = query_sector_comps(raw, sector="Technology")
    assert "notes" not in out.columns
    assert set(out.columns).issubset(
        {"year", "target", "acquirer", "sector", "deal_type", "ev_usd", "ev_ebitda"})
