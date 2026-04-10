"""Unit tests for the SharedDataManager.

Covers per purpose routing (stock vs index vs options vs macro), cache
round trip, error path wrapping (no raise), TTL expiry, and the
``get_any_prices`` cascade used by Portfolio Builder.
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
    # Wire the fake provider in for both single stock and index routes so
    # tests do not need to know which slot is being exercised.
    mgr.registry._stocks = fake
    mgr.registry._index = fake
    return mgr, fake


def test_get_stock_prices_returns_normalized(manager):
    mgr, _ = manager
    result = mgr.get_stock_prices("AAPL", period="1y")
    assert isinstance(result, PriceData)
    assert not result.is_empty()


def test_get_index_prices_returns_normalized(manager):
    mgr, _ = manager
    result = mgr.get_index_prices("SPY", period="1y")
    assert isinstance(result, PriceData)


def test_get_prices_alias_routes_to_stock(manager):
    """Backward compat alias must hit the stock provider, not the index one."""
    mgr, fake = manager
    fake.call_counts.clear()
    mgr.get_prices("AAPL")
    assert "prices:AAPL" in fake.call_counts


def test_get_stock_prices_cached(manager):
    mgr, fake = manager
    fake.call_counts.clear()
    mgr.get_stock_prices("AAPL", period="1y")
    first = fake.call_counts.get("prices:AAPL", 0)
    mgr.get_stock_prices("AAPL", period="1y")
    assert fake.call_counts.get("prices:AAPL", 0) == first


def test_get_stock_prices_error_wrapped(manager):
    mgr, fake = manager
    fake.fail_on.add("BROKEN")
    result = mgr.get_stock_prices("BROKEN")
    assert isinstance(result, ProviderError)
    assert "forced failure" in result.reason


def test_get_any_prices_falls_through_to_index(config, tmp_path):
    """Bug regression: portfolio cascade must try the index provider when
    the stock provider returns an error or empty payload."""
    cfg = copy.deepcopy(config)
    cfg["_meta"]["project_root"] = str(tmp_path)
    cfg["data"]["cache_ttl"] = {"prices": 60, "fundamentals": 60, "macro": 60, "options": 60, "engine_results": 60}
    mgr = SharedDataManager(cfg)
    failing = FakeProvider(cfg)
    failing.fail_on.add("SPY")
    working = FakeProvider(cfg)
    mgr.registry._stocks = failing
    mgr.registry._index = working
    result = mgr.get_any_prices("SPY")
    assert isinstance(result, PriceData)
    assert not result.is_empty()


def test_get_fundamentals_round_trip(manager):
    mgr, _ = manager
    f = mgr.get_fundamentals("AAPL")
    assert f.has_financials()
    assert f.key_ratios["pe_ratio"] == 18.0


def test_get_options_chain_uses_options_provider(config, tmp_path):
    cfg = copy.deepcopy(config)
    cfg["_meta"]["project_root"] = str(tmp_path)
    cfg["data"]["cache_ttl"] = {"prices": 60, "fundamentals": 60, "macro": 60, "options": 60, "engine_results": 60}
    mgr = SharedDataManager(cfg)
    fake = FakeProvider(cfg)
    mgr.registry._options = fake
    chain = mgr.get_options_chain("AAPL")
    assert "options:AAPL" in fake.call_counts


def test_get_macro_uses_fred_provider(manager):
    mgr, _ = manager
    macro = mgr.get_macro(["DGS10"])
    assert macro.provider in {"fred", "fake"}


def test_cache_expiry_triggers_refetch(config, tmp_path):
    cfg = copy.deepcopy(config)
    cfg["_meta"]["project_root"] = str(tmp_path)
    cfg["data"]["cache_ttl"] = {"prices": 0.05, "fundamentals": 60, "macro": 60, "options": 60, "engine_results": 60}
    mgr = SharedDataManager(cfg)
    fake = FakeProvider(cfg)
    mgr.registry._stocks = fake
    mgr.get_stock_prices("AAPL")
    time.sleep(0.1)
    mgr.get_stock_prices("AAPL")
    assert fake.call_counts["prices:AAPL"] == 2


def test_no_stock_provider_yields_error(config, tmp_path, monkeypatch):
    cfg = copy.deepcopy(config)
    cfg["_meta"]["project_root"] = str(tmp_path)
    cfg["app"]["mode"] = "production"
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    mgr = SharedDataManager(cfg)
    result = mgr.get_stock_prices("AAPL")
    assert isinstance(result, ProviderError)
    assert "no stock provider" in result.reason.lower()
