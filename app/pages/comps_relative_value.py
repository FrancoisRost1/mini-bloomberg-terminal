"""ANALYTICS. Comps Relative Value workspace.

Orchestrator only. The actual renderers live in sibling helper modules:
  _comps_peers        : peer fundamentals table + sector median row
  _comps_charts       : PE scoring bars + EV/growth scatter
  _comps_historical   : 5Y EV/EBITDA range with current marker
  _comps_renderers    : valuation KPI card, PE score, M&A comps table
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from style_inject import styled_header  # noqa: E402

from app.pages._comps_charts import render_ev_growth_scatter  # noqa: E402
from app.pages._comps_historical import render_historical_valuation  # noqa: E402
from app.pages._comps_peers import render_peer_fundamentals  # noqa: E402
from app.pages._comps_renderers import (  # noqa: E402
    render_ma_comps,
    render_pe_score,
    render_valuation_card,
)
from terminal.utils.density import section_bar  # noqa: E402
from terminal.utils.error_handling import inline_status_line, is_error  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    ticker = st.session_state.get("active_ticker", "AAPL")

    styled_header(f"Comps Relative Value. {ticker}", "Single ticker valuation | PE score | M&A snapshot")
    st.markdown(section_bar("COMPS", source="FMP + local"), unsafe_allow_html=True)

    fundamentals = data_manager.get_fundamentals(ticker)
    fund_ok = not is_error(fundamentals)
    ratios = fundamentals.key_ratios if fund_ok else {}
    sector = fundamentals.sector if fund_ok else ""

    tab_peers, tab_val, tab_hist, tab_pe, tab_ma = st.tabs(
        ["PEER FUNDAMENTALS", "VALUATION METRICS", "HISTORICAL RANGE", "PE SCORE", "M&A COMPS"]
    )
    with tab_peers:
        render_peer_fundamentals(data_manager, ticker, sector)
    with tab_val:
        if fund_ok:
            render_valuation_card(fundamentals, config)
            render_ev_growth_scatter(
                ticker,
                ratios.get("ev_ebitda"),
                ratios.get("revenue_growth"),
            )
        else:
            st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
    with tab_hist:
        prices = data_manager.get_stock_prices(ticker, period="5y")
        close = prices.prices["close"] if not is_error(prices) and not prices.is_empty() else pd.Series(dtype=float)
        render_historical_valuation(fundamentals if fund_ok else None, close, ratios.get("ev_ebitda"))
    with tab_pe:
        if fund_ok:
            render_pe_score(ratios, config)
        else:
            st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
    with tab_ma:
        render_ma_comps(sector or "Technology", config)


render()
