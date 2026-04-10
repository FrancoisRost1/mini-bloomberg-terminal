"""Sector ETF heatmap for the Market Overview workspace.

Equal-weight Plotly treemap colored by 1D return on the 11 sector
ETFs declared in ``config.market.breadth.universe``. Lives in its
own file to keep ``_market_overview_helpers.py`` under the line
budget.
"""

from __future__ import annotations

import streamlit as st

from terminal.utils.chart_helpers import sector_treemap
from terminal.utils.density import section_bar
from terminal.utils.error_handling import degraded_card, is_error


def render_sector_heatmap(data_manager, config) -> None:
    universe = config["market"]["breadth"]["universe"]
    st.markdown(section_bar("SECTOR HEATMAP (1D)", source="yfinance"), unsafe_allow_html=True)
    labels: list[str] = []
    returns_pct: list[float] = []
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
    if not labels:
        st.markdown(degraded_card("no sector ETF data", "registry"), unsafe_allow_html=True)
        return
    st.plotly_chart(
        sector_treemap(labels, returns_pct, title="Sector ETFs. equal weight, color by 1D return"),
        use_container_width=True,
    )
