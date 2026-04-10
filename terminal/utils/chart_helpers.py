"""Plotly chart factory backed by the canonical design system.

Every figure built here is themed via ``apply_plotly_theme`` from the
project root ``style_inject.py``. Heights match DESIGN.md (main charts
320 to 360, secondary 240 to 280). Colors come from ``TOKENS`` so that
swapping the project accent automatically reskins every chart.

DESIGN.md rules enforced here:
- Always call ``apply_plotly_theme(fig)`` before returning.
- Every chart has an explicit string title.
- Every axis has explicit units.
- Default chart height is 320 (main) or 280 (secondary). Never 450.
- Heatmap colorscale uses the danger/elevated/success token tuple.
- The interpretation callout uses ``styled_card`` semantics, not a
  parallel HTML implementation.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from style_inject import TOKENS, apply_plotly_theme


MAIN_HEIGHT = 340
SECONDARY_HEIGHT = 260


def line_chart(
    series: dict[str, pd.Series],
    title: str,
    y_unit: str,
    x_unit: str = "Date",
    height: int = MAIN_HEIGHT,
) -> go.Figure:
    """Single or multi-line chart with explicit unit-labelled axes."""
    fig = go.Figure()
    for name, data in series.items():
        if data is None or data.empty:
            continue
        fig.add_trace(go.Scatter(
            x=data.index, y=data.values, name=name, mode="lines",
            line={"width": 1.5},
        ))
    fig.update_xaxes(title_text=x_unit)
    fig.update_yaxes(title_text=y_unit)
    fig.update_layout(title={"text": title}, height=height)
    return apply_plotly_theme(fig)


def bar_chart(
    values: dict[str, float],
    title: str,
    y_unit: str,
    height: int = SECONDARY_HEIGHT,
    color_by_sign: bool = False,
) -> go.Figure:
    """Vertical bar chart keyed by category label."""
    labels = list(values.keys())
    data = list(values.values())
    if color_by_sign:
        colors = [
            TOKENS["accent_success"] if v >= 0 else TOKENS["accent_danger"]
            for v in data
        ]
    else:
        colors = [TOKENS["accent_primary"]] * len(data)
    fig = go.Figure(go.Bar(x=labels, y=data, marker_color=colors))
    fig.update_yaxes(title_text=y_unit)
    fig.update_layout(title={"text": title}, height=height)
    return apply_plotly_theme(fig)


def heatmap(
    matrix: pd.DataFrame,
    title: str,
    colorbar_unit: str,
    height: int = MAIN_HEIGHT,
) -> go.Figure:
    """Heatmap built from the canonical danger / elevated / success tokens."""
    colorscale = [
        [0.0, TOKENS["accent_danger"]],
        [0.5, TOKENS["bg_elevated"]],
        [1.0, TOKENS["accent_success"]],
    ]
    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=[str(c) for c in matrix.columns],
        y=[str(i) for i in matrix.index],
        colorscale=colorscale,
        colorbar={"title": colorbar_unit},
    ))
    fig.update_layout(title={"text": title}, height=height)
    return apply_plotly_theme(fig)


def sector_treemap(
    labels: list[str],
    returns_pct: list[float],
    title: str,
    height: int = MAIN_HEIGHT,
) -> go.Figure:
    """Equal-weight treemap colored by 1D return.

    ``returns_pct`` is in percent (e.g. -1.23 for -1.23%). Cells are
    sized equally so the heatmap reads as pure direction; color comes
    from the canonical danger / elevated / success ramp.
    """
    colorscale = [
        [0.0, TOKENS["accent_danger"]],
        [0.5, TOKENS["bg_elevated"]],
        [1.0, TOKENS["accent_success"]],
    ]
    text = [f"{lbl}<br><b>{r:+.2f}%</b>" for lbl, r in zip(labels, returns_pct)]
    fig = go.Figure(go.Treemap(
        labels=labels,
        values=[1] * len(labels),
        parents=[""] * len(labels),
        text=text,
        textinfo="text",
        textfont={"family": "JetBrains Mono, monospace", "size": 12},
        marker={
            "colors": returns_pct,
            "colorscale": colorscale,
            "cmid": 0.0,
            "line": {"color": "#080808", "width": 1},
        },
        hovertemplate="<b>%{label}</b><br>%{customdata:+.2f}%<extra></extra>",
        customdata=returns_pct,
    ))
    fig.update_layout(title={"text": title}, height=height,
                      margin={"l": 4, "r": 4, "t": 30, "b": 4})
    return apply_plotly_theme(fig)


def waterfall(
    categories: list[str],
    values: list[float],
    title: str,
    y_unit: str = "$",
    height: int = SECONDARY_HEIGHT,
) -> go.Figure:
    """Equity-bridge-style waterfall for the LBO P&L layer."""
    measures = ["relative"] * len(categories)
    fig = go.Figure(go.Waterfall(
        x=categories, y=values, measure=measures,
        increasing={"marker": {"color": TOKENS["accent_success"]}},
        decreasing={"marker": {"color": TOKENS["accent_danger"]}},
        totals={"marker": {"color": TOKENS["accent_primary"]}},
    ))
    fig.update_yaxes(title_text=y_unit)
    fig.update_layout(title={"text": title}, height=height)
    return apply_plotly_theme(fig)


def interpretation_callout_html(observation: str, interpretation: str, implication: str) -> str:
    """Build the observation / interpretation / implication card HTML.

    Returns a single-line HTML string designed to be passed to
    ``styled_card`` from the canonical design system. The accent line
    on the left of the card is applied by ``styled_card`` itself, so
    this function only formats the inner content.
    """
    return (
        f'<b style="color: {TOKENS["accent_primary"]};">Observation.</b> {observation}<br/>'
        f'<b style="color: {TOKENS["accent_primary"]};">Interpretation.</b> {interpretation}<br/>'
        f'<b style="color: {TOKENS["accent_primary"]};">Implication.</b> {implication}'
    )
