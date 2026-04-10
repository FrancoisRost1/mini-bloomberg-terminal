"""RESEARCH: Ticker Deep Dive workspace.

Runs the full deterministic Research pipeline and renders results in
four phases: price + stats, engine cards, deterministic recommendation,
optional LLM memo. Phase rendering helpers live in
``_research_page_helpers.py``. LLM absence never blocks Phases 1-3.
"""

from __future__ import annotations

import streamlit as st

from terminal.adapters.research_adapter import run_pipeline
from terminal.utils.error_handling import unavailable_card

from ._research_page_helpers import (
    render_phase1_prices,
    render_phase2_engines,
    render_phase3_recommendation,
    render_phase4_llm,
)


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    ticker = st.session_state.get("active_ticker", "AAPL")

    st.title(f"Research: {ticker}")
    st.caption("Should I own this?")

    with st.spinner(f"Running research pipeline for {ticker}..."):
        packet = run_pipeline(ticker, data_manager, config)

    if packet.get("status") == "hard_failure":
        st.markdown(unavailable_card(f"Cannot analyze {ticker}", packet["reason"]), unsafe_allow_html=True)
        return

    render_phase1_prices(packet)
    render_phase2_engines(packet)
    render_phase3_recommendation(packet)
    render_phase4_llm(packet, config)


render()
