"""Unit tests for the SharedDataManager.

Covers: cache round-trip, error-path wrapping (no raise), and that a
fresh call is only made when the TTL window has expired.
"""

from __future__ import annotations

import copy
import time

import pytest

from terminal.managers.data_manager import SharedDataManager
from terminal.data.schemas import PriceData, ProviderError
from tests.fakes import FakeProvider


@pytest.fixture
def manager(config, tmp_path):
    cfg = copy.deepcopy(config)
    cfg["_meta"]["project_root"] = str(tmp_path)
    (tmp_path / "data" / "cache").mkdir(parents=True, exist_ok=True)
    cfg["data"]["cache_ttl"] = {"prices": 60, "fundamentals": 60, "macro": 60, "options": 60, "engine_results": 60}
    mgr = SharedDataManager(cfg)
    fake = FakeProvider(cfg)
    mgr.registry._equity = fake
    return mgr, fake


def test_get_prices_returns_normalized(manager):
    mgr, fake = manager
    result = mgr.get_prices("AAPL", period="1y")
    assert isinstance(result, PriceData)
    assert result.ticker == "AAPL"
    assert not result.is_empty()


def test_get_prices_cached_on_second_call(manager):
    mgr, fake = manager
    mgr.get_prices("AAPL", period="1y")
    count_after_first = fake.call_counts.get("prices:AAPL", 0)
    mgr.get_prices("AAPL", period="1y")
    assert fake.call_counts.get("prices:AAPL", 0) == count_after_first


def test_get_prices_error_is_wrapped_not_raised(manager):
    mgr, fake = manager
    fake.fail_on.add("BROKEN")
    result = mgr.get_prices("BROKEN")
    assert isinstance(result, ProviderError)
    assert result.provider == "fake"
    assert "forced failure" in result.reason


def test_get_fundamentals_round_trip(manager):
    mgr, _ = manager
    f = mgr.get_fundamentals("AAPL")
    assert f.has_financials()
    assert f.key_ratios["pe_ratio"] == 18.0


def test_get_macro_uses_fred_provider(manager):
    mgr, _ = manager
    macro = mgr.get_macro(["DGS10"])
    # Registry's macro is a real FredProvider; without an API key it
    # returns an empty series, which is still a valid MacroData object.
    assert macro.provider in {"fred", "fake"}


def test_cache_expiry_triggers_refetch(config, tmp_path):
    cfg = copy.deepcopy(config)
    cfg["_meta"]["project_root"] = str(tmp_path)
    cfg["data"]["cache_ttl"] = {"prices": 0.05, "fundamentals": 60, "macro": 60, "options": 60, "engine_results": 60}
    mgr = SharedDataManager(cfg)
    fake = FakeProvider(cfg)
    mgr.registry._equity = fake
    mgr.get_prices("AAPL")
    time.sleep(0.1)
    mgr.get_prices("AAPL")
    assert fake.call_counts["prices:AAPL"] == 2


def test_no_equity_provider_yields_error(config, tmp_path):
    cfg = copy.deepcopy(config)
    cfg["_meta"]["project_root"] = str(tmp_path)
    cfg["app"]["mode"] = "production"
    cfg["data"]["primary_provider"] = "yfinance"  # refused in production
    mgr = SharedDataManager(cfg)
    result = mgr.get_prices("AAPL")
    assert isinstance(result, ProviderError)
    assert "no equity provider" in result.reason.lower()
