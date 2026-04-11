"""Research page rendering helpers. Tolerant of missing data."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app.pages._research_engine_renderers import (
    render_engine_grid as render_phase2_engines,  # noqa: F401  re export
    render_llm_memo as render_phase4_llm,  # noqa: F401  re export
)
from app.pages._research_financials import (
    render_52w_range_bar,
    render_financials_table,
)
from app.pages._research_visuals import (
    render_phase3_recommendation as render_phase3_recommendation,  # noqa: F401  re export
)
from terminal.utils.chart_helpers import line_chart
from terminal.utils.density import dense_kpi_rows, period_returns_tape, section_bar, signed_color
from terminal.utils.error_handling import inline_status_line, is_error
from terminal.utils.formatting import fmt_money, fmt_pct, fmt_ratio, fmt_ratio_with_note
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


_PERIOD_CHOICES: list[tuple[str, str]] = [
    ("1M", "1mo"),
    ("3M", "3mo"),
    ("6M", "6mo"),
    ("1Y", "1y"),
    ("2Y", "2y"),
    ("5Y", "5y"),
]


def render_phase1_chart(packet: dict[str, Any], data_manager=None) -> None:
    prices_obj = packet.get("prices")
    close = _close_series(packet)
    tape = period_returns_tape(close) if close is not None else ""
    st.markdown(section_bar("PRICE", tape=tape, source="FMP"), unsafe_allow_html=True)
    if close is None or prices_obj is None or is_error(prices_obj):
        st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
        return
    ticker = packet["ticker"]
    ctrl_l, ctrl_r = st.columns([3, 4])
    with ctrl_l:
        view = st.radio(
            "Chart view",
            options=["Candlestick", "Line"],
            index=0,
            horizontal=True,
            key=f"chart_view_{ticker}",
            label_visibility="collapsed",
        )
    with ctrl_r:
        period_label = st.radio(
            "Period",
            options=[p[0] for p in _PERIOD_CHOICES],
            index=3,  # default 1Y
            horizontal=True,
            key=f"chart_period_{ticker}",
            label_visibility="collapsed",
        )
    period_key = dict(_PERIOD_CHOICES)[period_label]

    # Refetch for the chosen period when the user changes it. The
    # default_price_period in config stays authoritative for the rest
    # of the pipeline; this override is chart only.
    if data_manager is not None and period_key != prices_obj.period:
        refetched = data_manager.get_stock_prices(ticker, period_key)
        if not is_error(refetched) and not refetched.is_empty():
            prices_obj = refetched
            close = refetched.prices["close"]

    placeholder = chart_skeleton(height=380)
    if view == "Candlestick":
        html = build_tv_chart_html(prices_obj.prices, ticker, height_px=380)
        placeholder.empty()
        components.html(html, height=390)
    else:
        fig = line_chart({ticker: close}, title=f"{ticker} price ({period_label})", y_unit="USD")
        placeholder.empty()
        st.plotly_chart(fig, use_container_width=True)


def render_phase1_stats(packet: dict[str, Any]) -> None:
    st.markdown(section_bar("KEY STATS", source="FMP"), unsafe_allow_html=True)
    fundamentals = packet.get("fundamentals")
    ratios = _ratios(packet)
    notes = ratios.get("_notes") if isinstance(ratios, dict) else None
    market_cap = getattr(fundamentals, "market_cap", float("nan")) if fundamentals and not is_error(fundamentals) else float("nan")
    rev_growth = ratios.get("revenue_growth")
    # Two rows of six. First row = "what does the market pay": size,
    # valuation, profitability. Second row = growth + balance sheet
    # + income mix. This keeps labels from clipping and groups the
    # metrics by the question they answer.
    items = [
        {"label": "MARKET CAP", "value": fmt_money(market_cap)},
        {"label": "P/E", "value": fmt_ratio(ratios.get("pe_ratio"), suffix="")},
        {"label": "EV/EBITDA", "value": fmt_ratio(ratios.get("ev_ebitda"))},
        {"label": "EBITDA MARGIN", "value": fmt_pct(ratios.get("ebitda_margin"))},
        {"label": "FCF CONV", "value": fmt_pct(ratios.get("fcf_conversion"))},
        {"label": "ROE", "value": fmt_pct(ratios.get("roe"))},
        {"label": "REV GROWTH", "value": fmt_pct(rev_growth), "value_color": signed_color(rev_growth)},
        {"label": "ND/EBITDA", "value": fmt_ratio(ratios.get("net_debt_ebitda"))},
        {"label": "INT COVERAGE", "value": fmt_ratio_with_note(
            ratios.get("interest_coverage"), notes, "interest_coverage")},
        {"label": "BETA", "value": fmt_ratio(ratios.get("beta"), suffix="")},
        {"label": "DIV YIELD", "value": fmt_pct(ratios.get("dividend_yield"))},
    ]
    st.markdown(dense_kpi_rows(items, rows=2, min_cell_px=125), unsafe_allow_html=True)
    close = _close_series(packet)
    render_52w_range_bar(close)
    if fundamentals is None or is_error(fundamentals):
        st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
        return
    render_financials_table(fundamentals)




