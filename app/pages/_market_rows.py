"""Market Overview dense KPI rows.

Split out of _market_extras.py so both modules stay under the line
budget. Each function returns nothing and renders a ``section_bar``
+ ``dense_kpi_row`` pair directly via Streamlit. Providers are
yfinance only; FRED and FMP are not touched here.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from terminal.utils.density import colored_dataframe, dense_kpi_row, section_bar, signed_color
from terminal.utils.error_handling import is_error


# yfinance FX symbols. JPY, CHF, CAD quote USD -> X (so price is the
# amount of the quote currency per 1 USD). EUR / GBP / AUD quote USD
# in the reverse direction. All six read in the natural finance
# convention (base / quote).
FX_PAIRS: list[tuple[str, str]] = [
    ("EURUSD", "EURUSD=X"),
    ("GBPUSD", "GBPUSD=X"),
    ("USDJPY", "JPY=X"),
    ("USDCHF", "CHF=X"),
    ("AUDUSD", "AUDUSD=X"),
    ("USDCAD", "CAD=X"),
]


# yfinance front-month futures tickers for the main commodity complex.
COMMODITY_TICKERS: list[tuple[str, str, int]] = [
    # (label, yfinance ticker, display decimals)
    ("WTI CRUDE", "CL=F", 2),
    ("GOLD",      "GC=F", 1),
    ("SILVER",    "SI=F", 2),
    ("COPPER",    "HG=F", 3),
    ("NAT GAS",   "NG=F", 3),
]


def _build_last_chg_item(label: str, data, decimals: int) -> dict:
    if is_error(data) or data.is_empty() or len(data.prices) < 2:
        return {"label": label, "value": "n/a"}
    closes = data.prices["close"]
    last = float(closes.iloc[-1])
    prev = float(closes.iloc[-2])
    chg = (last / prev - 1.0) if prev else 0.0
    return {
        "label": label,
        "value": f"{last:,.{decimals}f}",
        "delta": f"{chg * 100:+.2f}%",
        "delta_color": signed_color(chg),
        "value_color": signed_color(chg),
    }


def render_fx_row(data_manager) -> None:
    """KPI row for six FX majors with 1D move."""
    st.markdown(section_bar("FX MAJORS", source="yfinance"), unsafe_allow_html=True)
    items = [
        _build_last_chg_item(label, data_manager.get_index_prices(ticker, period="1mo"), 4)
        for label, ticker in FX_PAIRS
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=130), unsafe_allow_html=True)


def render_commodities_row(data_manager) -> None:
    """KPI row for the five flagship commodity futures with 1D move."""
    st.markdown(section_bar("COMMODITIES", source="yfinance"), unsafe_allow_html=True)
    items = [
        _build_last_chg_item(label, data_manager.get_index_prices(ticker, period="1mo"), dec)
        for label, ticker, dec in COMMODITY_TICKERS
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=130), unsafe_allow_html=True)


# Broader mover universe: 11 sector ETFs from config + 11 mega caps +
# 4 flagship ETFs so the Top Movers table fills the right column to
# the same depth as the Market Breadth table on the left (11 rows).
_MOVER_MEGA_CAPS: list[str] = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "JPM", "V", "JNJ", "WMT",
]
_MOVER_FLAGSHIP_ETFS: list[str] = ["SPY", "QQQ", "IWM", "DIA", "TLT", "HYG", "GLD"]


def render_gainers_losers(data_manager, config) -> None:
    """Broad 1D movers table across sector ETFs, mega caps, and ETFs.

    Replaces the prior 3 gainers / 3 losers KPI strip. The table
    pulls every ticker in ``config.market.breadth.universe`` plus a
    fixed list of mega caps and flagship ETFs, sorts by 1D change,
    and renders the full sorted list. Reads like a real market
    movers board, not a highlight reel, and fills the right column
    to match the depth of the left column breadth table.
    """
    st.markdown(section_bar("TOP MOVERS (1D, SORTED)", source="yfinance"), unsafe_allow_html=True)
    sector_etfs = list(config["market"]["breadth"]["universe"])
    tickers: list[str] = sector_etfs + _MOVER_FLAGSHIP_ETFS + _MOVER_MEGA_CAPS
    seen: set[str] = set()
    unique_tickers: list[str] = []
    for t in tickers:
        if t in seen:
            continue
        seen.add(t)
        unique_tickers.append(t)

    rows: list[dict] = []
    for ticker in unique_tickers:
        data = data_manager.get_any_prices(ticker, period="1mo")
        if is_error(data) or data.is_empty() or len(data.prices) < 2:
            continue
        closes = data.prices["close"]
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])
        week_prev = float(closes.iloc[-6]) if len(closes) >= 6 else prev
        if prev == 0 or week_prev == 0:
            continue
        chg_1d = (last / prev) - 1.0
        chg_5d = (last / week_prev) - 1.0
        rows.append({
            "Ticker":   ticker,
            "Last":     f"{last:,.2f}",
            "1D %":     f"{chg_1d * 100:+.2f}%",
            "5D %":     f"{chg_5d * 100:+.2f}%",
            "_chg_1d":  chg_1d,
        })

    if not rows:
        st.caption("DATA OFF | no mover data available")
        return

    rows.sort(key=lambda r: r["_chg_1d"], reverse=True)
    df = pd.DataFrame(rows).drop(columns=["_chg_1d"])
    st.dataframe(
        colored_dataframe(df, ["1D %", "5D %"]),
        use_container_width=True, hide_index=True,
    )
