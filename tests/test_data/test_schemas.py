"""Unit tests for the normalized data schemas."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from terminal.data.schemas import Fundamentals, MacroData, OptionsChain, PriceData, ProviderError


def _make_price_data(empty: bool = False) -> PriceData:
    if empty:
        df = pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume"])
    else:
        idx = pd.date_range("2024-01-01", periods=3, freq="B")
        df = pd.DataFrame({
            "open": [100, 101, 102], "high": [102, 103, 104], "low": [99, 100, 101],
            "close": [101, 102, 103], "adj_close": [101, 102, 103], "volume": [1000, 1100, 1200],
        }, index=idx)
    return PriceData("TEST", df, "USD", "test_provider", datetime.utcnow(), "1y")


def test_price_data_last_close():
    pd_obj = _make_price_data()
    assert pd_obj.last_close() == 103
    assert not pd_obj.is_empty()


def test_price_data_empty_handling():
    pd_obj = _make_price_data(empty=True)
    assert pd_obj.is_empty()
    assert pd_obj.last_close() != pd_obj.last_close()  # NaN


def test_fundamentals_has_financials_true():
    f = Fundamentals(
        ticker="TEST",
        income_statement=pd.DataFrame({"revenue": [100, 110]}),
        balance_sheet=pd.DataFrame(),
        cash_flow=pd.DataFrame(),
        key_ratios={"pe_ratio": 15},
        market_cap=1e9,
        sector="Tech",
        industry="SaaS",
        provider="test",
        as_of=datetime.utcnow(),
    )
    assert f.has_financials()


def test_fundamentals_has_financials_false_when_empty():
    f = Fundamentals(
        ticker="TEST", income_statement=pd.DataFrame(), balance_sheet=pd.DataFrame(),
        cash_flow=pd.DataFrame(), key_ratios={}, market_cap=0.0,
        sector="?", industry="?", provider="test", as_of=datetime.utcnow(),
    )
    assert not f.has_financials()


def test_macro_data_latest():
    s = pd.Series([1.0, 2.0, 3.0], index=pd.date_range("2024-01-01", periods=3))
    macro = MacroData(series={"DGS10": s}, provider="fred", as_of=datetime.utcnow())
    assert macro.latest("DGS10") == 3.0
    assert macro.latest("MISSING") != macro.latest("MISSING")  # NaN


def test_options_chain_expiries_sorted():
    chain = OptionsChain(
        ticker="TEST", spot=100.0,
        chains={"2025-06-20": pd.DataFrame({"strike": [100]}), "2025-03-21": pd.DataFrame({"strike": [100]})},
        provider="test", as_of=datetime.utcnow(),
    )
    assert chain.expiries() == ["2025-03-21", "2025-06-20"]
    assert not chain.is_empty()


def test_options_chain_empty():
    chain = OptionsChain("TEST", 0.0, {}, "test", datetime.utcnow())
    assert chain.is_empty()


def test_provider_error_as_dict_round_trip():
    err = ProviderError(provider="av", ticker="AAPL", data_type="prices", reason="429")
    d = err.as_dict()
    assert d["provider"] == "av"
    assert d["ticker"] == "AAPL"
    assert d["data_type"] == "prices"
    assert d["reason"] == "429"
    assert "raised_at" in d
