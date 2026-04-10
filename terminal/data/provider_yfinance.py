"""yfinance provider -- LOCAL DEVELOPMENT ONLY.

Do not rely on this provider in production. yfinance scrapes Yahoo pages,
has no SLA, its ``dividendYield`` field is unreliable (use trailing annual
rate divided by spot instead), and its Treasury yield output is in percent
units and must be divided by 100.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from .provider_interface import MarketDataProvider
from .schemas import Fundamentals, MacroData, OptionsChain, PriceData


class YFinanceProvider(MarketDataProvider):
    """Development-only provider. Carries a DEV MODE flag for the UI."""

    name = "yfinance"
    is_dev_only = True

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        self.yf_cfg = config["data"]["yfinance"]

    def _yf(self):
        import yfinance as yf  # imported lazily so prod images without yfinance still boot
        return yf

    def get_prices(self, ticker: str, period: str = "1y") -> PriceData:
        yf = self._yf()
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=False)
        if hist is None or hist.empty:
            empty = pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume"])
            return PriceData(ticker, empty, "USD", self.name, datetime.utcnow(), period)
        hist = hist.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Adj Close": "adj_close", "Volume": "volume",
        })
        if "adj_close" not in hist.columns:
            hist["adj_close"] = hist["close"]
        hist = hist[["open", "high", "low", "close", "adj_close", "volume"]]
        return PriceData(ticker, hist, "USD", self.name, datetime.utcnow(), period)

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        yf = self._yf()
        t = yf.Ticker(ticker)
        info = getattr(t, "info", {}) or {}
        income = _safe_df(getattr(t, "income_stmt", None))
        balance = _safe_df(getattr(t, "balance_sheet", None))
        cashflow = _safe_df(getattr(t, "cashflow", None))
        ratios = self._ratios(info, income, cashflow)
        return Fundamentals(
            ticker=ticker,
            income_statement=income,
            balance_sheet=balance,
            cash_flow=cashflow,
            key_ratios=ratios,
            market_cap=float(info.get("marketCap") or 0.0),
            sector=str(info.get("sector", "Unknown")),
            industry=str(info.get("industry", "Unknown")),
            provider=self.name,
            as_of=datetime.utcnow(),
        )

    def _ratios(self, info: dict, income: pd.DataFrame, cashflow: pd.DataFrame) -> dict[str, float]:
        spot = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0)
        trailing = float(info.get("trailingAnnualDividendRate") or 0.0)
        div_yield = trailing / spot if spot else 0.0
        if div_yield > self.yf_cfg["dividend_yield_warning"]:
            div_yield = float("nan")
        ratios = {
            "pe_ratio": float(info.get("trailingPE") or float("nan")),
            "ev_ebitda": float(info.get("enterpriseToEbitda") or float("nan")),
            "ebitda_margin": float(info.get("ebitdaMargins") or float("nan")),
            "roic": float(info.get("returnOnEquity") or float("nan")),
            "dividend_yield": div_yield,
            "beta": float(info.get("beta") or float("nan")),
            "revenue_growth": float(info.get("revenueGrowth") or float("nan")),
        }
        return ratios

    def get_macro(self, series: list[str]) -> MacroData:
        yf = self._yf()
        divisor = float(self.yf_cfg["treasury_yield_divisor"])
        out: dict[str, pd.Series] = {}
        for sid in series:
            hist = yf.Ticker(sid).history(period="5y")
            if hist is None or hist.empty:
                out[sid] = pd.Series(dtype=float, name=sid)
                continue
            s = hist["Close"].rename(sid)
            if sid.startswith("^TNX") or sid.startswith("^TYX") or sid.startswith("^FVX"):
                s = s / divisor
            out[sid] = s
        return MacroData(series=out, provider=self.name, as_of=datetime.utcnow())

    def get_options_chain(self, ticker: str) -> OptionsChain:
        yf = self._yf()
        t = yf.Ticker(ticker)
        expiries = list(getattr(t, "options", ()) or ())
        spot = float((getattr(t, "info", {}) or {}).get("regularMarketPrice") or 0.0)
        chains: dict[str, pd.DataFrame] = {}
        for expiry in expiries:
            try:
                chain = t.option_chain(expiry)
            except Exception:
                continue
            calls = chain.calls.assign(type="call")
            puts = chain.puts.assign(type="put")
            both = pd.concat([calls, puts], ignore_index=True)
            both = both.rename(columns={"openInterest": "open_interest", "lastPrice": "last"})
            keep = [c for c in ["strike", "bid", "ask", "last", "volume", "open_interest", "type"] if c in both.columns]
            chains[str(expiry)] = both[keep].reset_index(drop=True)
        return OptionsChain(ticker, spot, chains, self.name, datetime.utcnow())

    def healthcheck(self) -> bool:
        try:
            self._yf()
            return True
        except Exception:
            return False


def _safe_df(obj: Any) -> pd.DataFrame:
    if obj is None:
        return pd.DataFrame()
    if isinstance(obj, pd.DataFrame):
        return obj.T if obj.shape[0] > obj.shape[1] else obj
    return pd.DataFrame()
