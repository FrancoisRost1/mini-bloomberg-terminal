"""Financial Modeling Prep production provider.

Uses ONLY the FMP stable/ endpoints. The v3/ endpoints all return 403
on the Starter tier; this was confirmed empirically by
``scripts/fmp_endpoint_audit.py`` and the v3 paths are no longer
exercised anywhere in the provider.

Endpoints:
- stable/quote                    single ticker quote
- stable/historical-price-eod/full daily OHLCV (full history)
- stable/profile                  company profile
- stable/income-statement         annual income statement
- stable/balance-sheet-statement  annual balance sheet
- stable/cash-flow-statement      annual cash flow

This provider serves single ticker stock data. ETF / index history,
options chains, and macro series are routed to other providers by
``ProviderRegistry``. ``supports_options_chain`` returns False
unconditionally; the navigation layer routes Options Lab to yfinance.

HTTP layer (rate limit, retry, 403 detection) lives in _fmp_http.py.
Parsers live in _fmp_parsers.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from . import _fmp_parsers as parsers
from ._fmp_http import FMPHttp
from .provider_interface import MarketDataProvider
from .schemas import Fundamentals, MacroData, OptionsChain, PriceData


class FMPProvider(MarketDataProvider):
    """Production market data provider backed by Financial Modeling Prep."""

    name = "fmp"
    is_dev_only = False

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        self.http = FMPHttp(config)

    @property
    def api_key(self) -> str:
        return self.http.api_key

    def supports_options_chain(self) -> bool:
        """FMP Starter never serves options. Routed to yfinance instead."""
        return False

    def get_prices(self, ticker: str, period: str = "1y") -> PriceData:
        payload = self.http.request("stable/historical-price-eod/full", {"symbol": ticker})
        prices = parsers.parse_historical(payload, period)
        return PriceData(ticker, prices, "USD", self.name, datetime.utcnow(), period)

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        profile_payload = self.http.request("stable/profile", {"symbol": ticker})
        quote_payload = self.http.request("stable/quote", {"symbol": ticker})
        income = parsers.parse_statement(
            self.http.request("stable/income-statement", {"symbol": ticker, "limit": "5"})
        )
        balance = parsers.parse_statement(
            self.http.request("stable/balance-sheet-statement", {"symbol": ticker, "limit": "5"})
        )
        cashflow = parsers.parse_statement(
            self.http.request("stable/cash-flow-statement", {"symbol": ticker, "limit": "5"})
        )
        profile = profile_payload[0] if isinstance(profile_payload, list) and profile_payload else {}
        quote = quote_payload[0] if isinstance(quote_payload, list) and quote_payload else {}
        ratios = parsers.compute_ratios(profile, quote, income, balance, cashflow)
        return Fundamentals(
            ticker=ticker,
            income_statement=income,
            balance_sheet=balance,
            cash_flow=cashflow,
            key_ratios=ratios,
            market_cap=parsers.safe_float(profile.get("mktCap") or profile.get("marketCap")),
            sector=str(profile.get("sector", "Unknown")),
            industry=str(profile.get("industry", "Unknown")),
            provider=self.name,
            as_of=datetime.utcnow(),
        )

    def get_macro(self, series: list[str]) -> MacroData:
        raise NotImplementedError("Use FredProvider for macro data")

    def get_options_chain(self, ticker: str) -> OptionsChain:
        raise NotImplementedError("Use YFinanceProvider for options chains; FMP Starter does not include options.")

    def healthcheck(self) -> bool:
        return bool(self.api_key)
