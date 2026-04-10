"""Mode enforcement tests for the provider registry.

These tests guard Section 0 of CLAUDE.md, the live first operating
rule. Production mode MUST refuse to instantiate yfinance. If these
tests ever fail silently, the app is serving scraped data while
claiming production status.
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


def test_production_selects_fmp(prod_config, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test_key")
    registry = ProviderRegistry(prod_config)
    provider = registry.equity()
    assert isinstance(provider, FMPProvider)
    assert provider.name == "fmp"
    assert provider.is_dev_only is False


def test_production_refuses_yfinance_even_if_configured(prod_config):
    prod_config["data"]["primary_provider"] = "yfinance"
    registry = ProviderRegistry(prod_config)
    provider = registry.equity()
    assert provider is None


def test_production_without_fmp_key_is_none(prod_config, monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    registry = ProviderRegistry(prod_config)
    provider = registry.equity()
    assert provider is None


def test_development_allows_yfinance(dev_config):
    registry = ProviderRegistry(dev_config)
    provider = registry.equity()
    assert isinstance(provider, YFinanceProvider)
    assert provider.is_dev_only is True
    assert registry.is_dev_mode() is True


def test_registry_macro_always_fred_regardless_of_mode(prod_config, dev_config):
    for cfg in (prod_config, dev_config):
        registry = ProviderRegistry(cfg)
        assert isinstance(registry.macro(), FredProvider)


def test_env_var_overrides_config_mode(prod_config, monkeypatch):
    monkeypatch.setenv("APP_MODE", "development")
    registry = ProviderRegistry(prod_config)
    provider = registry.equity()
    assert isinstance(provider, YFinanceProvider)


def test_polygon_stub_raises_on_use(prod_config):
    polygon = PolygonProvider(prod_config)
    with pytest.raises(NotImplementedError):
        polygon.get_prices("AAPL")


def test_dev_mode_flag_label(dev_config):
    registry = ProviderRegistry(dev_config)
    assert registry.mode_label() == "DEVELOPMENT"
    assert registry.is_dev_mode()


def test_production_mode_flag_label(prod_config, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "k")
    registry = ProviderRegistry(prod_config)
    assert registry.mode_label() == "PRODUCTION"
    assert not registry.is_dev_mode()
