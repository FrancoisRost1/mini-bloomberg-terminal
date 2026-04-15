"""DIVIDENDS section for the Research page.

Small bar chart showing dividend per share over the last 3-5 years.
Shows an inline note when no dividend history is available.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme
from terminal.utils.density import dense_kpi_rows, section_bar
from terminal.utils.error_handling import inline_status_line
from terminal.utils.formatting import fmt_pct


def render_dividends(ticker: str, data_manager) -> None:
    """Render the DIVIDENDS section on the Research page."""
    st.markdown(section_bar("DIVIDENDS", source="yfinance"), unsafe_allow_html=True)
    data = data_manager.get_dividends(ticker)
    divs: pd.Series = data.get("dividends", pd.Series(dtype=float))
    if divs.empty:
        st.markdown(inline_status_line("No dividend history", source="yfinance"), unsafe_allow_html=True)
        return

    # Strip timezone to avoid tz-aware vs tz-naive comparison crash
    # (yfinance returns tz-aware index, pd.Timestamp.now() is naive).
    if divs.index.tz is not None:
        divs.index = divs.index.tz_localize(None)

    # Keep the last ~7 years so the chart always shows 5+ full annual bars
    # even when the partial current year is included.
    cutoff = pd.Timestamp.now() - pd.DateOffset(years=7)
    divs = divs[divs.index >= cutoff]
    if divs.empty:
        st.markdown(inline_status_line("No recent dividends", source="yfinance"), unsafe_allow_html=True)
        return

    # Aggregate to annual totals for a cleaner chart. Build plain Python
    # lists so Plotly receives a well-typed categorical axis regardless of
    # what dtype the upstream series happened to carry.
    annual = divs.groupby(divs.index.year).sum().sort_index()
    x_years = [str(int(y)) for y in annual.index.tolist()]
    y_dps = [float(v) for v in annual.values.tolist()]
    st.text(f"DEBUG DIVS: x_years={x_years}, y_vals={y_dps}")

    try:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=x_years,
            y=y_dps,
            marker_color=TOKENS["accent_primary"],
            opacity=0.85,
        ))
        fig.update_layout(
            title="Annual Dividend per Share",
            yaxis_title="DPS ($)",
            height=220,
            margin=dict(l=40, r=10, t=40, b=30),
        )
        apply_plotly_theme(fig)
        # Force category axis AFTER the theme so it cannot get clobbered by
        # the theme's xaxis dict merge.
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=x_years)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        import traceback
        st.error(f"Dividend chart error: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())

    latest = float(annual.iloc[-1]) if len(annual) else 0
    prev = float(annual.iloc[-2]) if len(annual) >= 2 else 0
    growth = ((latest / prev - 1) * 100) if prev > 0 else 0
    st.caption(f"Latest annual DPS ${latest:.2f}, YoY {growth:+.1f}%")

    # Dividend stats KPIs to fill the column height.
    stats = data.get("stats") or {}
    first = float(annual.iloc[0]) if len(annual) else 0
    n_years = len(annual) - 1
    cagr = ((latest / first) ** (1.0 / n_years) - 1) if first > 0 and n_years > 0 else None
    items = [
        {"label": "DIV YIELD", "value": fmt_pct(stats.get("dividend_yield"))},
        {"label": "PAYOUT RATIO", "value": fmt_pct(stats.get("payout_ratio"))},
        {"label": "EX-DIV DATE", "value": stats.get("ex_dividend_date") or "n/a"},
        {"label": f"{n_years}Y CAGR", "value": fmt_pct(cagr)},
    ]
    st.markdown(dense_kpi_rows(items, rows=2, min_cell_px=100), unsafe_allow_html=True)
