"""RESEARCH: Ticker Deep Dive workspace.

Runs the full deterministic Research pipeline and renders results in
four phases: price + stats, engine cards, deterministic recommendation,
optional LLM memo. Phase rendering helpers live in
``_research_page_helpers.py``. LLM absence never blocks Phases 1-3.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap project root for the streamlit-as-script load path.
# See app/app.py docstring for the rationale.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from app.pages._research_page_helpers import (  # noqa: E402
    render_phase1_prices,
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
