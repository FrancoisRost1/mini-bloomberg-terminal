"""Research page rendering helpers.

Split out of ``ticker_deep_dive.py`` so the page module stays under the
per-module line budget. Phase rendering functions live here; the page
file orchestrates the four phases.
"""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from terminal.synthesis.llm_client import generate_memo, is_available as llm_is_available
from terminal.utils.chart_helpers import interpretation_callout, line_chart
from terminal.utils.error_handling import degraded_card
from terminal.utils.formatting import badge, fmt_money, fmt_pct, fmt_ratio, styled_kpi


def render_phase1_prices(packet: dict[str, Any]) -> None:
    prices = packet["prices"]
    fundamentals = packet["fundamentals"]
    st.markdown("### Price and Key Stats")
    close = prices.prices["close"] if not prices.is_empty() else None
    if close is None:
        st.markdown(degraded_card("no price series", prices.provider), unsafe_allow_html=True)
        return
    fig = line_chart({packet["ticker"]: close}, title=f"{packet['ticker']} Price (1Y)", y_unit="USD")
    st.plotly_chart(fig, use_container_width=True)
    ratios = fundamentals.key_ratios
    cols = st.columns(5)
    with cols[0]:
        st.markdown(styled_kpi("Market Cap", fmt_money(fundamentals.market_cap)), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(styled_kpi("P/E", fmt_ratio(ratios.get("pe_ratio"))), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(styled_kpi("EV/EBITDA", fmt_ratio(ratios.get("ev_ebitda"))), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(styled_kpi("EBITDA Margin", fmt_pct(ratios.get("ebitda_margin"))), unsafe_allow_html=True)
    with cols[4]:
        st.markdown(styled_kpi("Div Yield", fmt_pct(ratios.get("dividend_yield"))), unsafe_allow_html=True)


def render_phase2_engines(packet: dict[str, Any]) -> None:
    st.markdown("### Engine Results")
    engines = packet["engines"]
    cols = st.columns(4)
    labels = [
        ("pe_scoring", "PE Scoring"),
        ("factor_exposure", "Factor Exposure"),
        ("tsmom", "TSMOM Signal"),
        ("lbo", "LBO Snapshot"),
    ]
    for col, (key, label) in zip(cols, labels):
        with col:
            engine = engines.get(key, {})
            status = engine.get("status", "missing")
            color = {"success": "#00C853", "failed": "#FF3D57", "missing": "#888"}.get(status, "#FFAB00")
            st.markdown(badge(f"{label}: {status.upper()}", color), unsafe_allow_html=True)
            _engine_detail(key, engine)


def _engine_detail(key: str, engine: dict[str, Any]) -> None:
    if engine.get("status") != "success":
        st.caption(engine.get("reason", "no detail"))
        return
    if key == "pe_scoring":
        st.caption(f"PE score: {engine['pe_score']:.1f}  |  flags: {len(engine.get('red_flags', []))}")
    elif key == "factor_exposure":
        st.caption(f"composite: {engine['composite']:.2f}  |  conf: {engine['confidence']:.2f}")
    elif key == "tsmom":
        st.caption(f"signal: {engine['signal']:+d}  |  12-1: {engine['twelve_one_return'] * 100:+.1f}%")
    elif key == "lbo":
        st.caption(f"IRR: {engine['irr'] * 100:+.1f}%  |  MOIC: {engine['moic']:.2f}x")


def render_phase3_recommendation(packet: dict[str, Any]) -> None:
    rec = packet["recommendation"]
    rating = rec["rating"]
    color_map = {"BUY": "#00C853", "HOLD": "#FFAB00", "SELL": "#FF3D57", "INSUFFICIENT_DATA": "#888"}
    st.markdown("### Deterministic Recommendation")
    st.markdown(
        styled_kpi("Rating", f"{rating}  (grade {rec['confidence_grade']})", color_map.get(rating, "#FF8C00")),
        unsafe_allow_html=True,
    )
    sub = rec["sub_scores"]
    if sub:
        cols = st.columns(len(sub))
        for col, (key, val) in zip(cols, sub.items()):
            with col:
                display = f"{val:.1f}" if val == val else "n/a"
                st.markdown(styled_kpi(key.title(), display), unsafe_allow_html=True)
    st.markdown(
        interpretation_callout(
            observation=f"Composite score {rec['composite_score']:.1f}",
            interpretation="Derived deterministically from valuation, quality, momentum, risk sub-scores.",
            implication=f"Override reason: {rec['override_reason'] or 'none'}.",
        ),
        unsafe_allow_html=True,
    )


def render_phase4_llm(packet: dict[str, Any], config: dict[str, Any]) -> None:
    st.markdown("### LLM Memo")
    llm_cfg = config["llm"]
    enabled_setting = llm_cfg.get("enabled", False)
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    auto_on = enabled_setting == "auto" and has_key
    if not (auto_on or enabled_setting is True):
        st.caption(
            "LLM synthesis unavailable (no ANTHROPIC_API_KEY or disabled in config). "
            "Deterministic output above is fully functional."
        )
        return
    if not llm_is_available():
        st.caption("LLM synthesis unavailable (anthropic SDK not importable in this environment).")
        return
    with st.spinner("Synthesizing memo via Claude..."):
        result = generate_memo(
            ticker=packet["ticker"],
            recommendation=packet["recommendation"],
            ratios=packet["fundamentals"].key_ratios,
            scenarios=packet["scenarios"],
            llm_cfg=llm_cfg,
        )
    if result["status"] != "success":
        st.caption(f"LLM synthesis skipped: {result.get('reason', 'unknown reason')}")
        return
    if result.get("inconsistency"):
        st.markdown(badge("LLM RATING INCONSISTENCY DETECTED", "#FF3D57"), unsafe_allow_html=True)
        st.caption(result["inconsistency"])
    st.markdown(result["memo"])
