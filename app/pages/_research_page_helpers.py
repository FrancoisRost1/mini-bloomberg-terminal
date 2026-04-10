"""Research page rendering helpers. Tolerant of missing data."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from style_inject import TOKENS

from app.pages._research_engine_renderers import (
    render_factor_engine,
    render_lbo_engine,
    render_llm_memo as render_phase4_llm,  # noqa: F401  re export
    render_pe_engine,
    render_tsmom_engine,
)
from app.pages._research_financials import (
    render_52w_range_bar,
    render_financials_table,
)
from app.pages._research_visuals import (
    render_phase3_recommendation as render_phase3_recommendation,  # noqa: F401  re export
    render_score_stacked_bar as _render_score_stacked_bar,  # noqa: F401
)
from terminal.utils.chart_helpers import line_chart
from terminal.utils.density import dense_kpi_row, period_returns_tape, section_bar, signed_color
from terminal.utils.error_handling import inline_status_line, is_error, status_pill
from terminal.utils.formatting import fmt_money, fmt_pct, fmt_ratio
from terminal.utils.skeletons import chart_skeleton
from terminal.utils.tv_chart import build_tv_chart_html


def _close_series(packet: dict[str, Any]) -> pd.Series | None:
    prices = packet.get("prices")
    if prices is None or is_error(prices):
        return None
    if not hasattr(prices, "prices") or prices.is_empty():
        return None
    return prices.prices["close"]


def _ratios(packet: dict[str, Any]) -> dict[str, Any]:
    f = packet.get("fundamentals")
    if f is None or is_error(f):
        return {}
    return getattr(f, "key_ratios", {}) or {}


def render_phase1_chart(packet: dict[str, Any]) -> None:
    prices_obj = packet.get("prices")
    close = _close_series(packet)
    tape = period_returns_tape(close) if close is not None else ""
    st.markdown(section_bar("PRICE", tape=tape, source="FMP"), unsafe_allow_html=True)
    if close is None or prices_obj is None or is_error(prices_obj):
        st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
        return
    view = st.radio(
        "Chart view",
        options=["Candlestick", "Line"],
        index=0,
        horizontal=True,
        key=f"chart_view_{packet['ticker']}",
        label_visibility="collapsed",
    )
    placeholder = chart_skeleton(height=380)
    if view == "Candlestick":
        html = build_tv_chart_html(prices_obj.prices, packet["ticker"], height_px=380)
        placeholder.empty()
        components.html(html, height=390)
    else:
        fig = line_chart({packet["ticker"]: close}, title=f"{packet['ticker']} price (1Y)", y_unit="USD")
        placeholder.empty()
        st.plotly_chart(fig, use_container_width=True)


def render_phase1_stats(packet: dict[str, Any]) -> None:
    st.markdown(section_bar("KEY STATS", source="FMP"), unsafe_allow_html=True)
    fundamentals = packet.get("fundamentals")
    ratios = _ratios(packet)
    market_cap = getattr(fundamentals, "market_cap", float("nan")) if fundamentals and not is_error(fundamentals) else float("nan")
    rev_growth = ratios.get("revenue_growth")
    items = [
        {"label": "MARKET CAP", "value": fmt_money(market_cap)},
        {"label": "P/E", "value": fmt_ratio(ratios.get("pe_ratio"), suffix="")},
        {"label": "EV/EBITDA", "value": fmt_ratio(ratios.get("ev_ebitda"))},
        {"label": "EBITDA MARGIN", "value": fmt_pct(ratios.get("ebitda_margin"))},
        {"label": "FCF CONV", "value": fmt_pct(ratios.get("fcf_conversion"))},
        {"label": "ROE", "value": fmt_pct(ratios.get("roe"))},
        {"label": "REV GROWTH", "value": fmt_pct(rev_growth), "value_color": signed_color(rev_growth)},
        {"label": "ND/EBITDA", "value": fmt_ratio(ratios.get("net_debt_ebitda"))},
        {"label": "INT COVERAGE", "value": fmt_ratio(ratios.get("interest_coverage"))},
        {"label": "BETA", "value": fmt_ratio(ratios.get("beta"), suffix="")},
        {"label": "DIV YIELD", "value": fmt_pct(ratios.get("dividend_yield"))},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=95), unsafe_allow_html=True)
    close = _close_series(packet)
    render_52w_range_bar(close)
    if fundamentals is None or is_error(fundamentals):
        st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
        return
    render_financials_table(fundamentals)


def render_phase2_engines(packet: dict[str, Any]) -> None:
    st.markdown(section_bar("ENGINE RESULTS", source="FMP"), unsafe_allow_html=True)
    engines = packet.get("engines") or {}
    tabs = st.tabs(["PE SCORING", "FACTOR EXPOSURE", "TSMOM SIGNAL", "LBO SNAPSHOT"])
    renderers = [
        ("pe_scoring", render_pe_engine),
        ("factor_exposure", render_factor_engine),
        ("tsmom", render_tsmom_engine),
        ("lbo", render_lbo_engine),
    ]
    for tab, (key, renderer) in zip(tabs, renderers):
        with tab:
            engine = engines.get(key, {})
            status = engine.get("status", "missing")
            st.markdown(status_pill(key.upper(), status), unsafe_allow_html=True)
            if engine.get("status") != "success":
                st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
                continue
            renderer(engine)


