"""Unit tests for the M&A comps adapter (P4 wrapper)."""

from __future__ import annotations

from terminal.adapters.ma_comps_adapter import (
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
