"""Research page rendering helpers."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st

from style_inject import TOKENS, styled_card, styled_section_label

from terminal.synthesis.llm_client import generate_memo, is_available as llm_is_available
from terminal.utils.chart_helpers import interpretation_callout_html, line_chart
from terminal.utils.density import dense_kpi_row, signed_color
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
    ratios = fundamentals.key_ratios
    items = [
        {"label": "MARKET CAP", "value": fmt_money(fundamentals.market_cap)},
        {"label": "P/E", "value": fmt_ratio(ratios.get("pe_ratio"), suffix="")},
        {"label": "EV/EBITDA", "value": fmt_ratio(ratios.get("ev_ebitda"))},
        {"label": "EBITDA MARGIN", "value": fmt_pct(ratios.get("ebitda_margin"))},
        {"label": "FCF CONV", "value": fmt_pct(ratios.get("fcf_conversion"))},
        {"label": "ROE", "value": fmt_pct(ratios.get("roe"))},
        {"label": "REV GROWTH", "value": fmt_pct(ratios.get("revenue_growth")),
         "delta_color": signed_color(ratios.get("revenue_growth"))},
        {"label": "ND/EBITDA", "value": fmt_ratio(ratios.get("net_debt_ebitda"))},
        {"label": "INT COVERAGE", "value": fmt_ratio(ratios.get("interest_coverage"), suffix="x")},
        {"label": "BETA", "value": fmt_ratio(ratios.get("beta"), suffix="")},
        {"label": "DIV YIELD", "value": fmt_pct(ratios.get("dividend_yield"))},
        {"label": "SECTOR", "value": fundamentals.sector[:14] if fundamentals.sector else "n/a"},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=105), unsafe_allow_html=True)
    chart_col, ratio_col = st.columns([3, 1])
    with chart_col:
        st.plotly_chart(line_chart({packet["ticker"]: close}, title=f"{packet['ticker']} price (1Y)", y_unit="USD"), use_container_width=True)
    with ratio_col:
        rows = [("Sector", fundamentals.sector or "n/a"), ("Industry", fundamentals.industry or "n/a"),
                ("Provider", fundamentals.provider), ("Last close", f"{close.iloc[-1]:.2f}"),
                ("52w high", f"{close.tail(252).max():.2f}"), ("52w low", f"{close.tail(252).min():.2f}")]
        st.dataframe(pd.DataFrame(rows, columns=["Field", "Value"]), use_container_width=True, hide_index=True)


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
    accent = color_map.get(rating, TOKENS["accent_primary"])
    styled_section_label("DETERMINISTIC RECOMMENDATION")
    items = [
        {"label": "RATING", "value": rating, "delta": f"grade {rec['confidence_grade']}", "delta_color": accent},
        {"label": "COMPOSITE", "value": f"{rec['composite_score']:.1f}",
         "delta_color": signed_color(rec["composite_score"] - 50)},
        {"label": "CONFIDENCE", "value": f"{rec['confidence']:.2f}"},
    ]
    for key, val in (rec["sub_scores"] or {}).items():
        items.append({
            "label": key.upper(),
            "value": f"{val:.1f}" if val == val else "n/a",
            "delta_color": signed_color(val - 50) if val == val else None,
        })
    st.markdown(dense_kpi_row(items, min_cell_px=105), unsafe_allow_html=True)
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
