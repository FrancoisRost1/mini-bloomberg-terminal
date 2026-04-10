"""Unit tests for the FMP provider.

No network calls. Monkeypatches requests.get to return canned payloads
matching the documented FMP response shapes. Verifies parser correctness,
schema normalization, and the rate limit retry path.
"""

from __future__ import annotations

import copy

import pytest

from terminal.data.provider_fmp import FMPProvider


@pytest.fixture
def provider(config, monkeypatch):
    cfg = copy.deepcopy(config)
    monkeypatch.setenv("FMP_API_KEY", "test_key")
    return FMPProvider(cfg)


def _resp(payload, status=200):
    class Resp:
        status_code = status

        def raise_for_status(self):
            if status >= 400:
                raise RuntimeError(f"HTTP {status}")

        def json(self):
            return payload

    return Resp()


def test_get_prices_parses_historical(provider, monkeypatch):
    payload = {
        "symbol": "AAPL",
        "historical": [
            {"date": "2024-01-02", "open": 185, "high": 186, "low": 184, "close": 185.5, "adjClose": 185.5, "volume": 1_000_000},
            {"date": "2024-01-03", "open": 186, "high": 187, "low": 185, "close": 186.5, "adjClose": 186.5, "volume": 1_100_000},
        ],
    }
    monkeypatch.setattr("terminal.data._fmp_http.requests.get", lambda *a, **k: _resp(payload))
    result = provider.get_prices("AAPL", period="1mo")
    assert not result.is_empty()
    assert result.last_close() == 186.5
    assert "open" in result.prices.columns
    assert "adj_close" in result.prices.columns


def test_get_fundamentals_builds_ratios(provider, monkeypatch):
    profile = [{"sector": "Technology", "industry": "Software", "mktCap": 3.0e12, "beta": 1.25, "lastDiv": 0.96}]
    quote = [{"price": 200.0, "pe": 28.5}]
    income = [
        {"date": "2022-12-31", "revenue": 380e9, "ebitda": 130e9, "operatingIncome": 110e9, "interestExpense": 3e9, "netIncome": 95e9},
        {"date": "2023-12-31", "revenue": 410e9, "ebitda": 145e9, "operatingIncome": 120e9, "interestExpense": 3.2e9, "netIncome": 100e9},
    ]
    balance = [
        {"date": "2022-12-31", "totalDebt": 110e9, "cashAndCashEquivalents": 60e9, "totalStockholdersEquity": 60e9},
        {"date": "2023-12-31", "totalDebt": 105e9, "cashAndCashEquivalents": 65e9, "totalStockholdersEquity": 70e9},
    ]
    cashflow = [
        {"date": "2022-12-31", "operatingCashFlow": 120e9, "capitalExpenditure": -10e9},
        {"date": "2023-12-31", "operatingCashFlow": 130e9, "capitalExpenditure": -11e9},
    ]
    payloads = iter([profile, quote, income, balance, cashflow])
    monkeypatch.setattr("terminal.data._fmp_http.requests.get", lambda *a, **k: _resp(next(payloads)))
    result = provider.get_fundamentals("AAPL")
    assert result.has_financials()
    assert result.sector == "Technology"
    assert result.market_cap == 3.0e12
    ratios = result.key_ratios
    # Sanity-check core ratios are populated and inside reasonable bands.
    assert ratios["pe_ratio"] == 28.5
    assert 0 < ratios["ebitda_margin"] < 1
    assert ratios["roe"] > 0
    assert "interest_coverage" in ratios
    assert "fcf_conversion" in ratios
    assert "ev_ebitda" in ratios
    assert "net_debt_ebitda" in ratios
    assert "revenue_growth" in ratios


def test_rate_limit_retries_on_429(provider, monkeypatch):
    state = {"calls": 0}

    def fake_get(*a, **k):
        state["calls"] += 1
        if state["calls"] < 3:
            return _resp({"error": "rate limit"}, status=429)
        return _resp({"historical": []})

    monkeypatch.setattr("terminal.data._fmp_http.requests.get", fake_get)
    monkeypatch.setattr("terminal.data._fmp_http.time.sleep", lambda *_: None)
    provider.http.request("v3/historical-price-full/AAPL")
    assert state["calls"] == 3


def test_missing_key_raises(config):
    cfg = copy.deepcopy(config)
    p = FMPProvider(cfg)
    p.http.api_key = ""
    with pytest.raises(RuntimeError, match="FMP_API_KEY"):
        p.http.request("v3/quote/AAPL")


def test_options_endpoint_403_disables_capability(provider, monkeypatch):
    """Bug 9 regression: a 403 on options must flip supports_options_chain to False."""
    def fake_get(*a, **k):
        return _resp({}, status=403)
    monkeypatch.setattr("terminal.data._fmp_http.requests.get", fake_get)
    assert provider.supports_options_chain() is True
    chain = provider.get_options_chain("AAPL")
    assert chain.is_empty()
    assert provider.supports_options_chain() is False


def test_options_chain_empty_when_endpoint_fails(provider, monkeypatch):
    def fake_get(*a, **k):
        raise RuntimeError("FMP options not available")

    monkeypatch.setattr("terminal.data._fmp_http.requests.get", fake_get)
    chain = provider.get_options_chain("AAPL")
    assert chain.is_empty()
    assert chain.provider == "fmp"
