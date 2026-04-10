"""ANALYTICS: Comps & Relative Value workspace.

Peer comps table, relative valuation positioning, and a slice of the
M&A database for sector-matched deal multiples.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from terminal.adapters.ma_comps_adapter import run_comps
from terminal.adapters.pe_scoring_adapter import score_single_ticker
from terminal.utils.chart_helpers import bar_chart, interpretation_callout
from terminal.utils.error_handling import degraded_card, is_error, unavailable_card
from terminal.utils.formatting import badge, fmt_pct, fmt_ratio, format_metric, styled_kpi


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    ticker = st.session_state.get("active_ticker", "AAPL")

    st.title(f"Comps & Relative Value: {ticker}")
    st.caption("How does this name compare to its peers?")

    fundamentals = data_manager.get_fundamentals(ticker)
    if is_error(fundamentals):
        st.markdown(degraded_card(fundamentals.reason, fundamentals.provider), unsafe_allow_html=True)
        return

    sector = fundamentals.sector
    st.markdown(styled_kpi("Sector", sector), unsafe_allow_html=True)

    _render_valuation_card(fundamentals.key_ratios, config)
    _render_pe_score(fundamentals.key_ratios, config)
    _render_ma_comps(sector, config)


def _render_valuation_card(ratios, config) -> None:
    st.markdown("### Valuation Metrics")
    metrics = config["comps"]["metrics"]
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            fmt = m.get("format", "ratio")
            value = ratios.get(m["key"])
            st.markdown(styled_kpi(m["label"], format_metric(value, fmt)), unsafe_allow_html=True)


def _render_pe_score(ratios, config) -> None:
    st.markdown("### PE Target Screener Score")
    result = score_single_ticker(ratios, config["comps"]["pe_scoring_bands"])
    score = result["pe_score"]
    color = "#00C853" if score == score and score >= 60 else ("#FFAB00" if score == score and score >= 40 else "#FF3D57")
    st.markdown(styled_kpi("Composite PE Score", f"{score:.1f}" if score == score else "n/a", color), unsafe_allow_html=True)
    per_metric = {k: v for k, v in result["per_metric_scores"].items() if v == v}
    if per_metric:
        fig = bar_chart(per_metric, title="Per-Metric Score (0-100)", y_unit="score")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        interpretation_callout(
            observation=f"{len(result.get('red_flags', []))} red flag(s) detected.",
            interpretation="Score blends EBITDA margin, FCF conversion, leverage, ROIC, and valuation bands.",
            implication="Use this as a screening signal, not a buy-sell trigger.",
        ),
        unsafe_allow_html=True,
    )


def _render_ma_comps(sector, config) -> None:
    st.markdown("### Recent M&A Comps")
    project_root = Path(config["_meta"]["project_root"])
    allow_synthetic = bool(config["comps"].get("allow_synthetic_demo", False))
    comps = run_comps(
        sector=sector,
        project_root=project_root,
        max_rows=int(config["comps"]["max_peers"]),
        allow_synthetic=allow_synthetic,
    )
    if comps["status"] == "data_unavailable":
        st.markdown(
            unavailable_card("M&A comps unavailable", comps["reason"]),
            unsafe_allow_html=True,
        )
        return
    if comps.get("data_source") == "synthetic":
        st.markdown(
            badge("SYNTHETIC DEMO DATA -- NOT REAL DEALS", "#FFAB00"),
            unsafe_allow_html=True,
        )
    table = comps["comps_table"]
    if table.empty:
        st.markdown(degraded_card("no comps for sector", "ma_comps"), unsafe_allow_html=True)
        return
    st.dataframe(table, use_container_width=True, hide_index=True)


render()
