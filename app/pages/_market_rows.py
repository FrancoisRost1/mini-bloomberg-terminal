"""Market Overview dense KPI rows.

Split out of _market_extras.py so both modules stay under the line
budget. Each function returns nothing and renders a ``section_bar``
+ ``dense_kpi_row`` pair directly via Streamlit. Providers are
yfinance only; FRED and FMP are not touched here.
"""

from __future__ import annotations

import streamlit as st

from terminal.utils.density import dense_kpi_row, section_bar, signed_color
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


def render_gainers_losers(data_manager, config) -> None:
    """Top 3 gainers and losers from the sector ETF universe by 1D return.

    Reuses ``config.market.breadth.universe`` so the source list stays
    config driven and the same 11 ETFs that drive the heatmap drive
    this row.
    """
    universe = config["market"]["breadth"]["universe"]
    rows: list[tuple[str, float, float]] = []
    for ticker in universe:
        data = data_manager.get_index_prices(ticker, period="1mo")
        if is_error(data) or data.is_empty() or len(data.prices) < 2:
            continue
        closes = data.prices["close"]
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])
        if prev == 0:
            continue
        rows.append((ticker, last, (last / prev) - 1.0))
    rows.sort(key=lambda r: r[2], reverse=True)
    gainers = rows[:3]
    losers = list(reversed(rows[-3:])) if len(rows) >= 3 else []

    st.markdown(section_bar("TOP MOVERS (SECTOR ETF, 1D)", source="yfinance"), unsafe_allow_html=True)
    items: list[dict] = []
    for tkr, px, chg in gainers:
        items.append({
            "label": f"GAIN {tkr}", "value": f"{px:,.2f}",
            "delta": f"+{chg * 100:.2f}%", "delta_color": signed_color(chg),
            "value_color": signed_color(chg),
        })
    for tkr, px, chg in losers:
        items.append({
            "label": f"LOSS {tkr}", "value": f"{px:,.2f}",
            "delta": f"{chg * 100:+.2f}%", "delta_color": signed_color(chg),
            "value_color": signed_color(chg),
        })
    if not items:
        st.caption("DATA OFF | no sector ETF data available")
        return
    st.markdown(dense_kpi_row(items, min_cell_px=130), unsafe_allow_html=True)
