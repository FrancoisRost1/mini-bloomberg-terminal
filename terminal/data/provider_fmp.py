"""Financial Modeling Prep production provider.

Replaces Alpha Vantage as the primary equity provider in the
production path. FMP Starter tier covers everything the terminal
needs except options chains.

Endpoints used:
- v3/quote/{symbol}
- v3/profile/{symbol}
- v3/historical-price-full/{symbol}
- v3/income-statement/{symbol}
- v3/balance-sheet-statement/{symbol}
- v3/cash-flow-statement/{symbol}
- v3/options-chain/{symbol}  (paid only; degrades to OFF on 403)

Capability flag ``supports_options_chain()`` is True until we observe
a 403 on the options endpoint, then flips to False so the navigation
layer can hide the Options Lab page entirely.

HTTP layer (rate limit, retry, 403 detection) lives in _fmp_http.py.
Parsers live in _fmp_parsers.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import requests

from . import _fmp_parsers as parsers
from ._fmp_http import FMPEndpointForbidden, FMPHttp
from .provider_interface import MarketDataProvider
from .schemas import Fundamentals, MacroData, OptionsChain, PriceData


class FMPProvider(MarketDataProvider):
    """Production market data provider backed by Financial Modeling Prep."""

    name = "fmp"
    is_dev_only = False

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        self.http = FMPHttp(config)
        self._options_known_unavailable = False

    @property
    def api_key(self) -> str:
        return self.http.api_key

    def supports_options_chain(self) -> bool:
        """False once we have proven the options endpoint returns 403."""
        return not self._options_known_unavailable

    def get_prices(self, ticker: str, period: str = "1y") -> PriceData:
        payload = self.http.request(f"v3/historical-price-full/{ticker}", {"serietype": "line"})
        prices = parsers.parse_historical(payload, period)
        return PriceData(ticker, prices, "USD", self.name, datetime.utcnow(), period)

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        profile_payload = self.http.request(f"v3/profile/{ticker}")
        quote_payload = self.http.request(f"v3/quote/{ticker}")
        income = parsers.parse_statement(self.http.request(f"v3/income-statement/{ticker}", {"limit": "5"}))
        balance = parsers.parse_statement(self.http.request(f"v3/balance-sheet-statement/{ticker}", {"limit": "5"}))
        cashflow = parsers.parse_statement(self.http.request(f"v3/cash-flow-statement/{ticker}", {"limit": "5"}))
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
        """FMP options is a paid endpoint. Empty chain on 403; flag capability."""
        try:
            payload = self.http.request(f"v3/options-chain/{ticker}")
        except FMPEndpointForbidden:
            self._options_known_unavailable = True
            return OptionsChain(ticker, float("nan"), {}, self.name, datetime.utcnow())
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
