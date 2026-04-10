"""Fake market data provider for offline tests.

Used by both the manager tests and the integration tests (Research
pipeline, Portfolio workflow). Deterministic synthetic prices and
fundamentals, with a switch to force failure paths for DEGRADED-state
tests. Never touches the network.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from terminal.data.provider_interface import MarketDataProvider
from terminal.data.schemas import Fundamentals, MacroData, OptionsChain, PriceData


class FakeProvider(MarketDataProvider):
    """Synthetic provider that returns reproducible data for any ticker.

    Pass ``fail_on`` to force specific tickers to raise, so tests can
    exercise the manager's error-path wrapping.
    """

    name = "fake"
    is_dev_only = True

    def __init__(self, config: dict[str, Any], fail_on: set[str] | None = None):
        self.cfg = config
        self.fail_on = fail_on or set()
        self.call_counts: dict[str, int] = {}

    def _tick(self, key: str) -> None:
        self.call_counts[key] = self.call_counts.get(key, 0) + 1

    def _guard(self, ticker: str, data_type: str) -> None:
        if ticker in self.fail_on:
            raise RuntimeError(f"forced failure for {ticker} ({data_type})")

    def get_prices(self, ticker: str, period: str = "1y") -> PriceData:
        self._tick(f"prices:{ticker}")
        self._guard(ticker, "prices")
        rng = np.random.default_rng(abs(hash(ticker)) % (2 ** 32))
        n = 400
        returns = rng.normal(0.0005, 0.012, n)
        closes = 100 * np.cumprod(1 + returns)
        idx = pd.date_range("2023-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "open": closes * 0.999,
            "high": closes * 1.005,
            "low": closes * 0.995,
            "close": closes,
            "adj_close": closes,
            "volume": rng.integers(1_000_000, 5_000_000, n),
        }, index=idx)
        return PriceData(ticker, df, "USD", self.name, datetime.utcnow(), period)

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        self._tick(f"fundamentals:{ticker}")
        self._guard(ticker, "fundamentals")
        income = pd.DataFrame(
            {"totalRevenue": [900.0, 1000.0, 1100.0], "ebitda": [180.0, 220.0, 250.0]},
            index=pd.to_datetime(["2021-12-31", "2022-12-31", "2023-12-31"]),
        )
        balance = pd.DataFrame(
            {"shortLongTermDebtTotal": [300.0, 350.0, 380.0], "cashAndCashEquivalentsAtCarryingValue": [100.0, 120.0, 150.0]},
            index=income.index,
        )
        cashflow = pd.DataFrame(
            {"operatingCashflow": [160.0, 200.0, 230.0], "capitalExpenditures": [-40.0, -50.0, -60.0]},
            index=income.index,
        )
        ratios = {
            "pe_ratio": 18.0, "ev_ebitda": 11.0, "ebitda_margin": 0.22,
            "fcf_conversion": 0.76, "roe": 0.18, "revenue_growth": 0.10,
            "net_debt_ebitda": 1.8, "interest_coverage": 7.5, "dividend_yield": 0.015, "beta": 1.1,
        }
        return Fundamentals(
            ticker=ticker, income_statement=income, balance_sheet=balance, cash_flow=cashflow,
            key_ratios=ratios, market_cap=5.0e9, sector="Technology", industry="Software",
            provider=self.name, as_of=datetime.utcnow(),
        )

    def get_macro(self, series: list[str]) -> MacroData:
        self._tick("macro")
        out: dict[str, pd.Series] = {}
        idx = pd.date_range("2020-01-01", periods=500, freq="B")
        for sid in series:
            rng = np.random.default_rng(abs(hash(sid)) % (2 ** 32))
            out[sid] = pd.Series(4.0 + rng.normal(0, 0.05, 500).cumsum() * 0.01, index=idx, name=sid)
        return MacroData(series=out, provider=self.name, as_of=datetime.utcnow())

    def get_options_chain(self, ticker: str) -> OptionsChain:
        self._tick(f"options:{ticker}")
        self._guard(ticker, "options")
        strikes = np.linspace(80, 120, 9)
        calls = pd.DataFrame({
            "strike": strikes, "bid": np.maximum(100 - strikes + 2, 0.1),
            "ask": np.maximum(100 - strikes + 2.5, 0.2), "last": np.maximum(100 - strikes + 2.2, 0.15),
            "volume": [100] * 9, "open_interest": [500] * 9, "type": ["call"] * 9,
        })
        puts = calls.copy()
        puts["type"] = "put"
        puts["bid"] = np.maximum(strikes - 100 + 2, 0.1)
        puts["ask"] = np.maximum(strikes - 100 + 2.5, 0.2)
        puts["last"] = np.maximum(strikes - 100 + 2.2, 0.15)
        chain = pd.concat([calls, puts], ignore_index=True)
        return OptionsChain(ticker, 100.0, {"2025-06-20": chain}, self.name, datetime.utcnow())

    def healthcheck(self) -> bool:
        return True
