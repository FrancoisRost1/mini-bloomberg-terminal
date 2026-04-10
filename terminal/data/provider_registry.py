"""Provider registry and per purpose routing.

The terminal uses three live data sources, each owning a specific
purpose. There is NO silent failover between them: each route is an
explicit architectural decision based on what the source actually
serves on its current paid tier.

- single_stock_provider:  FMP   (stable/quote, prices, statements)
- index_etf_provider:     yfinance (SPY, QQQ, ^VIX, ETFs, sector universe)
- options_provider:       yfinance (FMP Starter does not include options)
- macro:                  FRED   (Treasury yields, credit spreads, VIX history)

In production mode the single stock provider is FMP. If FMP is
unavailable the registry returns None and the UI surfaces an inline
DEGRADED tag rather than silently falling through to yfinance for
single stocks. yfinance is allowed in production for the explicit
ETF / index / options routes only.
"""

from __future__ import annotations

from typing import Any

from ..config_loader import get_app_mode, is_production
from .provider_fmp import FMPProvider
from .provider_fred import FredProvider
from .provider_interface import MarketDataProvider
from .provider_polygon import PolygonProvider  # noqa: F401  reserved for v2
from .provider_yfinance import YFinanceProvider


class ProviderRegistry:
    """Resolves the active provider for each data purpose."""

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        self.mode = get_app_mode(config)
        self._stocks: MarketDataProvider | None = None
        self._index: MarketDataProvider | None = None
        self._options: MarketDataProvider | None = None
        self._macro: MarketDataProvider | None = None

    def single_stock_provider(self) -> MarketDataProvider | None:
        """FMP in production. Falls back to yfinance only in development."""
        if self._stocks is not None:
            return self._stocks
        fmp = FMPProvider(self.cfg)
        if fmp.healthcheck():
            self._stocks = fmp
            return fmp
        if is_production(self.cfg):
            return None
        self._stocks = YFinanceProvider(self.cfg)
        return self._stocks

    def index_etf_provider(self) -> MarketDataProvider:
        """Always yfinance. Used for indices, ETFs, and the breadth universe."""
        if self._index is None:
            self._index = YFinanceProvider(self.cfg)
        return self._index

    def options_provider(self) -> MarketDataProvider:
        """Always yfinance. FMP Starter does not include options."""
        if self._options is None:
            self._options = YFinanceProvider(self.cfg)
        return self._options

    def macro(self) -> MarketDataProvider:
        if self._macro is None:
            self._macro = FredProvider(self.cfg)
        return self._macro

    def equity(self) -> MarketDataProvider | None:
        """Backward compatibility alias for ``single_stock_provider``."""
        return self.single_stock_provider()

    def mode_label(self) -> str:
        return self.mode.upper()

    def is_dev_mode(self) -> bool:
        return not is_production(self.cfg)
