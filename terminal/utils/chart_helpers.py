"""Plotly chart factory with Bloomberg dark theme.

Every chart built here has an explicit string title, labelled axes with
units, and a required interpretation callout built via the
observation/interpretation/implication format. Pages never construct
plotly figures directly -- they always go through these helpers.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go


BG_COLOR = "#0E1117"
PAPER_COLOR = "#161A23"
GRID_COLOR = "#262B3A"
TEXT_COLOR = "#E6E6E6"
ACCENT = "#FF8C00"
POS_COLOR = "#00C853"
NEG_COLOR = "#FF3D57"


def _apply_theme(fig: go.Figure, title: str, height: int) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.0, "xanchor": "left", "font": {"color": TEXT_COLOR, "size": 14}},
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=PAPER_COLOR,
        font={"family": "JetBrains Mono, monospace", "color": TEXT_COLOR, "size": 11},
        height=height,
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
        hovermode="x unified",
        showlegend=True,
        legend={"bgcolor": "rgba(0,0,0,0)", "font": {"color": TEXT_COLOR}},
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    fig.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    return fig


def line_chart(
    series: dict[str, pd.Series],
    title: str,
    y_unit: str,
    x_unit: str = "Date",
    height: int = 450,
) -> go.Figure:
    """Single-line or multi-line chart with explicit units on both axes."""
    fig = go.Figure()
    palette = [ACCENT, "#00B0FF", POS_COLOR, "#B388FF", "#FFD600"]
    for i, (name, data) in enumerate(series.items()):
        if data is None or data.empty:
            continue
        fig.add_trace(go.Scatter(
            x=data.index, y=data.values, name=name, mode="lines",
            line={"color": palette[i % len(palette)], "width": 1.5},
        ))
    fig.update_xaxes(title_text=x_unit)
    fig.update_yaxes(title_text=y_unit)
    return _apply_theme(fig, title, height)


def bar_chart(
    values: dict[str, float],
    title: str,
    y_unit: str,
    height: int = 400,
    color_by_sign: bool = False,
) -> go.Figure:
    """Horizontal or vertical bar chart keyed by label."""
    labels = list(values.keys())
    data = list(values.values())
    colors = [POS_COLOR if v >= 0 else NEG_COLOR for v in data] if color_by_sign else [ACCENT] * len(data)
    fig = go.Figure(go.Bar(x=labels, y=data, marker_color=colors))
    fig.update_yaxes(title_text=y_unit)
    return _apply_theme(fig, title, height)


def heatmap(
    matrix: pd.DataFrame,
    title: str,
    colorbar_unit: str,
    height: int = 450,
) -> go.Figure:
    """Heatmap for sensitivity tables and correlation-style views."""
    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=[str(c) for c in matrix.columns],
        y=[str(i) for i in matrix.index],
        colorscale="Oranges",
        colorbar={"title": colorbar_unit},
    ))
    return _apply_theme(fig, title, height)


def waterfall(
    categories: list[str],
    values: list[float],
    title: str,
    y_unit: str = "$",
    height: int = 400,
) -> go.Figure:
    """Equity-bridge-style waterfall for the LBO P&L layer."""
    measures = ["relative"] * len(categories)
    fig = go.Figure(go.Waterfall(
        x=categories, y=values, measure=measures,
        increasing={"marker": {"color": POS_COLOR}},
        decreasing={"marker": {"color": NEG_COLOR}},
        totals={"marker": {"color": ACCENT}},
    ))
    fig.update_yaxes(title_text=y_unit)
    return _apply_theme(fig, title, height)


def interpretation_callout(observation: str, interpretation: str, implication: str) -> str:
    """Single-line HTML callout in observation/interpretation/implication format."""
    return f'<div style="padding:10px 14px;background:#161A23;border-left:3px solid {ACCENT};border-radius:4px;font-family:JetBrains Mono,monospace;font-size:12px;color:#E6E6E6;line-height:1.5;"><b style="color:{ACCENT};">Observation:</b> {observation}<br/><b style="color:{ACCENT};">Interpretation:</b> {interpretation}<br/><b style="color:{ACCENT};">Implication:</b> {implication}</div>'
