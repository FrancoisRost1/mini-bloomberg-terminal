"""SharedDataManager.

Routes every data call through the registry to the correct per-purpose
provider. Each method returns a normalized schema or ProviderError.
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
        """Try stock provider first, then index. For unknown ticker types."""
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

    def _yf_cached(self, namespace: str, ticker: str, fetcher, ttl_key: str = "fundamentals", **kw):
        """Shared cache-through pattern for yfinance convenience methods."""
        key = f"{namespace}|{ticker}"
        cached = self.cache.get(namespace, key)
        if cached is not None:
            return cached
        data = fetcher(ticker, **kw) if kw else fetcher(ticker)
        self.cache.set(namespace, key, data, float(self.ttls.get(ttl_key, 3600)))
        return data

    def get_news(self, ticker: str, count: int = 8) -> list[dict]:
        from ._news_fetch import fetch_news
        return self._yf_cached("news", ticker, fetch_news, "prices", count=count)

    def get_analyst_data(self, ticker: str) -> dict:
        from ._analyst_fetch import fetch_analyst_data
        return self._yf_cached("analyst", ticker, fetch_analyst_data)

    def get_earnings(self, ticker: str) -> dict:
        from ._earnings_fetch import fetch_earnings
        return self._yf_cached("earnings", ticker, fetch_earnings)

    def get_ownership(self, ticker: str) -> dict:
        from ._ownership_fetch import fetch_ownership
        return self._yf_cached("ownership", ticker, fetch_ownership)

    def get_short_interest(self, ticker: str) -> dict:
        from ._short_interest_fetch import fetch_short_interest
        return self._yf_cached("short_interest", ticker, fetch_short_interest)

    def get_dividends(self, ticker: str) -> dict:
        from ._dividends_fetch import fetch_dividends
        return self._yf_cached("dividends", ticker, fetch_dividends)

    def snapshot_age(self) -> datetime:
        return datetime.utcnow()
