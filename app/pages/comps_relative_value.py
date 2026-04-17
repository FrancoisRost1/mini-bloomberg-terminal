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
from terminal.utils.skeletons import chart_skeleton, kpi_skeleton, table_skeleton  # noqa: E402


def render() -> None:
    """Progressive render: page skeleton first, then data.

    Cold first load previously showed only section headers for ~27s while
    the peer fundamentals loop blocked on 5 sequential FMP fetches. The
    2026-04-17 audit flagged this as the biggest lead killer on Comps.
    Now the shell (header + all four section bars + placeholder bars/
    skeletons) renders immediately so the page feels alive from the first
    paint; each data region hydrates into its own st.empty() slot as the
    fetches return.
    """
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    ticker = st.session_state.get("active_ticker", "AAPL")

    styled_header(f"Comps Relative Value. {ticker}", "Single ticker valuation | PE score | M&A snapshot")
    st.markdown(section_bar("COMPS", source="FMP + local"), unsafe_allow_html=True)

    # Row 1: peer fundamentals. Section bar renders instantly; the
    # expensive loop (5 serial FMP fetches) runs inside a placeholder.
    st.markdown(section_bar("PEER FUNDAMENTALS + SECTOR MEDIAN", source="FMP"), unsafe_allow_html=True)
    peer_slot = table_skeleton(rows=6)

    # Row 2 skeletons: valuation card + scatter | historical range.
    row2_l, row2_r = st.columns([1, 1])
    with row2_l:
        val_kpi_slot = kpi_skeleton(rows=1, cells=6)
        scatter_slot = chart_skeleton(height=260)
    with row2_r:
        historical_slot = chart_skeleton(height=300)

    # Row 3 skeleton: PE score block.
    pe_slot = chart_skeleton(height=240)

    # Row 4 skeleton: M&A comps table.
    ma_slot = table_skeleton(rows=5)

    # Hydrate. The fundamentals call is the single most-cached blob so
    # we pull it once up front and reuse across every downstream render.
    fundamentals = data_manager.get_fundamentals(ticker)
    fund_ok = not is_error(fundamentals)
    ratios = fundamentals.key_ratios if fund_ok else {}
    sector = fundamentals.sector if fund_ok else ""

    peer_slot.empty()
    with peer_slot.container():
        render_peer_fundamentals(data_manager, ticker, sector, render_header=False)

    val_kpi_slot.empty()
    scatter_slot.empty()
    with val_kpi_slot.container():
        if fund_ok:
            render_valuation_card(fundamentals, config)
        else:
            st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
    with scatter_slot.container():
        if fund_ok:
            render_ev_growth_scatter(ticker, data_manager=data_manager, sector=sector)

    historical_slot.empty()
    with historical_slot.container():
        prices = data_manager.get_stock_prices(ticker, period="5y")
        close = prices.prices["close"] if not is_error(prices) and not prices.is_empty() else pd.Series(dtype=float)
        render_historical_valuation(fundamentals if fund_ok else None, close, ratios.get("ev_ebitda"))

    pe_slot.empty()
    with pe_slot.container():
        if fund_ok:
            render_pe_score(ratios, config)
        else:
            st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)

    ma_slot.empty()
    with ma_slot.container():
        render_ma_comps(sector or "Technology", config)


render()
