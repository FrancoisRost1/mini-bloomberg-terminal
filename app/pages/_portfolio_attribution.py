"""Portfolio Builder attribution helpers.

Drawdown comparison and marginal risk contribution breakdown. Split
out of _portfolio_helpers.py so both modules stay under the 150 line
budget. Reuses the method palette and portfolio-series builder from
_portfolio_helpers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme

from app.pages._portfolio_common import METHOD_PALETTE, build_portfolio_series
from terminal.utils.density import colored_dataframe, section_bar


def render_drawdown_chart(returns: pd.DataFrame, weights: dict[str, dict[str, float]]) -> None:
    """Drawdown path for MV vs HRP vs equal weight.

    For each method compute the NAV path, running peak, and drawdown =
    NAV / peak - 1. Every series starts at 0 and sits at or below 0 by
    construction, which makes the worst drawdown read off the y-axis
    without a legend.
    """
    st.markdown(section_bar("DRAWDOWN PATHS"), unsafe_allow_html=True)
    if returns is None or returns.empty:
        st.caption("DATA OFF | no return history available")
        return

    port_returns = build_portfolio_series(returns, weights)
    fig = go.Figure()
    max_dd_labels: list[str] = []
    for name, port in port_returns.items():
        nav = (1.0 + port).cumprod()
        peak = nav.cummax()
        dd = (nav / peak - 1.0) * 100.0
        color = METHOD_PALETTE.get(name, TOKENS["accent_primary"])
        fig.add_trace(go.Scatter(
            x=dd.index, y=dd.values, name=name, mode="lines",
            line={"width": 1.4, "color": color},
            fill="tozeroy",
            fillcolor=color + "15",
        ))
        max_dd_labels.append(f"{name} max dd {float(dd.min()):.1f}%")
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Drawdown (%)", rangemode="tozero")
    fig.update_layout(
        title={"text": "Drawdown. " + " | ".join(max_dd_labels)},
        height=280, legend={"orientation": "h", "y": 1.08, "x": 0},
    )
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)


def render_risk_contributions(returns: pd.DataFrame,
                              weights: dict[str, dict[str, float]],
                              cov: "np.ndarray | None") -> None:
    """Marginal risk contribution per asset per method.

    RC_i = w_i * (Sigma * w)_i / (w' Sigma w)
    Sum of RC_i across assets == 1.0 for each portfolio. Displayed as a
    compact dataframe with MV / HRP / EW side by side so the user can
    see which assets concentrate risk regardless of weight.
    """
    st.markdown(section_bar("RISK CONTRIBUTIONS"), unsafe_allow_html=True)
    if returns is None or returns.empty or cov is None:
        st.caption("DATA OFF | need returns and covariance")
        return
    sigma = cov
    assets = list(returns.columns)

    def _rc(wv: np.ndarray) -> np.ndarray:
        port_var = float(wv @ sigma @ wv)
        if port_var <= 0:
            return np.zeros_like(wv)
        return wv * (sigma @ wv) / port_var

    mv_w = pd.Series(weights.get("mean_variance", {}), dtype=float).reindex(assets).fillna(0.0).values
    hrp_w = pd.Series(weights.get("hrp", {}), dtype=float).reindex(assets).fillna(0.0).values
    eq_w = np.ones(len(assets)) / max(1, len(assets))
    mv_rc = _rc(mv_w)
    hrp_rc = _rc(hrp_w)
    eq_rc = _rc(eq_w)
    rows = [
        {
            "Asset": asset,
            "MV %":  f"{mv_rc[idx] * 100:.1f}%",
            "HRP %": f"{hrp_rc[idx] * 100:.1f}%",
            "EW %":  f"{eq_rc[idx] * 100:.1f}%",
        }
        for idx, asset in enumerate(assets)
    ]
    df = pd.DataFrame(rows)
    st.dataframe(colored_dataframe(df, ["MV %", "HRP %", "EW %"]),
                 use_container_width=True, hide_index=True)
    st.caption("RC_i = w_i * (Sigma * w)_i / (w' Sigma w). Columns sum to 100%.")
