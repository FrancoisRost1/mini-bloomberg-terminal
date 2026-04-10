"""Provider registry and mode enforcement.

Production mode: FMP only for equities. No silent yfinance fallback.
If FMP is unavailable, upstream code must surface a DEGRADED or
DATA UNAVAILABLE state.

Development mode: yfinance is permitted and carries a visible DEV MODE
flag.

Polygon is interface ready but not wired in v1. Swapping FMP for
Polygon in v2 requires only a config change and an API key.
"""

from __future__ import annotations

from typing import Any

from ..config_loader import get_app_mode, is_production
from .provider_fmp import FMPProvider
from .provider_fred import FredProvider
from .provider_interface import MarketDataProvider
from .provider_polygon import PolygonProvider
from .provider_yfinance import YFinanceProvider


class ProviderRegistry:
    """Resolves the active equity and macro providers for a given config.

    The registry holds lazily constructed singletons. Healthcheck
    failures cause ``equity()`` to return ``None``; the UI treats this
    as DEGRADED rather than crashing the process.
    """

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        self.mode = get_app_mode(config)
        self._equity: MarketDataProvider | None = None
        self._macro: MarketDataProvider | None = None

    def equity(self) -> MarketDataProvider | None:
        if self._equity is not None:
            return self._equity
        name = self._select_equity_name()
        provider = self._instantiate(name)
        if provider is None:
            return None
        if not provider.healthcheck():
            if is_production(self.cfg):
                return None
        self._equity = provider
        return provider

    def macro(self) -> MarketDataProvider:
        if self._macro is None:
            self._macro = FredProvider(self.cfg)
        return self._macro

    def mode_label(self) -> str:
        return self.mode.upper()

    def is_dev_mode(self) -> bool:
        return not is_production(self.cfg)

    def _select_equity_name(self) -> str:
        if is_production(self.cfg):
            return str(self.cfg["data"].get("primary_provider", "fmp"))
        return str(self.cfg["data"].get("dev_provider", "yfinance"))

    def _instantiate(self, name: str) -> MarketDataProvider | None:
        name = (name or "").lower()
        if name == "fmp":
            return FMPProvider(self.cfg)
        if name == "yfinance":
            if is_production(self.cfg):
                return None
            return YFinanceProvider(self.cfg)
        if name == "polygon":
            return PolygonProvider(self.cfg)
        return None
