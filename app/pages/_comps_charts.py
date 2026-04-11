"""Comps page extra visualizations.

- Per metric bar chart for the PE Score tab. Each bar is the current
  value, the band overlay shows the ideal -> penalty range.
- EV/EBITDA vs revenue growth scatter. Plots the active ticker plus
  its four sector peers (via sector_peers.peers_for), highlighting
  the active ticker in the project accent. Crosshairs show the
  median of the peers that actually landed on screen, so the "sector
  median" line updates with the underlying data.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
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
    data_manager=None,
    sector: str | None = None,
) -> None:
    """Peer scatter of EV/EBITDA vs Revenue Growth.

    Fetches the same five sector peers as the PEER FUNDAMENTALS tab
    (via ``sector_peers.peers_for``) and plots every peer with real
    data. The active ticker is drawn in the project accent and in a
    larger size. Crosshairs are the median of the plotted peers, so
    the "sector median" is computed from the actual dots on screen.
    """
    from terminal.utils.error_handling import is_error
    from terminal.utils.sector_peers import peers_for

    if data_manager is None:
        st.caption("DATA OFF | data manager not wired into scatter")
        return
    peers = peers_for(sector, ticker, limit=5)
    xs: list[float] = []
    ys: list[float] = []
    labels: list[str] = []
    for tkr in peers:
        f = data_manager.get_fundamentals(tkr)
        if is_error(f):
            continue
        ratios = f.key_ratios or {}
        ev = ratios.get("ev_ebitda")
        rg = ratios.get("revenue_growth")
        if ev is None or rg is None or ev != ev or rg != rg:
            continue
        xs.append(float(rg) * 100.0)
        ys.append(float(ev))
        labels.append(tkr)

    if not xs:
        st.caption("DATA OFF | no peer EV/EBITDA or revenue growth available")
        return

    median_x = float(pd.Series(xs).median())
    median_y = float(pd.Series(ys).median())

    # Outlier handling. A single extreme EV/EBITDA (TSLA at 110x, early
    # cycle growth story at 85x) flattens every peer into an invisible
    # cluster at the bottom of the chart. Cap the axis at 3x the peer
    # median (clamped to a minimum of 25x so normal sectors aren't
    # over-compressed) and draw outliers at the cap with an "off
    # scale" annotation on the marker itself.
    axis_cap = max(25.0, median_y * 3.0)
    plotted_ys: list[float] = []
    off_scale_flags: list[bool] = []
    annotations: list[str] = []
    for raw_y, lbl in zip(ys, labels):
        if raw_y > axis_cap:
            plotted_ys.append(axis_cap)
            off_scale_flags.append(True)
            annotations.append(f"{lbl} ↑ off scale at {raw_y:.1f}x")
        else:
            plotted_ys.append(raw_y)
            off_scale_flags.append(False)
            annotations.append(lbl)

    fig = go.Figure()
    colors: list[str] = []
    sizes: list[int] = []
    symbols: list[str] = []
    for lbl, off in zip(labels, off_scale_flags):
        if lbl.upper() == ticker.upper():
            colors.append(TOKENS["accent_primary"])
            sizes.append(20)
        else:
            colors.append(TOKENS["accent_info"])
            sizes.append(13)
        symbols.append("triangle-up" if off else "circle")
    fig.add_trace(go.Scatter(
        x=xs, y=plotted_ys, mode="markers+text",
        marker={"color": colors, "size": sizes, "symbol": symbols,
                "line": {"color": "#080808", "width": 1}},
        text=annotations, textposition="top center",
        textfont={"family": "JetBrains Mono, monospace", "size": 11,
                  "color": TOKENS["text_primary"]},
        hovertemplate="<b>%{text}</b><br>Growth %{x:.1f}%<br>EV/EBITDA %{y:.1f}x<extra></extra>",
        name="peers",
        cliponaxis=False,
    ))
    fig.add_vline(
        x=median_x,
        line={"color": TOKENS["text_muted"], "width": 1, "dash": "dash"},
        annotation_text=f"median growth {median_x:.1f}%",
        annotation_position="top right",
    )
    fig.add_hline(
        y=median_y,
        line={"color": TOKENS["text_muted"], "width": 1, "dash": "dash"},
        annotation_text=f"median EV/EBITDA {median_y:.1f}x",
        annotation_position="top left",
    )
    fig.update_xaxes(title_text="Revenue growth (%)", ticksuffix="%")
    fig.update_yaxes(title_text="EV / EBITDA", range=[0, axis_cap * 1.1])
    off_count = sum(off_scale_flags)
    title_suffix = f" | {off_count} off-scale at {axis_cap:.0f}x cap" if off_count else ""
    fig.update_layout(
        title={"text": f"Valuation vs Growth. {len(labels)} sector peers, dashed = median{title_suffix}"},
        height=SECONDARY_HEIGHT, showlegend=False,
    )
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
