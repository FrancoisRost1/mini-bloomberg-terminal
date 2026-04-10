"""Per purpose routing tests for the provider registry.

The registry exposes three per purpose methods:

- single_stock_provider:  FMP in production, yfinance fallback in dev
- index_etf_provider:     yfinance always
- options_provider:       yfinance always
- macro:                  FRED always

There is NO silent failover between purposes. If the FMP key is missing
in production, ``single_stock_provider()`` returns None and the UI
surfaces a DEGRADED tag. yfinance is allowed in production for the
explicit ETF / index / options routes only.
"""

from __future__ import annotations

import copy

import pytest

from terminal.data.provider_fmp import FMPProvider
from terminal.data.provider_fred import FredProvider
from terminal.data.provider_polygon import PolygonProvider
from terminal.data.provider_registry import ProviderRegistry
from terminal.data.provider_yfinance import YFinanceProvider


@pytest.fixture
def prod_config(config):
    cfg = copy.deepcopy(config)
    cfg["app"]["mode"] = "production"
    return cfg


@pytest.fixture
def dev_config(config):
    cfg = copy.deepcopy(config)
    cfg["app"]["mode"] = "development"
    return cfg


@pytest.fixture(autouse=True)
def _clear_app_mode(monkeypatch):
    monkeypatch.delenv("APP_MODE", raising=False)


def test_single_stock_provider_is_fmp_in_production(prod_config, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test_key")
    registry = ProviderRegistry(prod_config)
    provider = registry.single_stock_provider()
    assert isinstance(provider, FMPProvider)
    assert provider.name == "fmp"


def test_single_stock_provider_none_when_fmp_key_missing_in_prod(prod_config, monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    registry = ProviderRegistry(prod_config)
    assert registry.single_stock_provider() is None


def test_single_stock_provider_falls_back_to_yfinance_in_dev(dev_config, monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    registry = ProviderRegistry(dev_config)
    provider = registry.single_stock_provider()
    assert isinstance(provider, YFinanceProvider)


def test_index_etf_provider_always_yfinance_production(prod_config, monkeypatch):
    """Production allows yfinance for ETF / index data even though
    yfinance is forbidden as the primary single stock provider."""
    monkeypatch.setenv("FMP_API_KEY", "test_key")
    registry = ProviderRegistry(prod_config)
    provider = registry.index_etf_provider()
    assert isinstance(provider, YFinanceProvider)


def test_index_etf_provider_always_yfinance_dev(dev_config):
    registry = ProviderRegistry(dev_config)
    provider = registry.index_etf_provider()
    assert isinstance(provider, YFinanceProvider)


def test_options_provider_always_yfinance(prod_config, dev_config, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test_key")
    for cfg in (prod_config, dev_config):
        registry = ProviderRegistry(cfg)
        provider = registry.options_provider()
        assert isinstance(provider, YFinanceProvider)
        assert provider.supports_options_chain() is True


def test_macro_always_fred(prod_config, dev_config):
    for cfg in (prod_config, dev_config):
        registry = ProviderRegistry(cfg)
        assert isinstance(registry.macro(), FredProvider)


def test_equity_alias_returns_single_stock_provider(prod_config, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test_key")
    registry = ProviderRegistry(prod_config)
    assert registry.equity() is registry.single_stock_provider()


def test_polygon_stub_raises_on_use(prod_config):
    polygon = PolygonProvider(prod_config)
    with pytest.raises(NotImplementedError):
        polygon.get_prices("AAPL")


def test_dev_mode_flag_label(dev_config):
    registry = ProviderRegistry(dev_config)
    assert registry.mode_label() == "DEVELOPMENT"
    assert registry.is_dev_mode() is True


def test_production_mode_flag_label(prod_config, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "k")
    registry = ProviderRegistry(prod_config)
    assert registry.mode_label() == "PRODUCTION"
    assert registry.is_dev_mode() is False
