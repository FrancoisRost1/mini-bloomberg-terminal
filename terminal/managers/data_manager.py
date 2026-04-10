"""SharedDataManager.

Holds provider instances and the disk cache. Every data call goes through
here so the rest of the app never sees raw provider calls. Returns either
a normalized schema or a ``ProviderError`` dataclass -- never raises.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..config_loader import config_hash
from ..data.cache import DiskCache
from ..data.provider_registry import ProviderRegistry
from ..data.schemas import Fundamentals, MacroData, OptionsChain, PriceData, ProviderError


class SharedDataManager:
    """Single source of truth for market data in the app.

    Lifecycle: one instance per Streamlit session via ``st.cache_resource``.
    Intended to be constructed once and reused across pages so that TTL
    caching is meaningful.
    """

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        self.registry = ProviderRegistry(config)
        cache_dir = Path(config["_meta"]["project_root"]) / "data" / "cache"
        self.cache = DiskCache(cache_dir, config_hash(config))
        self.ttls = config["data"]["cache_ttl"]

    def get_prices(self, ticker: str, period: str = "1y") -> PriceData | ProviderError:
        key = f"prices|{ticker}|{period}"
        cached = self.cache.get("prices", key)
        if cached is not None:
            return cached
        provider = self.registry.equity()
        if provider is None:
            return ProviderError("registry", ticker, "prices", "no equity provider available")
        try:
            data = provider.get_prices(ticker, period)
        except Exception as exc:
            return ProviderError(provider.name, ticker, "prices", str(exc))
        self.cache.set("prices", key, data, float(self.ttls["prices"]))
        return data

    def get_fundamentals(self, ticker: str) -> Fundamentals | ProviderError:
        key = f"fundamentals|{ticker}"
        cached = self.cache.get("fundamentals", key)
        if cached is not None:
            return cached
        provider = self.registry.equity()
        if provider is None:
            return ProviderError("registry", ticker, "fundamentals", "no equity provider available")
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
        self.cache.set("macro", key, data, float(self.ttls["macro"]))
        return data

    def get_options_chain(self, ticker: str) -> OptionsChain | ProviderError:
        key = f"options|{ticker}"
        cached = self.cache.get("options", key)
        if cached is not None:
            return cached
        provider = self.registry.equity()
        if provider is None:
            return ProviderError("registry", ticker, "options", "no equity provider available")
        try:
            data = provider.get_options_chain(ticker)
        except Exception as exc:
            return ProviderError(provider.name, ticker, "options", str(exc))
        self.cache.set("options", key, data, float(self.ttls["options"]))
        return data

    def snapshot_age(self) -> datetime:
        """Timestamp helper for the global header."""
        return datetime.utcnow()
