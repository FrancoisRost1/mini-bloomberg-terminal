"""Portfolio Builder helpers.

Pulled out of portfolio_builder.py so the page module stays under the
~150 line budget. Renderers:

- correlation matrix heatmap on the asset returns
- cumulative return backtest comparing MV, HRP, and equal weight

Drawdown paths and risk contributions live in _portfolio_attribution.py.
Efficient frontier and allocation donuts live in _portfolio_alloc.py.
Shared palette + portfolio-series builder live in _portfolio_common.py
so sibling modules can import them without creating a cycle.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme

from app.pages._portfolio_attribution import (  # noqa: F401  re export
    render_drawdown_chart,
    render_risk_contributions,
)
from app.pages._portfolio_common import METHOD_PALETTE, build_portfolio_series
from terminal.utils.chart_helpers import heatmap as plot_heatmap
from terminal.utils.density import section_bar


def render_correlation_heatmap(returns: pd.DataFrame) -> None:
    """Plotly heatmap of pairwise return correlations across all assets."""
    st.markdown(section_bar("CORRELATION MATRIX"), unsafe_allow_html=True)
    if returns is None or returns.shape[1] < 2:
        st.caption("DATA OFF | need 2+ assets for correlation matrix")
        return
    corr = returns.corr().round(2)
    fig = plot_heatmap(corr, title="Asset Return Correlation", colorbar_unit="rho")
    fig.update_traces(zmin=-1, zmax=1, zmid=0,
                      text=corr.values, texttemplate="%{text:.2f}",
                      textfont={"size": 9, "family": "JetBrains Mono, monospace"})
    st.plotly_chart(fig, use_container_width=True)


def render_backtest_chart(returns: pd.DataFrame, weights: dict[str, dict[str, float]]) -> None:
    """Cumulative return chart for MV vs HRP vs equal weight on the
    same asset universe and lookback. Pure long-only, no rebalance,
    no transaction cost; this is a quick visual sanity check, not a
    full backtest engine.
    """
    st.markdown(section_bar("CUMULATIVE RETURNS"), unsafe_allow_html=True)
    if returns is None or returns.empty:
        st.caption("DATA OFF | no return history available")
        return

    port_returns = build_portfolio_series(returns, weights)
    fig = go.Figure()
    for name, port in port_returns.items():
        cum = (1.0 + port).cumprod() - 1.0
        fig.add_trace(go.Scatter(
            x=cum.index, y=(cum.values * 100), name=name, mode="lines",
            line={"width": 1.6, "color": METHOD_PALETTE.get(name, TOKENS["accent_primary"])},
        ))
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Cumulative return (%)")
    fig.update_layout(title={"text": "Backtest. MV vs HRP vs Equal Weight (no rebalance, no TC)"},
                      height=280, legend={"orientation": "h", "y": 1.08, "x": 0})
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
