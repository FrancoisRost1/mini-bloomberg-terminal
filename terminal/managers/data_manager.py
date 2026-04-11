"""SharedDataManager.

Routes every data call through the registry to the correct per purpose
provider. Single stock fundamentals and prices go to FMP. Indices,
ETFs, options chains, and the breadth universe go to yfinance. Macro
goes to FRED. Each method returns either a normalized schema or a
``ProviderError`` -- never raises.

The page layer should pick the right method explicitly:
- get_stock_prices  for an FMP single ticker
- get_index_prices  for SPY / QQQ / sector ETFs / ^VIX style symbols
- get_any_prices    for portfolio holdings where the type is unknown
- get_fundamentals  for FMP single ticker statements
- get_options_chain for an options chain (yfinance)
- get_macro         for FRED series
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..config_loader import config_hash
from ..data.cache import DiskCache
from ..data.provider_registry import ProviderRegistry
from ..data.schemas import Fundamentals, MacroData, OptionsChain, PriceData, ProviderError
from ..utils.last_good_cache import LastGoodCache
from ._macro_fallback import backfill_from_last_good, persist_last_good


class SharedDataManager:
    """Single source of truth for market data in the app."""

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        self.registry = ProviderRegistry(config)
        project_root = Path(config["_meta"]["project_root"])
        cache_dir = project_root / "data" / "cache"
        self.cache = DiskCache(cache_dir, config_hash(config))
        self.ttls = config["data"]["cache_ttl"]
        # Tiny cross-session JSON cache for the last successful FRED
        # observation per series. When FRED returns empty (rate limit,
        # network blip, API key glitch) we serve the stored value so
        # the page never collapses to n/a. MacroData.stale records
        # which ids were served from the fallback so the UI can
        # annotate them with a STALE marker.
        self._macro_last_good = LastGoodCache(project_root / "data" / "macro_last_good.json")

    def get_stock_prices(self, ticker: str, period: str = "1y") -> PriceData | ProviderError:
        return self._fetch_prices("stock", self.registry.single_stock_provider(), ticker, period)

    def get_index_prices(self, ticker: str, period: str = "1y") -> PriceData | ProviderError:
        return self._fetch_prices("index", self.registry.index_etf_provider(), ticker, period)

    def get_any_prices(self, ticker: str, period: str = "1y") -> PriceData | ProviderError:
        """Try the stock provider first; fall through to the index provider per ticker.

        Used by the Portfolio Builder where the user enters arbitrary
        tickers and we cannot tell stocks from ETFs at the call site.
        Returns the first non-error response. Both providers are
        explicitly probed; this is NOT a silent failover at the
        registry level.
        """
        result = self.get_stock_prices(ticker, period)
        if isinstance(result, PriceData) and not result.is_empty():
            return result
        return self.get_index_prices(ticker, period)

    # Backward compat alias. Defaults to the stock route.
    def get_prices(self, ticker: str, period: str = "1y") -> PriceData | ProviderError:
        return self.get_stock_prices(ticker, period)

    def get_fundamentals(self, ticker: str) -> Fundamentals | ProviderError:
        key = f"fundamentals|{ticker}"
        cached = self.cache.get("fundamentals", key)
        if cached is not None:
            return cached
        provider = self.registry.single_stock_provider()
        if provider is None:
            return ProviderError("registry", ticker, "fundamentals", "no single stock provider available")
        try:
            data = provider.get_fundamentals(ticker)
        except Exception as exc:
            return ProviderError(provider.name, ticker, "fundamentals", str(exc))
        self.cache.set("fundamentals", key, data, float(self.ttls["fundamentals"]))
        return data

    def get_macro(self, series: list[str]) -> MacroData | ProviderError:
        key = f"macro|{','.join(sorted(series))}"
        cached = self.cache.get("macro", key)
        if cached is not None:
            return cached
        try:
            data = self.registry.macro().get_macro(series)
        except Exception as exc:
            return ProviderError("fred", "-", "macro", str(exc))
        persist_last_good(self._macro_last_good, data, series)
        backfill_from_last_good(self._macro_last_good, data, series)
        self.cache.set("macro", key, data, float(self.ttls["macro"]))
        return data

    def get_options_chain(self, ticker: str) -> OptionsChain | ProviderError:
        key = f"options|{ticker}"
        cached = self.cache.get("options", key)
        if cached is not None:
            return cached
        provider = self.registry.options_provider()
        try:
            data = provider.get_options_chain(ticker)
        except Exception as exc:
            return ProviderError(provider.name, ticker, "options", str(exc))
        self.cache.set("options", key, data, float(self.ttls["options"]))
        return data

    def _fetch_prices(self, kind: str, provider, ticker: str, period: str) -> PriceData | ProviderError:
        if provider is None:
            return ProviderError("registry", ticker, f"{kind}_prices", f"no {kind} provider available")
        key = f"{kind}_prices|{ticker}|{period}"
        cached = self.cache.get("prices", key)
        if cached is not None:
            return cached
        try:
            data = provider.get_prices(ticker, period)
        except Exception as exc:
            return ProviderError(provider.name, ticker, f"{kind}_prices", str(exc))
        self.cache.set("prices", key, data, float(self.ttls["prices"]))
        return data

    def snapshot_age(self) -> datetime:
        return datetime.utcnow()
