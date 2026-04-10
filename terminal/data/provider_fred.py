"""FRED macro data provider.

Always used for macro series in both production and development. Treasury
yields arrive as percentages (e.g. 4.25 for 4.25%) and are left in percent
units; downstream code that wants fractions must divide by 100 explicitly.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import pandas as pd
import requests

from .provider_interface import MarketDataProvider
from .schemas import Fundamentals, MacroData, OptionsChain, PriceData


FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


class FredProvider(MarketDataProvider):
    """FRED-only provider for macro time series. Not used for equities."""

    name = "fred"
    is_dev_only = False

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        self.api_key = os.environ.get("FRED_API_KEY", "")

    def get_macro(self, series: list[str]) -> MacroData:
        result: dict[str, pd.Series] = {}
        for series_id in series:
            result[series_id] = self._fetch_series(series_id)
        return MacroData(series=result, provider=self.name, as_of=datetime.utcnow())

    def _fetch_series(self, series_id: str) -> pd.Series:
        if not self.api_key:
            return pd.Series(dtype=float, name=series_id)
        try:
            resp = requests.get(
                FRED_BASE,
                params={
                    "series_id": series_id,
                    "api_key": self.api_key,
                    "file_type": "json",
                    "observation_start": "2010-01-01",
                },
                timeout=15,
            )
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError):
            return pd.Series(dtype=float, name=series_id)
        obs = payload.get("observations", [])
        if not obs:
            return pd.Series(dtype=float, name=series_id)
        df = pd.DataFrame(obs)
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.set_index("date")["value"].dropna().rename(series_id)

    def get_prices(self, ticker: str, period: str = "1y") -> PriceData:
        raise NotImplementedError("FredProvider does not serve equity prices")

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        raise NotImplementedError("FredProvider does not serve fundamentals")

    def get_options_chain(self, ticker: str) -> OptionsChain:
        raise NotImplementedError("FredProvider does not serve options chains")

    def healthcheck(self) -> bool:
        return bool(self.api_key)
