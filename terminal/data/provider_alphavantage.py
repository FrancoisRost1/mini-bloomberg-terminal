"""Alpha Vantage production provider.

Full REST integration, not a stub. Covers: daily prices, company overview,
annual income statement / balance sheet / cash flow, and options chain.

Rate limit: 25 req/min free tier, 75 req/min paid. The configured value
is respected here and exponential backoff is applied on 429 and on
``Note``/``Information`` rate-limit responses.

Parsing logic lives in ``_alphavantage_parsers.py`` so this file stays
within the per-module line budget.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

import requests

from . import _alphavantage_parsers as parsers
from .provider_interface import MarketDataProvider
from .schemas import Fundamentals, MacroData, OptionsChain, PriceData


class AlphaVantageProvider(MarketDataProvider):
    """Production market data provider backed by Alpha Vantage REST API."""

    name = "alpha_vantage"
    is_dev_only = False

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        av_cfg = config["data"]["alpha_vantage"]
        self.base_url = av_cfg["base_url"]
        self.rate_limit_per_minute = int(av_cfg["rate_limit_per_minute"])
        self._last_calls: list[float] = []
        retry_cfg = config["data"]["rate_limit"]
        self.max_retries = int(retry_cfg["max_retries"])
        self.backoff_base = float(retry_cfg["backoff_base_seconds"])
        self.backoff_mult = float(retry_cfg["backoff_multiplier"])
        self.api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "")

    def _throttle(self) -> None:
        """Sliding-window throttle against the configured req/min limit."""
        now = time.time()
        self._last_calls = [t for t in self._last_calls if now - t < 60]
        if len(self._last_calls) >= self.rate_limit_per_minute:
            sleep_for = 60 - (now - self._last_calls[0]) + 0.1
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._last_calls.append(time.time())

    def _request(self, params: dict[str, str]) -> dict[str, Any]:
        """Execute a GET with throttle, retry, and explicit rate-limit handling."""
        if not self.api_key:
            raise RuntimeError("ALPHA_VANTAGE_API_KEY environment variable not set")
        params = dict(params)
        params["apikey"] = self.api_key
        attempt = 0
        while True:
            self._throttle()
            resp = requests.get(self.base_url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if "Note" in data or "Information" in data:
                if attempt >= self.max_retries:
                    raise RuntimeError(
                        f"Alpha Vantage rate limit: {data.get('Note') or data.get('Information')}"
                    )
                time.sleep(self.backoff_base * (self.backoff_mult ** attempt))
                attempt += 1
                continue
            if "Error Message" in data:
                raise RuntimeError(f"Alpha Vantage error: {data['Error Message']}")
            return data

    def get_prices(self, ticker: str, period: str = "1y") -> PriceData:
        payload = self._request({
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": ticker,
            "outputsize": "full",
        })
        prices = parsers.parse_daily_series(payload, period)
        return PriceData(ticker, prices, "USD", self.name, datetime.utcnow(), period)

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        overview = self._request({"function": "OVERVIEW", "symbol": ticker})
        income = parsers.parse_statement(self._request({"function": "INCOME_STATEMENT", "symbol": ticker}))
        balance = parsers.parse_statement(self._request({"function": "BALANCE_SHEET", "symbol": ticker}))
        cashflow = parsers.parse_statement(self._request({"function": "CASH_FLOW", "symbol": ticker}))
        ratios = parsers.compute_ratios(overview, income, balance, cashflow)
        return Fundamentals(
            ticker=ticker,
            income_statement=income,
            balance_sheet=balance,
            cash_flow=cashflow,
            key_ratios=ratios,
            market_cap=parsers.safe_float(overview.get("MarketCapitalization")),
            sector=str(overview.get("Sector", "Unknown")),
            industry=str(overview.get("Industry", "Unknown")),
            provider=self.name,
            as_of=datetime.utcnow(),
        )

    def get_macro(self, series: list[str]) -> MacroData:
        raise NotImplementedError("Use FredProvider for macro data")

    def get_options_chain(self, ticker: str) -> OptionsChain:
        payload = self._request({"function": "HISTORICAL_OPTIONS", "symbol": ticker})
        spot, chains = parsers.parse_options_chain(payload)
        return OptionsChain(ticker, spot, chains, self.name, datetime.utcnow())

    def healthcheck(self) -> bool:
        return bool(self.api_key)
