"""Polygon.io provider stub.

Interface-ready but not wired in v1. Migration path: implement each method
against the Polygon REST API, add ``polygon`` to config.yaml under
``data.primary_provider``, and set ``POLYGON_API_KEY`` in the container
environment. No other code changes are required.
"""

from __future__ import annotations

import os
from typing import Any

from .provider_interface import MarketDataProvider
from .schemas import Fundamentals, MacroData, OptionsChain, PriceData


class PolygonProvider(MarketDataProvider):
    """Future-upgrade provider. Raises on use so nothing silently falls through."""

    name = "polygon"
    is_dev_only = False

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        self.api_key = os.environ.get("POLYGON_API_KEY", "")

    def _not_implemented(self) -> None:
        raise NotImplementedError(
            "Polygon provider is interface-ready but not wired in v1. "
            "Swap FMP for Polygon by implementing this class."
        )

    def get_prices(self, ticker: str, period: str = "1y") -> PriceData:
        self._not_implemented()

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        self._not_implemented()

    def get_macro(self, series: list[str]) -> MacroData:
        self._not_implemented()

    def get_options_chain(self, ticker: str) -> OptionsChain:
        self._not_implemented()

    def healthcheck(self) -> bool:
        return False
