"""RESEARCH. Ticker Deep Dive workspace.

Runs the full deterministic Research pipeline and renders the results
in four phases. Phase rendering helpers live in
``_research_page_helpers.py``. The LLM memo phase is optional and
never blocks phases 1 to 3.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import styled_divider, styled_header  # noqa: E402

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

    styled_header(f"Research. {ticker}", "Deterministic pipeline | Sub scores | Memo synthesis")

    with st.spinner(f"Running research pipeline for {ticker}."):
        packet = run_pipeline(ticker, data_manager, config)

    if packet.get("status") == "hard_failure":
        st.markdown(unavailable_card(f"Cannot analyze {ticker}", packet["reason"]), unsafe_allow_html=True)
        return

    render_phase1_prices(packet)
    styled_divider()
    render_phase2_engines(packet)
    styled_divider()
    render_phase3_recommendation(packet)
    styled_divider()
    render_phase4_llm(packet, config)


render()
