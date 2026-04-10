"""Research page rendering helpers."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st

from style_inject import TOKENS, styled_card

from app.pages._research_engine_renderers import (
    render_factor_engine,
    render_lbo_engine,
    render_pe_engine,
    render_tsmom_engine,
)
from terminal.synthesis.llm_client import generate_memo, is_available as llm_is_available
from terminal.utils.chart_helpers import interpretation_callout_html, line_chart
from terminal.utils.density import dense_kpi_row, period_returns_tape, section_bar, signed_color
from terminal.utils.error_handling import degraded_card, status_pill
from terminal.utils.formatting import fmt_money, fmt_pct, fmt_ratio


def render_phase1_chart(packet: dict[str, Any]) -> None:
    prices = packet["prices"]
    close = prices.prices["close"] if not prices.is_empty() else None
    tape = period_returns_tape(close) if close is not None else ""
    st.markdown(section_bar("PRICE", tape=tape), unsafe_allow_html=True)
    if close is None:
        st.markdown(degraded_card("no price series", prices.provider), unsafe_allow_html=True)
        return
    st.plotly_chart(
        line_chart({packet["ticker"]: close}, title=f"{packet['ticker']} price (1Y)", y_unit="USD"),
        use_container_width=True,
    )


def render_phase1_stats(packet: dict[str, Any]) -> None:
    fundamentals = packet["fundamentals"]
    ratios = fundamentals.key_ratios
    close = packet["prices"].prices["close"] if not packet["prices"].is_empty() else None
    st.markdown(section_bar("KEY STATS"), unsafe_allow_html=True)
    rev_growth = ratios.get("revenue_growth")
    items = [
        {"label": "MARKET CAP", "value": fmt_money(fundamentals.market_cap)},
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
    rows = [("Sector", fundamentals.sector or "n/a"), ("Industry", fundamentals.industry or "n/a"),
            ("Provider", fundamentals.provider)]
    if close is not None:
        rows += [("Last close", f"{close.iloc[-1]:.2f}"), ("52w high", f"{close.tail(252).max():.2f}"),
                 ("52w low", f"{close.tail(252).min():.2f}")]
    st.dataframe(pd.DataFrame(rows, columns=["Field", "Value"]), use_container_width=True, hide_index=True)


def render_phase2_engines(packet: dict[str, Any]) -> None:
    st.markdown(section_bar("ENGINE RESULTS"), unsafe_allow_html=True)
    engines = packet["engines"]
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
                st.caption(engine.get("reason", "no detail"))
                continue
            renderer(engine)


def render_phase3_recommendation(packet: dict[str, Any]) -> None:
    rec = packet["recommendation"]
    rating = rec["rating"]
    color_map = {
        "BUY": TOKENS["accent_success"], "HOLD": TOKENS["accent_warning"],
        "SELL": TOKENS["accent_danger"], "INSUFFICIENT_DATA": TOKENS["text_muted"],
    }
    accent = color_map.get(rating, TOKENS["accent_primary"])
    st.markdown(section_bar("DETERMINISTIC RATING"), unsafe_allow_html=True)
    items = [
        {"label": "RATING", "value": rating, "delta": f"grade {rec['confidence_grade']}",
         "delta_color": accent, "value_color": accent},
        {"label": "COMPOSITE", "value": f"{rec['composite_score']:.1f}",
         "value_color": signed_color(rec["composite_score"] - 50)},
        {"label": "CONFIDENCE", "value": f"{rec['confidence']:.2f}"},
    ]
    for key, val in (rec["sub_scores"] or {}).items():
        items.append({
            "label": key.upper(), "value": f"{val:.1f}" if val == val else "n/a",
            "value_color": signed_color(val - 50) if val == val else None,
        })
    st.markdown(dense_kpi_row(items, min_cell_px=95), unsafe_allow_html=True)
    styled_card(
        interpretation_callout_html(
            observation=f"Composite score {rec['composite_score']:.1f}.",
            interpretation="Derived deterministically from valuation, quality, momentum, and risk sub scores.",
            implication=f"Override reason. {rec['override_reason'] or 'none'}.",
        ),
        accent_color=accent,
    )


def render_phase4_llm(packet: dict[str, Any], config: dict[str, Any]) -> None:
    st.markdown(section_bar("LLM MEMO"), unsafe_allow_html=True)
    llm_cfg = config["llm"]
    enabled_setting = llm_cfg.get("enabled", False)
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not ((enabled_setting == "auto" and has_key) or enabled_setting is True):
        st.caption("LLM synthesis unavailable. No ANTHROPIC_API_KEY or disabled in config.")
        return
    if not llm_is_available():
        st.caption("LLM synthesis unavailable. anthropic SDK not importable.")
        return
    with st.spinner("Synthesizing memo via Claude."):
        result = generate_memo(
            ticker=packet["ticker"], recommendation=packet["recommendation"],
            ratios=packet["fundamentals"].key_ratios, scenarios=packet["scenarios"], llm_cfg=llm_cfg,
        )
    if result["status"] != "success":
        st.caption(f"LLM synthesis skipped. {result.get('reason', 'unknown reason')}.")
        return
    if result.get("inconsistency"):
        st.markdown(status_pill("LLM RATING INCONSISTENCY DETECTED", "failed"), unsafe_allow_html=True)
        st.caption(result["inconsistency"])
    st.markdown(result["memo"])
