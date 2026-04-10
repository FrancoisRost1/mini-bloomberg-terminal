"""Financial Modeling Prep production provider.

Replaces Alpha Vantage as the primary equity provider in the
production path. FMP Starter tier covers everything the terminal needs.

Endpoints used:
- GET /api/v3/quote/{symbol}                    quote with PE, price
- GET /api/v3/profile/{symbol}                  company profile
- GET /api/v3/historical-price-full/{symbol}    daily prices (OHLCV)
- GET /api/v3/income-statement/{symbol}         annual income statement
- GET /api/v3/balance-sheet-statement/{symbol}  annual balance sheet
- GET /api/v3/cash-flow-statement/{symbol}      annual cash flow
- GET /api/v3/historical-chart/15min/{symbol}   intraday (not used in v1)
- GET /api/v3/options-chain/{symbol}            options chain (when available)

Rate limit handling: FMP Starter is 750 req/min, far above what the
terminal consumes. Throttle still active as a safety net using the
configured value.

Parsing logic lives in _fmp_parsers.py to keep this file under the
per module line budget.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

import pandas as pd
import requests

from . import _fmp_parsers as parsers
from .provider_interface import MarketDataProvider
from .schemas import Fundamentals, MacroData, OptionsChain, PriceData


class FMPProvider(MarketDataProvider):
    """Production market data provider backed by Financial Modeling Prep."""

    name = "fmp"
    is_dev_only = False

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        fmp_cfg = config["data"]["fmp"]
        self.base_url = fmp_cfg["base_url"]
        self.rate_limit_per_minute = int(fmp_cfg["rate_limit_per_minute"])
        self._last_calls: list[float] = []
        retry_cfg = config["data"]["rate_limit"]
        self.max_retries = int(retry_cfg["max_retries"])
        self.backoff_base = float(retry_cfg["backoff_base_seconds"])
        self.backoff_mult = float(retry_cfg["backoff_multiplier"])
        self.api_key = os.environ.get("FMP_API_KEY", "")

    def _throttle(self) -> None:
        now = time.time()
        self._last_calls = [t for t in self._last_calls if now - t < 60]
        if len(self._last_calls) >= self.rate_limit_per_minute:
            sleep_for = 60 - (now - self._last_calls[0]) + 0.1
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._last_calls.append(time.time())

    def _request(self, path: str, params: dict[str, str] | None = None) -> Any:
        if not self.api_key:
            raise RuntimeError("FMP_API_KEY environment variable not set")
        merged = dict(params or {})
        merged["apikey"] = self.api_key
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        attempt = 0
        while True:
            self._throttle()
            resp = requests.get(url, params=merged, timeout=20)
            if resp.status_code == 429:
                if attempt >= self.max_retries:
                    raise RuntimeError("FMP rate limit exceeded after retries")
                time.sleep(self.backoff_base * (self.backoff_mult ** attempt))
                attempt += 1
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "Error Message" in data:
                raise RuntimeError(f"FMP error: {data['Error Message']}")
            return data

    def get_prices(self, ticker: str, period: str = "1y") -> PriceData:
        payload = self._request(f"v3/historical-price-full/{ticker}", {"serietype": "line"})
        prices = parsers.parse_historical(payload, period)
        return PriceData(ticker, prices, "USD", self.name, datetime.utcnow(), period)

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        profile_payload = self._request(f"v3/profile/{ticker}")
        quote_payload = self._request(f"v3/quote/{ticker}")
        income = parsers.parse_statement(self._request(f"v3/income-statement/{ticker}", {"limit": "5"}))
        balance = parsers.parse_statement(self._request(f"v3/balance-sheet-statement/{ticker}", {"limit": "5"}))
        cashflow = parsers.parse_statement(self._request(f"v3/cash-flow-statement/{ticker}", {"limit": "5"}))
        profile = profile_payload[0] if isinstance(profile_payload, list) and profile_payload else {}
        quote = quote_payload[0] if isinstance(quote_payload, list) and quote_payload else {}
        ratios = parsers.compute_ratios(profile, quote, income, balance, cashflow)
        return Fundamentals(
            ticker=ticker,
            income_statement=income,
            balance_sheet=balance,
            cash_flow=cashflow,
            key_ratios=ratios,
            market_cap=parsers.safe_float(profile.get("mktCap")),
            sector=str(profile.get("sector", "Unknown")),
            industry=str(profile.get("industry", "Unknown")),
            provider=self.name,
            as_of=datetime.utcnow(),
        )

    def get_macro(self, series: list[str]) -> MacroData:
        raise NotImplementedError("Use FredProvider for macro data")

    def get_options_chain(self, ticker: str) -> OptionsChain:
        """FMP options coverage is limited; return empty chain on failure."""
        try:
            payload = self._request(f"v3/options-chain/{ticker}")
        except (requests.RequestException, RuntimeError):
            return OptionsChain(ticker, float("nan"), {}, self.name, datetime.utcnow())
        if not isinstance(payload, list) or not payload:
            return OptionsChain(ticker, float("nan"), {}, self.name, datetime.utcnow())
        df = pd.DataFrame(payload)
        chains: dict[str, pd.DataFrame] = {}
        if "expirationDate" in df.columns:
            keep_cols = [c for c in ["strike", "bid", "ask", "lastPrice", "volume", "openInterest", "type"] if c in df.columns]
            for expiry, group in df.groupby("expirationDate"):
                sub = group[keep_cols].rename(columns={"lastPrice": "last", "openInterest": "open_interest"}).reset_index(drop=True)
                chains[str(expiry)] = sub
        spot = parsers.safe_float(df.get("underlyingPrice", pd.Series([float("nan")])).iloc[0]) if "underlyingPrice" in df.columns else float("nan")
        return OptionsChain(ticker, spot, chains, self.name, datetime.utcnow())

    def healthcheck(self) -> bool:
        return bool(self.api_key)
