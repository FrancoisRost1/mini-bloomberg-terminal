"""DIVIDENDS section for the Research page.

Small bar chart showing dividend per share over the last 3-5 years.
Shows an inline note when no dividend history is available.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme, styled_card
from terminal.utils.chart_helpers import interpretation_callout_html
from terminal.utils.density import section_bar
from terminal.utils.error_handling import inline_status_line


def render_dividends(ticker: str, data_manager) -> None:
    """Render the DIVIDENDS section on the Research page."""
    st.markdown(section_bar("DIVIDENDS", source="yfinance"), unsafe_allow_html=True)
    data = data_manager.get_dividends(ticker)
    divs: pd.Series = data.get("dividends", pd.Series(dtype=float))
    if divs.empty:
        st.markdown(inline_status_line("No dividend history", source="yfinance"), unsafe_allow_html=True)
        return

    # Keep last 5 years.
    cutoff = pd.Timestamp.now() - pd.DateOffset(years=5)
    divs = divs[divs.index >= cutoff]
    if divs.empty:
        st.markdown(inline_status_line("No recent dividends", source="yfinance"), unsafe_allow_html=True)
        return

    # Aggregate to annual totals for a cleaner chart.
    annual = divs.groupby(divs.index.year).sum()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[str(y) for y in annual.index],
        y=annual.values,
        marker_color=TOKENS["accent_primary"],
        opacity=0.85,
    ))
    fig.update_layout(
        title="Annual Dividend per Share",
        yaxis_title="DPS ($)",
        height=200,
        margin=dict(l=40, r=10, t=40, b=25),
    )
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

    latest = float(annual.iloc[-1]) if len(annual) else 0
    prev = float(annual.iloc[-2]) if len(annual) >= 2 else 0
    growth = ((latest / prev - 1) * 100) if prev > 0 else 0
    styled_card(
        interpretation_callout_html(
            observation=f"Latest annual DPS ${latest:.2f}, YoY change {growth:+.1f}%.",
            interpretation="Stable or growing dividends signal cash flow discipline and shareholder commitment.",
            implication="Dividend cuts are a strong negative signal; watch payout ratio for sustainability.",
        ),
        accent_color=TOKENS["accent_primary"],
    )
