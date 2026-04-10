"""Sector ETF heatmap for the Market Overview workspace.

Plotly treemap colored by 1D return on the 11 sector ETFs declared in
``config.market.breadth.universe``. Cells are sized by the sector ETF
fund AUM so XLK (the largest sector ETF by assets) visually dominates
and XLRE (the smallest) sits in a corner, which matches how a Bloomberg
sector monitor reads. Lives in its own file to keep
``_market_overview_helpers.py`` under the line budget.
"""

from __future__ import annotations

import streamlit as st

from terminal.utils.chart_helpers import sector_treemap
from terminal.utils.density import section_bar
from terminal.utils.error_handling import degraded_card, is_error


# Approximate fund AUM (USD billions) for each sector ETF. Updated
# 2026-Q1. These are static proxies for how the sector-weighted view
# should look; exact accuracy is not required because the treemap is a
# visual heuristic, not a settlement price. If an ETF is missing here
# it falls back to a 1B floor via the sector_treemap helper.
SECTOR_ETF_AUM_USD_BN: dict[str, float] = {
    "XLK":  72.0,  # Technology
    "XLF":  50.0,  # Financials
    "XLV":  38.0,  # Health Care
    "XLY":  22.0,  # Consumer Discretionary
    "XLI":  20.0,  # Industrials
    "XLE":  38.0,  # Energy
    "XLP":  17.0,  # Consumer Staples
    "XLC":  20.0,  # Communication Services
    "XLU":  17.0,  # Utilities
    "XLB":   6.0,  # Materials
    "XLRE":  7.0,  # Real Estate
}


def render_sector_heatmap(data_manager, config) -> None:
    universe = config["market"]["breadth"]["universe"]
    st.markdown(section_bar("SECTOR HEATMAP (1D)", source="yfinance"), unsafe_allow_html=True)
    labels: list[str] = []
    returns_pct: list[float] = []
    sizes: list[float] = []
    for ticker in universe:
        data = data_manager.get_index_prices(ticker, period="1mo")
        if is_error(data) or data.is_empty() or len(data.prices) < 2:
            continue
        closes = data.prices["close"]
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])
        if prev == 0:
            continue
        labels.append(ticker)
        returns_pct.append((last / prev - 1) * 100)
        sizes.append(SECTOR_ETF_AUM_USD_BN.get(ticker, 1.0))
    if not labels:
        st.markdown(degraded_card("no sector ETF data", "registry"), unsafe_allow_html=True)
        return
    st.plotly_chart(
        sector_treemap(
            labels, returns_pct,
            title="Sector ETFs. sized by fund AUM, color by 1D return",
            sizes=sizes,
        ),
        use_container_width=True,
    )
