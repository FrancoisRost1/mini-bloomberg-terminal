"""ANALYST CONSENSUS section for the Research page.

KPI row with target prices and analyst count, plus a visual range bar
showing where the current price sits relative to the analyst target
range (low to high). Degrades gracefully when data is unavailable.
"""

from __future__ import annotations

import math

import streamlit as st

from style_inject import TOKENS
from terminal.utils.density import dense_kpi_rows, section_bar
from terminal.utils.error_handling import inline_status_line
from terminal.utils.formatting import fmt_money


def _consensus_label(key: str | None, mean: float | None) -> str:
    """Readable consensus string from yfinance recommendation fields."""
    if key:
        return key.upper().replace("_", " ")
    if mean is not None and not math.isnan(mean):
        if mean <= 1.5:
            return "STRONG BUY"
        if mean <= 2.5:
            return "BUY"
        if mean <= 3.5:
            return "HOLD"
        if mean <= 4.5:
            return "SELL"
        return "STRONG SELL"
    return "n/a"


def _target_range_bar(lo: float, hi: float, current: float) -> str:
    """HTML bar showing current price position within analyst targets."""
    if hi <= lo or current != current:
        return ""
    pct = max(0.0, min(1.0, (current - lo) / (hi - lo)))
    accent = TOKENS["accent_primary"]
    bg = TOKENS["bg_elevated"]
    border = TOKENS["border_default"]
    muted = TOKENS["text_muted"]
    text = TOKENS["text_primary"]
    mono = TOKENS["font_mono"]
    upside = (hi / current - 1.0) * 100 if current > 0 else float("nan")
    upside_str = f"+{upside:.0f}% to HIGH" if upside == upside else ""
    return (
        f'<div style="padding:0.35rem 0.1rem 0.45rem 0.1rem;">'
        f'<div style="display:flex;align-items:center;gap:0.6rem;'
        f'font-family:{mono};font-size:0.7rem;color:{text};line-height:1.4;">'
        f'<span style="color:{muted};">LOW</span>'
        f'<span>{lo:,.2f}</span>'
        f'<div style="flex:1;position:relative;height:10px;background:{bg};'
        f'border:1px solid {border};border-radius:2px;">'
        f'<div style="position:absolute;left:{pct * 100:.1f}%;top:-3px;'
        f'width:2px;height:16px;background:{accent};"></div>'
        f'<div style="position:absolute;left:0;top:0;height:100%;'
        f'width:{pct * 100:.1f}%;background:rgba(255,138,42,0.18);"></div>'
        f'</div>'
        f'<span>{hi:,.2f}</span>'
        f'<span style="color:{muted};">HIGH</span>'
        f'<span style="color:{accent};font-weight:700;margin-left:0.6rem;">'
        f'CURRENT {current:,.2f} ({upside_str})</span>'
        f'</div></div>'
    )


def render_analyst_consensus(
    analyst: dict, current_price: float | None,
) -> None:
    """Render the ANALYST CONSENSUS section on the Research page."""
    st.markdown(
        section_bar("ANALYST CONSENSUS", source="yfinance"),
        unsafe_allow_html=True,
    )
    if not analyst:
        st.markdown(
            inline_status_line("OFF", source="yfinance"),
            unsafe_allow_html=True,
        )
        return

    target_mean = analyst.get("targetMeanPrice")
    target_hi = analyst.get("targetHighPrice")
    target_lo = analyst.get("targetLowPrice")
    n_analysts = analyst.get("numberOfAnalystOpinions")
    consensus = _consensus_label(
        analyst.get("recommendationKey"), analyst.get("recommendationMean"),
    )

    items = [
        {"label": "TARGET MEAN", "value": fmt_money(target_mean) if target_mean else "n/a"},
        {"label": "TARGET HIGH", "value": fmt_money(target_hi) if target_hi else "n/a"},
        {"label": "TARGET LOW", "value": fmt_money(target_lo) if target_lo else "n/a"},
        {"label": "# ANALYSTS", "value": str(n_analysts) if n_analysts else "n/a"},
        {"label": "CONSENSUS", "value": consensus},
    ]
    st.markdown(dense_kpi_rows(items, rows=2, min_cell_px=120), unsafe_allow_html=True)

    # Range bar: current price within analyst low-to-high target range.
    if target_lo and target_hi and current_price and not math.isnan(current_price):
        bar_html = _target_range_bar(float(target_lo), float(target_hi), current_price)
        if bar_html:
            st.markdown(bar_html, unsafe_allow_html=True)
