"""Options Lab IV smile rendering.

Extracted from _options_chain.py so both files stay under the 150
line budget after the full chain styler grew. Builds (strike,
moneyness, iv, type) rows from a chain DataFrame and plots the smile
split by call vs put.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme

from terminal.adapters.options_adapter import implied_vol
from terminal.utils.density import section_bar
from terminal.utils.error_handling import inline_status_line


def render_iv_smile_moneyness(chain_df: pd.DataFrame, spot: float, tau: float, rate: float, config: dict[str, Any]) -> None:
    """IV smile across strikes for the selected expiry, x axis is moneyness (K/S - 1)."""
    st.markdown(section_bar("IV SMILE", source="yfinance"), unsafe_allow_html=True)
    if chain_df is None or chain_df.empty or spot <= 0:
        st.markdown(inline_status_line("OFF", source="yfinance"), unsafe_allow_html=True)
        return
    rows = _smile_rows(chain_df, spot, tau, rate, config)
    if rows.empty:
        st.markdown(inline_status_line("PARTIAL", source="yfinance"), unsafe_allow_html=True)
        return

    fig = go.Figure()
    for side, color in [("call", TOKENS["accent_primary"]), ("put", TOKENS["accent_info"])]:
        sub = rows[rows["type"] == side].sort_values("moneyness")
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["moneyness"] * 100, y=sub["iv"] * 100,
            name=side.upper(), mode="lines+markers",
            line={"width": 1.6, "color": color}, marker={"size": 5, "color": color},
        ))
    fig.add_vline(x=0.0, line={"color": TOKENS["text_muted"], "width": 1, "dash": "dot"},
                  annotation_text="ATM", annotation_position="top")
    fig.update_xaxes(title_text="Moneyness K/S - 1 (%)", ticksuffix="%")
    fig.update_yaxes(title_text="Implied volatility (%)", ticksuffix="%")
    fig.update_layout(title={"text": "IV Smile. selected expiry"}, height=300,
                      legend={"orientation": "h", "y": 1.1, "x": 0})
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)


def _smile_rows(chain_df: pd.DataFrame, spot: float, tau: float, rate: float, config: dict[str, Any]) -> pd.DataFrame:
    """Build (strike, moneyness, iv, type) rows. Prefer the provider IV
    column when available; fall back to a Brent solve from the mid.
    """
    solver = config["options_lab"]["iv_solver"]
    rows: list[dict] = []
    for _, row in chain_df.iterrows():
        strike = float(row.get("strike", float("nan")))
        if not strike or strike != strike:
            continue
        opt_type = str(row.get("type", "call"))
        provider_iv = float(row.get("implied_volatility", float("nan"))) if "implied_volatility" in chain_df.columns else float("nan")
        if provider_iv == provider_iv and provider_iv > 0:
            iv = provider_iv
        else:
            mid = 0.5 * (float(row.get("bid", float("nan"))) + float(row.get("ask", float("nan"))))
            if not (mid == mid and mid > 0):
                continue
            iv = implied_vol(mid, spot, strike, tau, rate, 0.0, opt_type, solver)
        if not (iv == iv and 0.01 < iv < 5.0):
            continue
        rows.append({"strike": strike, "moneyness": (strike / spot) - 1.0, "iv": iv, "type": opt_type})
    return pd.DataFrame(rows)
