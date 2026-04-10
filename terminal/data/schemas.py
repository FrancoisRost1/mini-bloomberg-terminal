"""Normalized data schemas.

Every provider returns these dataclasses. The UI and adapters are forbidden
from touching provider-specific payloads directly; they must work off these
schemas so swapping providers never leaks into downstream code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass
class PriceData:
    """OHLCV price history for a single ticker.

    prices columns (lowercase): open, high, low, close, volume, adj_close.
    Index is a DatetimeIndex in trading-day order (ascending).
    """

    ticker: str
    prices: pd.DataFrame
    currency: str
    provider: str
    as_of: datetime
    period: str

    def is_empty(self) -> bool:
        return self.prices is None or self.prices.empty

    def last_close(self) -> float:
        if self.is_empty():
            return float("nan")
        return float(self.prices["close"].iloc[-1])


@dataclass
class Fundamentals:
    """Annual financial statements and key ratios for a single ticker.

    Ratios used downstream: pe_ratio, ev_ebitda, roic, ebitda_margin,
    fcf_conversion, net_debt_ebitda, interest_coverage, revenue_growth.
    """

    ticker: str
    income_statement: pd.DataFrame
    balance_sheet: pd.DataFrame
    cash_flow: pd.DataFrame
    key_ratios: dict[str, float]
    market_cap: float
    sector: str
    industry: str
    provider: str
    as_of: datetime

    def has_financials(self) -> bool:
        """Research workspace uses this as the hard-fail gate."""
        return not (self.income_statement is None or self.income_statement.empty)


@dataclass
class MacroData:
    """Macro time series bundle keyed by series id (FRED convention)."""

    series: dict[str, pd.Series]
    provider: str
    as_of: datetime

    def latest(self, series_id: str) -> float:
        s = self.series.get(series_id)
        if s is None or s.empty:
            return float("nan")
        return float(s.dropna().iloc[-1])


@dataclass
class OptionsChain:
    """Options chain grouped by expiry date (ISO string).

    Each expiry DataFrame has columns: strike, bid, ask, last, volume,
    open_interest, implied_volatility (when the provider returns it),
    type ('call' or 'put').
    """

    ticker: str
    spot: float
    chains: dict[str, pd.DataFrame]
    provider: str
    as_of: datetime

    def expiries(self) -> list[str]:
        return sorted(self.chains.keys())

    def is_empty(self) -> bool:
        return not self.chains or all(df.empty for df in self.chains.values())


@dataclass
class ProviderError:
    """Returned instead of raising, so the UI can render DEGRADED states
    without crashing on every data path failure.
    """

    provider: str
    ticker: str
    data_type: str
    reason: str
    raised_at: datetime = field(default_factory=datetime.utcnow)

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "ticker": self.ticker,
            "data_type": self.data_type,
            "reason": self.reason,
            "raised_at": self.raised_at.isoformat(),
        }
