"""RESEARCH. Ticker Deep Dive workspace. 2x2 multi pane layout."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import styled_header  # noqa: E402

from app.pages._research_page_helpers import (  # noqa: E402
    render_phase1_chart,
    render_phase1_stats,
    render_phase2_engines,
    render_phase3_recommendation,
    render_phase4_llm,
)
from terminal.adapters.research_adapter import run_pipeline  # noqa: E402
from terminal.utils.error_handling import unavailable_card  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    ticker = st.session_state.get("active_ticker", "AAPL")

    styled_header(f"Research. {ticker}", "Deterministic pipeline | Sub scores | Memo synthesis")

    with st.spinner(f"Running research pipeline for {ticker}."):
        packet = run_pipeline(ticker, data_manager, config)

    if packet.get("status") == "hard_failure":
        st.markdown(unavailable_card(f"Cannot analyze {ticker}", packet["reason"]), unsafe_allow_html=True)
        return

    row1_l, row1_r = st.columns([1, 1])
    with row1_l:
        render_phase1_chart(packet)
    with row1_r:
        render_phase1_stats(packet)

    row2_l, row2_r = st.columns([1, 1])
    with row2_l:
        render_phase2_engines(packet)
        render_phase3_recommendation(packet)
    with row2_r:
        render_phase4_llm(packet, config)


render()
