"""Comps page extra visualizations.

- Per metric bar chart for the PE Score tab. Each bar is the current
  value, the band overlay shows the ideal -> penalty range.
- EV/EBITDA vs revenue growth scatter for the active ticker, with a
  vertical and horizontal reference line at the sector medians.
  v1 plots a single point; when peer data lands in v2 the same chart
  populates with peer dots.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme

from terminal.utils.chart_helpers import MAIN_HEIGHT, SECONDARY_HEIGHT


def render_pe_metric_bars(ratios: dict[str, float], bands: dict[str, dict[str, Any]]) -> None:
    """Horizontal bars: current value vs ideal band per scoring metric."""
    if not bands:
        st.caption("DATA OFF | no scoring bands configured")
        return

    metrics: list[str] = []
    current_vals: list[float] = []
    ideals: list[float] = []
    penalties: list[float] = []
    higher_better: list[bool] = []
    for key, band in bands.items():
        v = ratios.get(key)
        if v is None or v != v:
            continue
        metrics.append(key.replace("_", " ").upper())
        current_vals.append(float(v))
        ideals.append(float(band["ideal"]))
        penalties.append(float(band["penalty"]))
        higher_better.append(bool(band["higher_better"]))
    if not metrics:
        st.caption("DATA OFF | no metric values to plot")
        return

    fig = go.Figure()
    # Penalty band: from 0 to penalty
    fig.add_trace(go.Bar(
        y=metrics, x=penalties, orientation="h",
        name="Penalty",
        marker={"color": "rgba(196,61,61,0.18)", "line": {"width": 0}},
        hovertemplate="Penalty: %{x}<extra></extra>",
    ))
    # Ideal band marker
    fig.add_trace(go.Scatter(
        y=metrics, x=ideals, mode="markers",
        name="Ideal",
        marker={"color": TOKENS["accent_success"], "size": 9, "symbol": "diamond"},
        hovertemplate="Ideal: %{x}<extra></extra>",
    ))
    # Current value marker
    fig.add_trace(go.Scatter(
        y=metrics, x=current_vals, mode="markers+text",
        name="Current",
        marker={"color": TOKENS["accent_primary"], "size": 12, "symbol": "circle"},
        text=[f"{v:.2f}" for v in current_vals], textposition="middle right",
        textfont={"family": "JetBrains Mono, monospace", "size": 10,
                  "color": TOKENS["text_primary"]},
        hovertemplate="Current: %{x:.3f}<extra></extra>",
    ))
    fig.update_xaxes(title_text="Metric value")
    fig.update_yaxes(title_text="Scoring metric", autorange="reversed")
    fig.update_layout(
        title={"text": "PE Scoring Bands. current vs ideal vs penalty"},
        height=MAIN_HEIGHT, barmode="overlay", showlegend=True,
        legend={"orientation": "h", "y": 1.08, "x": 0},
    )
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)


def render_ev_growth_scatter(
    ticker: str,
    ev_ebitda: float | None,
    revenue_growth: float | None,
    sector_median_ev: float = 11.0,
    sector_median_growth: float = 0.06,
) -> None:
    """Single ticker scatter with sector median reference lines.

    The sector medians are static placeholders (typical large cap
    sector medians) until peer data lands in v2.
    """
    if ev_ebitda is None or ev_ebitda != ev_ebitda or revenue_growth is None or revenue_growth != revenue_growth:
        st.caption("DATA OFF | EV/EBITDA or revenue growth not available for this ticker")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[float(revenue_growth) * 100], y=[float(ev_ebitda)],
        mode="markers+text", name=ticker,
        marker={"color": TOKENS["accent_primary"], "size": 16, "line": {"color": "#080808", "width": 1}},
        text=[ticker], textposition="top center",
        textfont={"family": "JetBrains Mono, monospace", "size": 11, "color": TOKENS["text_primary"]},
        hovertemplate=f"{ticker}<br>Growth %{{x:.1f}}%<br>EV/EBITDA %{{y:.1f}}<extra></extra>",
    ))
    fig.add_vline(x=sector_median_growth * 100,
                  line={"color": TOKENS["text_muted"], "width": 1, "dash": "dash"},
                  annotation_text=f"sector median growth {sector_median_growth * 100:.0f}%",
                  annotation_position="top")
    fig.add_hline(y=sector_median_ev,
                  line={"color": TOKENS["text_muted"], "width": 1, "dash": "dash"},
                  annotation_text=f"sector median EV/EBITDA {sector_median_ev:.0f}x",
                  annotation_position="right")
    fig.update_xaxes(title_text="Revenue growth (%)", ticksuffix="%")
    fig.update_yaxes(title_text="EV / EBITDA")
    fig.update_layout(
        title={"text": "Valuation vs Growth. peer dots populate in v2"},
        height=SECONDARY_HEIGHT, showlegend=False,
    )
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
