"""Research page financials summary table and 52w range bar.

Pulled out of _research_page_helpers.py so the helpers module stays
under the line budget. Both renderers are tolerant of missing data
and degrade to inline status lines rather than raising.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd
import streamlit as st

from style_inject import TOKENS

from terminal.utils.density import section_bar
from terminal.utils.error_handling import inline_status_line
from terminal.utils.formatting import fmt_money


def _last_n(series: pd.Series, n: int = 3) -> list[float]:
    if series is None or series.empty:
        return []
    return [float(v) for v in series.dropna().tail(n).tolist()]


def render_financials_table(fundamentals) -> None:
    """3Y revenue, EBITDA, net income, and FCF with sparklines."""
    st.markdown(section_bar("FINANCIALS (LAST 3Y)", source="FMP"), unsafe_allow_html=True)
    if fundamentals is None:
        st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
        return

    income = getattr(fundamentals, "income_statement", pd.DataFrame())
    cash = getattr(fundamentals, "cash_flow", pd.DataFrame())

    rev = income.get("revenue", pd.Series(dtype=float)) if not income.empty else pd.Series(dtype=float)
    ebitda = income.get("ebitda", pd.Series(dtype=float)) if not income.empty else pd.Series(dtype=float)
    ni = income.get("netIncome", pd.Series(dtype=float)) if not income.empty else pd.Series(dtype=float)
    if not cash.empty:
        ocf = cash.get("operatingCashFlow", pd.Series(dtype=float))
        capex = cash.get("capitalExpenditure", pd.Series(dtype=float)).abs()
        fcf = (ocf - capex).dropna()
    else:
        fcf = pd.Series(dtype=float)

    rows: list[dict[str, Any]] = []
    for label, series in [("Revenue", rev), ("EBITDA", ebitda), ("Net Income", ni), ("Free Cash Flow", fcf)]:
        vals = _last_n(series, 3)
        if not vals:
            continue
        latest = vals[-1]
        prior = vals[-2] if len(vals) >= 2 else float("nan")
        yoy = (latest / prior - 1.0) if (prior == prior and prior != 0) else float("nan")
        rows.append({
            "Line": label,
            "Latest": fmt_money(latest),
            "Prior": fmt_money(prior) if prior == prior else "n/a",
            "YoY %": f"{yoy * 100:+.1f}%" if (yoy == yoy and not math.isnan(yoy)) else "n/a",
            "3Y Trend": vals,
        })
    if not rows:
        st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
        return
    df = pd.DataFrame(rows)
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        column_config={"3Y Trend": st.column_config.LineChartColumn("3Y Trend", width="medium")},
    )


def render_52w_range_bar(close: pd.Series) -> None:
    """Visual bar showing where the current price sits in its 52w range."""
    st.markdown(section_bar("52W RANGE", source="FMP"), unsafe_allow_html=True)
    if close is None or close.empty:
        st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
        return
    window = close.tail(252)
    lo = float(window.min())
    hi = float(window.max())
    last = float(window.iloc[-1])
    if hi <= lo:
        st.markdown(inline_status_line("PARTIAL", source="FMP"), unsafe_allow_html=True)
        return
    pct = (last - lo) / (hi - lo)
    pct = max(0.0, min(1.0, pct))
    accent = TOKENS["accent_primary"]
    bg = TOKENS["bg_elevated"]
    border = TOKENS["border_default"]
    muted = TOKENS["text_muted"]
    text = TOKENS["text_primary"]
    # Wrap the bar in a padded container so the top edge never
    # touches the section_bar underline above it and the bottom
    # never touches the financials table below.
    bar = (
        f'<div style="padding:0.45rem 0.1rem 0.55rem 0.1rem;">'
        f'<div style="display:flex;align-items:center;gap:0.6rem;'
        f'font-family:{TOKENS["font_mono"]};font-size:0.7rem;color:{text};'
        f'line-height:1.4;">'
        f'<span style="color:{muted};">52W LOW</span>'
        f'<span>{lo:,.2f}</span>'
        f'<div style="flex:1;position:relative;height:10px;background:{bg};'
        f'border:1px solid {border};border-radius:2px;">'
        f'<div style="position:absolute;left:{pct * 100:.1f}%;top:-3px;'
        f'width:2px;height:16px;background:{accent};"></div>'
        f'<div style="position:absolute;left:0;top:0;height:100%;'
        f'width:{pct * 100:.1f}%;background:rgba(255,138,42,0.18);"></div>'
        f'</div>'
        f'<span>{hi:,.2f}</span>'
        f'<span style="color:{muted};">52W HIGH</span>'
        f'<span style="color:{accent};font-weight:700;margin-left:0.6rem;">'
        f'LAST {last:,.2f} ({pct * 100:.0f}%)</span>'
        f'</div></div>'
    )
    st.markdown(bar, unsafe_allow_html=True)
