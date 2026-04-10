"""Unit tests for the FMP provider (stable/ endpoints only).

No network calls. Monkeypatches requests.get to return canned payloads
matching the FMP stable/ response shapes. Verifies parser correctness,
schema normalization, and the rate limit retry path. Confirms that
get_options_chain raises NotImplementedError because options are now
served by yfinance, not FMP.
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


def test_supports_options_chain_is_false(provider):
    """FMP Starter never serves options. Capability flag is False."""
    assert provider.supports_options_chain() is False


def test_get_options_chain_raises(provider):
    with pytest.raises(NotImplementedError):
        provider.get_options_chain("AAPL")


def test_get_prices_parses_stable_flat_list(provider, monkeypatch):
    """stable/historical-price-eod/full returns a flat list of bars."""
    payload = [
        {"symbol": "AAPL", "date": "2024-01-02", "open": 185, "high": 186, "low": 184, "close": 185.5, "volume": 1_000_000},
        {"symbol": "AAPL", "date": "2024-01-03", "open": 186, "high": 187, "low": 185, "close": 186.5, "volume": 1_100_000},
    ]
    monkeypatch.setattr("terminal.data._fmp_http.requests.get", lambda *a, **k: _resp(payload))
    result = provider.get_prices("AAPL", period="1mo")
    assert not result.is_empty()
    assert result.last_close() == 186.5
    assert "open" in result.prices.columns
    assert "adj_close" in result.prices.columns  # parser fills from close when missing


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
    assert ratios["pe_ratio"] == 28.5
    assert 0 < ratios["ebitda_margin"] < 1
    assert ratios["roe"] > 0
    assert "interest_coverage" in ratios
    assert "fcf_conversion" in ratios
    assert "ev_ebitda" in ratios
    assert "net_debt_ebitda" in ratios
    assert "revenue_growth" in ratios


def test_fundamentals_handles_marketCap_alias(provider, monkeypatch):
    """stable/profile may return ``marketCap`` instead of ``mktCap``."""
    profile = [{"sector": "Tech", "industry": "Software", "marketCap": 1.5e12, "beta": 1.0}]
    quote = [{"price": 100.0, "peRatio": 20.0}]
    payloads = iter([profile, quote, [], [], []])
    monkeypatch.setattr("terminal.data._fmp_http.requests.get", lambda *a, **k: _resp(next(payloads)))
    result = provider.get_fundamentals("AAPL")
    assert result.market_cap == 1.5e12
    assert result.key_ratios["pe_ratio"] == 20.0


def test_calls_only_stable_endpoints(provider, monkeypatch):
    """Bug regression: ZERO v3/ calls. Every URL must contain stable/."""
    seen_urls: list[str] = []

    def fake_get(url, params=None, timeout=None):
        seen_urls.append(url)
        return _resp([{"symbol": "AAPL", "date": "2024-01-02", "close": 100, "open": 99, "high": 101, "low": 98, "volume": 1000}])

    monkeypatch.setattr("terminal.data._fmp_http.requests.get", fake_get)
    provider.get_prices("AAPL")
    monkeypatch.setattr("terminal.data._fmp_http.requests.get", lambda *a, **k: _resp([{"symbol": "AAPL", "sector": "T", "industry": "S", "mktCap": 1e12, "beta": 1.0}]))
    provider.get_fundamentals("AAPL")
    assert seen_urls, "no requests were captured"
    for url in seen_urls:
        assert "/stable/" in url, f"non stable endpoint hit: {url}"
        assert "/v3/" not in url, f"v3 endpoint must not be called: {url}"
        # Bug regression: stable endpoints live at /stable/, NOT /api/stable/.
        # If the base URL contains /api the constructed URL is wrong and FMP 403s.
        assert "/api/stable/" not in url, f"wrong base URL: {url}"


def test_url_composition_matches_audit_script(provider, monkeypatch):
    """Hard URL regression. The constructed URL must equal what
    scripts/_fmp_endpoints.py produces, otherwise the audit and the
    runtime hit different surfaces."""
    captured: dict[str, str] = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["symbol"] = (params or {}).get("symbol", "")
        return _resp([{"symbol": "AAPL", "date": "2024-01-02", "close": 100, "open": 99, "high": 101, "low": 98, "volume": 1000}])

    monkeypatch.setattr("terminal.data._fmp_http.requests.get", fake_get)
    provider.get_prices("AAPL")
    assert captured["url"] == "https://financialmodelingprep.com/stable/historical-price-eod/full"
    assert captured["symbol"] == "AAPL"


def test_rate_limit_retries_on_429(provider, monkeypatch):
    state = {"calls": 0}

    def fake_get(*a, **k):
        state["calls"] += 1
        if state["calls"] < 3:
            return _resp({"error": "rate limit"}, status=429)
        return _resp([])

    monkeypatch.setattr("terminal.data._fmp_http.requests.get", fake_get)
    monkeypatch.setattr("terminal.data._fmp_http.time.sleep", lambda *_: None)
    provider.http.request("stable/historical-price-eod/full", {"symbol": "AAPL"})
    assert state["calls"] == 3


def test_missing_key_raises(config):
    cfg = copy.deepcopy(config)
    p = FMPProvider(cfg)
    p.http.api_key = ""
    with pytest.raises(RuntimeError, match="FMP_API_KEY"):
        p.http.request("stable/quote", {"symbol": "AAPL"})
