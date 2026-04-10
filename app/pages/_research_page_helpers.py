"""Research page rendering helpers.

Split from ticker_deep_dive.py so the page module stays under the per
module line budget. Phase rendering functions live here; the page file
orchestrates the four phases.
"""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from style_inject import (
    TOKENS,
    styled_card,
    styled_kpi,
    styled_section_label,
)

from terminal.synthesis.llm_client import generate_memo, is_available as llm_is_available
from terminal.utils.chart_helpers import interpretation_callout_html, line_chart
from terminal.utils.error_handling import degraded_card, status_pill
from terminal.utils.formatting import fmt_money, fmt_pct, fmt_ratio


def render_phase1_prices(packet: dict[str, Any]) -> None:
    prices = packet["prices"]
    fundamentals = packet["fundamentals"]
    styled_section_label("PRICE AND KEY STATS")
    close = prices.prices["close"] if not prices.is_empty() else None
    if close is None:
        st.markdown(degraded_card("no price series", prices.provider), unsafe_allow_html=True)
        return
    fig = line_chart({packet["ticker"]: close}, title=f"{packet['ticker']} Price (1Y)", y_unit="USD")
    st.plotly_chart(fig, use_container_width=True)
    ratios = fundamentals.key_ratios
    cols = st.columns(5)
    with cols[0]:
        styled_kpi("MARKET CAP", fmt_money(fundamentals.market_cap))
    with cols[1]:
        styled_kpi("P/E", fmt_ratio(ratios.get("pe_ratio")))
    with cols[2]:
        styled_kpi("EV/EBITDA", fmt_ratio(ratios.get("ev_ebitda")))
    with cols[3]:
        styled_kpi("EBITDA MARGIN", fmt_pct(ratios.get("ebitda_margin")))
    with cols[4]:
        styled_kpi("DIV YIELD", fmt_pct(ratios.get("dividend_yield")))


def render_phase2_engines(packet: dict[str, Any]) -> None:
    styled_section_label("ENGINE RESULTS")
    engines = packet["engines"]
    cols = st.columns(4)
    labels = [
        ("pe_scoring", "PE SCORING"),
        ("factor_exposure", "FACTOR EXPOSURE"),
        ("tsmom", "TSMOM SIGNAL"),
        ("lbo", "LBO SNAPSHOT"),
    ]
    for col, (key, label) in zip(cols, labels):
        with col:
            engine = engines.get(key, {})
            status = engine.get("status", "missing")
            st.markdown(status_pill(label, status), unsafe_allow_html=True)
            _engine_detail(key, engine)


def _engine_detail(key: str, engine: dict[str, Any]) -> None:
    if engine.get("status") != "success":
        st.caption(engine.get("reason", "no detail"))
        return
    if key == "pe_scoring":
        st.caption(f"PE score {engine['pe_score']:.1f} | flags {len(engine.get('red_flags', []))}")
    elif key == "factor_exposure":
        st.caption(f"composite {engine['composite']:.2f} | conf {engine['confidence']:.2f}")
    elif key == "tsmom":
        st.caption(f"signal {engine['signal']:+d} | 12 1 {engine['twelve_one_return'] * 100:+.1f}%")
    elif key == "lbo":
        st.caption(f"IRR {engine['irr'] * 100:+.1f}% | MOIC {engine['moic']:.2f}x")


def render_phase3_recommendation(packet: dict[str, Any]) -> None:
    rec = packet["recommendation"]
    rating = rec["rating"]
    color_map = {
        "BUY": TOKENS["accent_success"],
        "HOLD": TOKENS["accent_warning"],
        "SELL": TOKENS["accent_danger"],
        "INSUFFICIENT_DATA": TOKENS["text_muted"],
    }
    styled_section_label("DETERMINISTIC RECOMMENDATION")
    accent = color_map.get(rating, TOKENS["accent_primary"])
    styled_kpi("RATING", rating, delta=f"grade {rec['confidence_grade']}", delta_color=accent)
    sub = rec["sub_scores"]
    if sub:
        cols = st.columns(len(sub))
        for col, (key, val) in zip(cols, sub.items()):
            with col:
                display = f"{val:.1f}" if val == val else "n/a"
                styled_kpi(key.upper(), display)
    styled_card(
        interpretation_callout_html(
            observation=f"Composite score {rec['composite_score']:.1f}.",
            interpretation="Derived deterministically from valuation, quality, momentum, and risk sub scores.",
            implication=f"Override reason. {rec['override_reason'] or 'none'}.",
        ),
        accent_color=accent,
    )


def render_phase4_llm(packet: dict[str, Any], config: dict[str, Any]) -> None:
    styled_section_label("LLM MEMO")
    llm_cfg = config["llm"]
    enabled_setting = llm_cfg.get("enabled", False)
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    auto_on = enabled_setting == "auto" and has_key
    if not (auto_on or enabled_setting is True):
        st.caption(
            "LLM synthesis unavailable. No ANTHROPIC_API_KEY or disabled in config. "
            "Deterministic output above is fully functional."
        )
        return
    if not llm_is_available():
        st.caption("LLM synthesis unavailable. anthropic SDK not importable in this environment.")
        return
    with st.spinner("Synthesizing memo via Claude."):
        result = generate_memo(
            ticker=packet["ticker"],
            recommendation=packet["recommendation"],
            ratios=packet["fundamentals"].key_ratios,
            scenarios=packet["scenarios"],
            llm_cfg=llm_cfg,
        )
    if result["status"] != "success":
        st.caption(f"LLM synthesis skipped. {result.get('reason', 'unknown reason')}.")
        return
    if result.get("inconsistency"):
        st.markdown(status_pill("LLM RATING INCONSISTENCY DETECTED", "failed"), unsafe_allow_html=True)
        st.caption(result["inconsistency"])
    st.markdown(result["memo"])
