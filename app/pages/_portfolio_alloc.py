"""Portfolio Builder allocation visualizations.

- Efficient frontier scatter (random long only sketch + MV / HRP /
  equal weight markers).
- Side by side allocation donut charts.

Split out of _portfolio_helpers.py so both modules stay under the
~150 line budget.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme

from terminal.adapters.optimizer_adapter import ledoit_wolf
from terminal.utils.density import section_bar


def render_efficient_frontier(returns: pd.DataFrame, weights: dict[str, dict[str, float]]) -> None:
    """Risk vs return scatter. Random long only portfolios sketch the
    feasible set; MV, HRP, and equal weight are marked on top.
    """
    st.markdown(section_bar("EFFICIENT FRONTIER"), unsafe_allow_html=True)
    if returns is None or returns.shape[1] < 2:
        st.caption("DATA OFF | need 2+ assets for the frontier")
        return
    cols = list(returns.columns)
    n = len(cols)
    sigma = ledoit_wolf(returns)
    mu = returns.mean().values * 252
    rng = np.random.default_rng(seed=7)
    samples = 800
    rand_w = rng.dirichlet(np.ones(n), samples)
    rand_ret = rand_w @ mu
    rand_vol = np.sqrt(np.einsum("ij,jk,ik->i", rand_w, sigma * 252, rand_w))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rand_vol * 100, y=rand_ret * 100, mode="markers",
        name="Random long only", marker={"size": 4, "color": "rgba(255,255,255,0.10)"},
        hovertemplate="vol %{x:.1f}%<br>ret %{y:.1f}%<extra></extra>",
    ))

    palette = {"mean_variance": TOKENS["accent_primary"], "hrp": TOKENS["accent_info"]}
    for method, wmap in weights.items():
        wv = pd.Series(wmap).reindex(cols).fillna(0).values
        ret = float(wv @ mu)
        vol = float(np.sqrt(wv @ (sigma * 252) @ wv))
        fig.add_trace(go.Scatter(
            x=[vol * 100], y=[ret * 100], mode="markers+text",
            name=method.upper(),
            marker={"size": 14, "color": palette.get(method, TOKENS["accent_primary"]),
                    "line": {"color": "#080808", "width": 1}, "symbol": "diamond"},
            text=[method.upper()], textposition="top center",
            textfont={"family": "JetBrains Mono, monospace", "size": 10,
                      "color": TOKENS["text_primary"]},
        ))
    eq_w = np.ones(n) / n
    eq_ret = float(eq_w @ mu)
    eq_vol = float(np.sqrt(eq_w @ (sigma * 252) @ eq_w))
    fig.add_trace(go.Scatter(
        x=[eq_vol * 100], y=[eq_ret * 100], mode="markers+text",
        name="EQUAL WEIGHT",
        marker={"size": 12, "color": TOKENS["text_secondary"], "symbol": "x",
                "line": {"color": "#080808", "width": 1}},
        text=["EW"], textposition="top center",
        textfont={"family": "JetBrains Mono, monospace", "size": 10,
                  "color": TOKENS["text_primary"]},
    ))
    fig.update_xaxes(title_text="Annualized volatility (%)", ticksuffix="%")
    fig.update_yaxes(title_text="Annualized return (%)", ticksuffix="%")
    fig.update_layout(title={"text": "Efficient Frontier. random long only sketch + chosen portfolios"},
                      height=280, showlegend=False)
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)


def render_allocation_donut(weight_map: dict[str, float], method: str) -> None:
    """Single compact donut for one optimizer method.

    Meant to be called inline next to the weight table in the method
    pane so there is no dedicated full-width ALLOCATIONS row eating
    vertical space.
    """
    wmap = {k: float(v) for k, v in weight_map.items() if v and v > 1e-4}
    if not wmap:
        st.caption(f"{method.upper()} | empty allocation")
        return
    labels = list(wmap.keys())
    values = list(wmap.values())
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.65, sort=False,
        textinfo="label+percent",
        textfont={"family": "JetBrains Mono, monospace", "size": 9},
        marker={"line": {"color": "#080808", "width": 1}},
    ))
    fig.update_layout(
        title={"text": method.upper().replace("_", " ")},
        height=220, width=220, showlegend=False,
        margin={"l": 2, "r": 2, "t": 26, "b": 2},
    )
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)


def render_allocation_donuts(weights: dict[str, dict[str, float]]) -> None:
    """Kept for backward compat. The inline layout is preferred but
    the full row variant is still used when the page wants one wide
    donut row instead of per-pane donuts.
    """
    st.markdown(section_bar("ALLOCATIONS"), unsafe_allow_html=True)
    if not weights:
        st.caption("DATA OFF | no weights produced")
        return
    method_keys = list(weights.keys())
    cols = st.columns(max(1, len(method_keys)))
    for col, method in zip(cols, method_keys):
        with col:
            render_allocation_donut(weights[method], method)
