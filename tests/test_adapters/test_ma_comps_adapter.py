"""Unit tests for the M&A comps adapter (P4 wrapper)."""

from __future__ import annotations

from terminal.adapters.ma_comps_adapter import load_deals, query_sector_comps, run_comps, sector_summary


def test_seed_deals_load():
    deals = load_deals(project_root=None)
    assert not deals.empty
    assert "sector" in deals.columns
    assert "ev_ebitda" in deals.columns


def test_query_sector_filters():
    deals = load_deals()
    tech = query_sector_comps(deals, sector="Technology", max_rows=10)
    assert not tech.empty
    assert (tech["sector"].str.lower() == "technology").all()


def test_query_sector_sorted_by_year():
    deals = load_deals()
    tech = query_sector_comps(deals, sector="Technology")
    years = tech["year"].tolist()
    assert years == sorted(years, reverse=True)


def test_query_unknown_sector_falls_back():
    deals = load_deals()
    result = query_sector_comps(deals, sector="ZZZ_NOT_A_SECTOR")
    assert not result.empty


def test_sector_summary_structure():
    deals = load_deals()
    summary = sector_summary(deals)
    for _, row in summary.items():
        assert "median_ev_ebitda" in row
        assert "deal_count" in row


def test_run_comps_returns_status():
    result = run_comps(sector="Technology", project_root=None)
    assert result["status"] == "success"
    assert "comps_table" in result
    assert "sector_summary" in result
