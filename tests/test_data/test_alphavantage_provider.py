"""Unit tests for the Alpha Vantage provider error handling.

These tests do NOT hit the network. They monkeypatch ``_request`` to
exercise the premium-endpoint detection and free-tier fallback path.
"""

from __future__ import annotations

import copy

import pytest

from terminal.data.provider_alphavantage import AlphaVantageProvider, PremiumEndpointError


@pytest.fixture
def provider(config, monkeypatch):
    cfg = copy.deepcopy(config)
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test_key")
    return AlphaVantageProvider(cfg)


def test_premium_endpoint_distinct_from_rate_limit(provider, monkeypatch):
    """Bug 2 regression: premium-endpoint info must NOT be retried as rate-limit."""
    captured = {"calls": 0}

    def fake_get(*args, **kwargs):
        captured["calls"] += 1

        class Resp:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"Information": "Thank you for using Alpha Vantage! This is a premium endpoint. Please subscribe."}

        return Resp()

    monkeypatch.setattr("terminal.data.provider_alphavantage.requests.get", fake_get)
    with pytest.raises(PremiumEndpointError):
        provider._request({"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": "AAPL"})
    # Must NOT have retried -- premium errors are immediate, not rate-limit.
    assert captured["calls"] == 1


def test_get_prices_falls_back_to_free_endpoint(provider, monkeypatch):
    """Bug 2 regression: get_prices must transparently fall back to TIME_SERIES_DAILY on premium error."""
    call_log: list[str] = []

    def fake_get(url, params=None, timeout=None):
        function = params.get("function") if params else ""
        call_log.append(function)

        class Resp:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                if function == "TIME_SERIES_DAILY_ADJUSTED":
                    return {"Information": "premium endpoint"}
                if function == "TIME_SERIES_DAILY":
                    return {
                        "Time Series (Daily)": {
                            "2024-01-02": {"1. open": "100", "2. high": "101", "3. low": "99",
                                            "4. close": "100.5", "6. volume": "1000"},
                            "2024-01-03": {"1. open": "100.5", "2. high": "102", "3. low": "100",
                                            "4. close": "101.5", "6. volume": "1100"},
                        }
                    }
                return {}

        return Resp()

    monkeypatch.setattr("terminal.data.provider_alphavantage.requests.get", fake_get)
    result = provider.get_prices("AAPL", period="1mo")
    # Both endpoints should have been called: adjusted first, then daily fallback.
    assert "TIME_SERIES_DAILY_ADJUSTED" in call_log
    assert "TIME_SERIES_DAILY" in call_log
    assert not result.is_empty()
    assert result.last_close() == 101.5


def test_genuine_rate_limit_still_retries(provider, monkeypatch):
    """Distinct from premium: a Note response must trigger retry-with-backoff."""
    state = {"call": 0}

    def fake_get(*args, **kwargs):
        state["call"] += 1

        class Resp:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                if state["call"] < 3:
                    return {"Note": "rate limit hit"}
                return {"Time Series (Daily)": {}}

        return Resp()

    monkeypatch.setattr("terminal.data.provider_alphavantage.requests.get", fake_get)
    monkeypatch.setattr("terminal.data.provider_alphavantage.time.sleep", lambda *_: None)
    result = provider._request({"function": "TIME_SERIES_DAILY", "symbol": "AAPL"})
    assert state["call"] == 3
    assert "Time Series (Daily)" in result
