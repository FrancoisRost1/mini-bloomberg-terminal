"""Abstract market data provider interface.

All concrete providers (FMP, yfinance, Polygon) implement this
contract and return normalized schemas from ``schemas.py``. The UI layer
only ever talks to this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .schemas import Fundamentals, MacroData, OptionsChain, PriceData


class MarketDataProvider(ABC):
    """Abstract interface for market data providers.

    Rationale: enforces a single boundary where the rest of the app can
    remain provider agnostic. Swapping FMP for Polygon in v2
    should only require changing a config key and adding an API key.
    """

    name: str = "abstract"
    is_dev_only: bool = False

    @abstractmethod
    def get_prices(self, ticker: str, period: str = "1y") -> PriceData:
        """Fetch OHLCV price history for a single ticker."""

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> Fundamentals:
        """Fetch annual financial statements and key ratios."""

    @abstractmethod
    def get_macro(self, series: list[str]) -> MacroData:
        """Fetch macro time series (typically FRED-style series ids)."""

    @abstractmethod
    def get_options_chain(self, ticker: str) -> OptionsChain:
        """Fetch the current options chain with bid/ask/volume/OI."""

    def healthcheck(self) -> bool:
        """Lightweight probe for the registry to decide if the provider is live."""
        return True
