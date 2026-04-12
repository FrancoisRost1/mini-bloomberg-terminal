"""Earnings surprise grouped bar chart for the Research page.

Grouped bars: EPS Estimate (gray) vs EPS Actual (green if beat, red
if miss) per quarter. Sits beside the earnings table in a 2-col layout.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme, styled_card
from terminal.utils.chart_helpers import interpretation_callout_html

_GREEN = "#00C853"
_RED = "#FF1744"
_GRAY = TOKENS["text_muted"]


def render_earnings_chart(history: list[dict]) -> None:
    """Render a grouped bar chart of EPS estimate vs actual."""
    valid = [q for q in history if q.get("eps_estimate") is not None and q.get("eps_actual") is not None]
    if not valid:
        return

    quarters = [q["quarter"] for q in valid]
    estimates = [q["eps_estimate"] for q in valid]
    actuals = [q["eps_actual"] for q in valid]
    colors = [_GREEN if a >= e else _RED for a, e in zip(actuals, estimates)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=quarters, y=estimates, name="Estimate",
        marker_color=_GRAY, opacity=0.6,
    ))
    fig.add_trace(go.Bar(
        x=quarters, y=actuals, name="Actual",
        marker_color=colors, opacity=0.9,
    ))
    fig.update_layout(
        barmode="group", height=240,
        title="EPS: Estimate vs Actual",
        yaxis_title="EPS ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=10, t=50, b=30),
    )
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

    beats = sum(1 for a, e in zip(actuals, estimates) if a >= e)
    total = len(valid)
    beat_rate = beats / total * 100 if total else 0
    avg_surp = sum((a - e) / abs(e) * 100 for a, e in zip(actuals, estimates) if e != 0) / total if total else 0
    styled_card(
        interpretation_callout_html(
            observation=f"Beat rate {beat_rate:.0f}% over last {total} quarters, avg surprise {avg_surp:+.1f}%.",
            interpretation="Consistent beats suggest conservative guidance; misses flag execution risk.",
            implication="Use the surprise trend to gauge management credibility on forward estimates.",
        ),
        accent_color=_GREEN if beat_rate >= 50 else _RED,
    )
