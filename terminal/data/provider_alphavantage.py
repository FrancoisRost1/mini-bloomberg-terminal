"""Alpha Vantage production provider.

Covers daily prices, company overview, annual statements, and options.

- Rate limit: 25/min free, 75/min paid. Respected via sliding-window
  throttle and exponential backoff on Note responses.
- Premium endpoint detection: AV returns ``Information`` keys for paid
  endpoints. Surfaced as ``PremiumEndpointError`` so callers can fall
  back rather than mistaking it for rate limiting.
- Free-tier fallback: ``TIME_SERIES_DAILY_ADJUSTED`` is paid-only.
  ``get_prices`` falls back to ``TIME_SERIES_DAILY`` automatically.

Parsing logic lives in ``_alphavantage_parsers.py``.
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


class PremiumEndpointError(RuntimeError):
    """Raised when AV returns an ``Information`` payload indicating a paid-only endpoint."""


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
        """Execute a GET with throttle, retry, premium-endpoint detection, and rate-limit handling."""
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
            # Premium-only endpoint: AV returns {"Information": "...premium endpoint..."}.
            # This is distinct from rate limiting; do NOT retry, raise so the caller
            # can fall back to a free-tier endpoint instead.
            info = data.get("Information")
            if isinstance(info, str) and ("premium" in info.lower() or "subscribe" in info.lower()):
                raise PremiumEndpointError(info)
            # Genuine rate limit (Note key, or non-premium Information)
            if "Note" in data or info is not None:
                if attempt >= self.max_retries:
                    raise RuntimeError(
                        f"Alpha Vantage rate limit: {data.get('Note') or info}"
                    )
                time.sleep(self.backoff_base * (self.backoff_mult ** attempt))
                attempt += 1
                continue
            if "Error Message" in data:
                raise RuntimeError(f"Alpha Vantage error: {data['Error Message']}")
            return data

    def get_prices(self, ticker: str, period: str = "1y") -> PriceData:
        """Fetch daily prices.

        Tries the adjusted endpoint (paid tier) first, falls back to the
        free ``TIME_SERIES_DAILY`` endpoint on PremiumEndpointError. The
        non-adjusted endpoint omits the ``adj_close`` column; the parser
        falls back to ``close`` for adj_close in that case.
        """
        try:
            payload = self._request({
                "function": "TIME_SERIES_DAILY_ADJUSTED",
                "symbol": ticker,
                "outputsize": "full",
            })
        except PremiumEndpointError:
            payload = self._request({
                "function": "TIME_SERIES_DAILY",
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
