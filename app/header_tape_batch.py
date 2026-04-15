"""Batch ticker fetch for the header marquee.

The marquee used to make one provider call per tape item, which
caps the tape at ~10 items before cold renders feel slow. This
module runs a single ``yfinance.download`` call for the full tape
universe and returns a dict of ``label -> (price, change_pct)``
pairs. The result is cached via ``st.cache_data`` with a short TTL
so page navigation does not re-fetch.

The batch path is yfinance-only because that is where the tape
universe lives (indices, sector ETFs, FX, commodities, crypto).
FMP stays on the single-stock route for the Research pipeline.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pandas as pd
import streamlit as st

from terminal.data._yfinance_session import get_hardened_session


@lru_cache(maxsize=1)
def _session():
    return get_hardened_session()


# Display label -> yfinance symbol. Order is the order on the tape.
# Tape target: 30+ items so the marquee always reads dense.
TAPE_UNIVERSE: list[tuple[str, str]] = [
    # Indices and flagship ETFs
    ("SPY",     "SPY"),
    ("QQQ",     "QQQ"),
    ("DJI",     "^DJI"),
    ("IWM",     "IWM"),
    ("VIX",     "^VIX"),
    # Mega caps
    ("AAPL",    "AAPL"),
    ("MSFT",    "MSFT"),
    ("NVDA",    "NVDA"),
    ("AMZN",    "AMZN"),
    ("GOOGL",   "GOOGL"),
    ("META",    "META"),
    ("TSLA",    "TSLA"),
    ("JPM",     "JPM"),
    ("V",       "V"),
    ("JNJ",     "JNJ"),
    ("WMT",     "WMT"),
    ("PG",      "PG"),
    # Sector ETFs
    ("XLK",     "XLK"),
    ("XLF",     "XLF"),
    ("XLV",     "XLV"),
    ("XLY",     "XLY"),
    ("XLP",     "XLP"),
    ("XLE",     "XLE"),
    ("XLI",     "XLI"),
    ("XLB",     "XLB"),
    ("XLU",     "XLU"),
    ("XLRE",    "XLRE"),
    # Bonds
    ("TLT",     "TLT"),
    ("IEF",     "IEF"),
    ("HYG",     "HYG"),
    # FX + crypto + commodities
    ("EURUSD",  "EURUSD=X"),
    ("USDJPY",  "JPY=X"),
    ("BTCUSD",  "BTC-USD"),
    ("CL",      "CL=F"),
    ("GLD",     "GLD"),
]


@st.cache_data(ttl=300, show_spinner=False)
def fetch_tape_batch() -> dict[str, dict[str, Any]]:
    """One batched yfinance.download for the full tape universe.

    Returns ``{label: {"price": float, "change_pct": float} | None}``.
    Missing / failed tickers are omitted entirely from the dict. The
    5 minute TTL keeps the marquee cheap across page navigation; the
    marquee itself animates via CSS and never triggers a rerun.
    """
    try:
        import yfinance as yf
    except ImportError:
        return {}
    symbols = [sym for _label, sym in TAPE_UNIVERSE]
    try:
        df = yf.download(
            tickers=symbols,
            period="5d",
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            threads=True,
            progress=False,
            session=_session(),
        )
    except Exception:
        return {}
    if df is None or df.empty:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for label, sym in TAPE_UNIVERSE:
        try:
            if isinstance(df.columns, pd.MultiIndex):
                if sym not in df.columns.get_level_values(0):
                    continue
                closes = df[sym]["Close"].dropna()
            else:
                closes = df["Close"].dropna() if "Close" in df.columns else pd.Series(dtype=float)
            if closes.empty or len(closes) < 2:
                continue
            last = float(closes.iloc[-1])
            prev = float(closes.iloc[-2])
            if prev == 0 or pd.isna(last) or pd.isna(prev):
                continue
            out[label] = {"price": last, "change_pct": (last - prev) / prev}
        except Exception:
            continue
    return out
