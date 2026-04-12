"""Options Lab. Single-leg payoff chart with spot and breakeven lines."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme
from terminal.engines.pnl_engine import compute_option_payoff


def render_payoff_with_lines(
    spot: float, strike: float, premium: float, opt_type: str, config: dict[str, Any],
) -> None:
    """Single leg payoff with vertical lines for spot and breakeven."""
    payoff_cfg = config["options_lab"]["payoff"]
    df = compute_option_payoff(
        spot=spot, strike=strike, premium=premium, option_type=opt_type,
        spot_range_pct=float(payoff_cfg["spot_range_pct"]),
        points=int(payoff_cfg["spot_points"]),
    )
    breakeven = strike + premium if opt_type == "call" else strike - premium
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["pnl"], name="P&L", mode="lines",
        line={"width": 1.7, "color": TOKENS["accent_primary"]},
        fill="tozeroy", fillcolor="rgba(255,138,42,0.07)",
    ))
    fig.add_hline(y=0, line={"color": TOKENS["text_muted"], "width": 1})
    fig.add_vline(x=spot, line={"color": TOKENS["accent_info"], "width": 1.4, "dash": "dot"},
                  annotation_text=f"SPOT {spot:,.2f}", annotation_position="top")
    fig.add_vline(x=breakeven, line={"color": TOKENS["accent_warning"], "width": 1.4, "dash": "dash"},
                  annotation_text=f"BE {breakeven:,.2f}", annotation_position="bottom")
    fig.update_xaxes(title_text="Spot at expiry ($)")
    fig.update_yaxes(title_text="P&L ($)")
    fig.update_layout(title={"text": f"Expiration Payoff. {opt_type.upper()} K {strike:,.2f}"}, height=260)
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
