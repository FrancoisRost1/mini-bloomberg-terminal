"""RESEARCH. Ticker Deep Dive workspace.

Always renders the full 2x2 skeleton. Each phase fills with whatever
data is available and shows an inline status pill where data is
missing. The page never collapses to a void.
"""

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
from terminal.adapters.research_adapter import run_pipeline
from terminal.utils.error_handling import dev_detail_caption, safe_render
from terminal.utils.skeletons import chart_skeleton, kpi_skeleton


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    ticker = st.session_state.get("active_ticker", "AAPL")

    styled_header(f"Research. {ticker}", "Deterministic pipeline | Sub scores | Memo synthesis")

    # Fetch the raw building blocks BEFORE the pipeline runs so Phase 1
    # KPIs always have data to render, even when a downstream engine
    # raises and the pipeline is reduced to a hard_failure packet.
    raw_prices = data_manager.get_stock_prices(ticker, config["research"]["default_price_period"])
    raw_fundamentals = data_manager.get_fundamentals(ticker)

    chart_slot = chart_skeleton(height=380)
    kpi_slot = kpi_skeleton(rows=2, cells=6)
    with st.spinner(f"Running research pipeline for {ticker}."):
        try:
            packet = run_pipeline(ticker, data_manager, config)
        except Exception as exc:
            packet = {"status": "hard_failure", "ticker": ticker, "reason": "pipeline error"}
            dev_detail_caption(f"run_pipeline raised: {type(exc).__name__}: {exc}")
    chart_slot.empty()
    kpi_slot.empty()

    # Build a partial packet so the skeleton always has something to render.
    packet.setdefault("ticker", ticker)
    packet.setdefault("engines", {})
    packet.setdefault("recommendation", {
        "rating": "INSUFFICIENT_DATA", "composite_score": float("nan"),
        "confidence": 0.0, "confidence_grade": "F",
        "sub_scores": {}, "override_reason": None, "rule_trace": [],
    })
    packet.setdefault("scenarios", [])
    # Inject raw price + fundamentals into the packet if the pipeline
    # itself did not. On success these are already present (same
    # objects, since data_manager is cache-backed). On hard_failure the
    # key is absent and Phase 1 would otherwise show all n/a.
    packet.setdefault("prices", raw_prices)
    packet.setdefault("fundamentals", raw_fundamentals)

    row1_l, row1_r = st.columns([1, 1])
    with row1_l:
        safe_render(lambda: render_phase1_chart(packet), label="phase1_chart", source="FMP")
    with row1_r:
        safe_render(lambda: render_phase1_stats(packet), label="phase1_stats", source="FMP")

    row2_l, row2_r = st.columns([1, 1])
    with row2_l:
        safe_render(lambda: render_phase2_engines(packet), label="phase2_engines", source="FMP")
        safe_render(lambda: render_phase3_recommendation(packet), label="phase3_recommendation", source="local")
    with row2_r:
        safe_render(lambda: render_phase4_llm(packet, config), label="phase4_llm", source="anthropic")


render()
