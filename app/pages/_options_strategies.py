"""Options Lab. Preset two leg strategies.

Implements bull call spread, bear put spread, straddle, and strangle.
Each preset takes a single ATM strike (straddle), a strike pair
(spreads, strangle), and produces:

- combined payoff at expiry across a spot grid
- combined Greeks (sum of leg Greeks; sign reflects long / short)
- breakeven points implied by the payoff curve
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme

from terminal.adapters.options_adapter import all_greeks, black_scholes
from terminal.utils.density import dense_kpi_row, section_bar, signed_color
from terminal.utils.formatting import fmt_ratio


PRESETS: dict[str, dict[str, Any]] = {
    "Bull call spread":  {"legs": [("call", +1, "K1"), ("call", -1, "K2")], "needs": ["K1", "K2"]},
    "Bear put spread":   {"legs": [("put",  +1, "K2"), ("put",  -1, "K1")], "needs": ["K1", "K2"]},
    "Long straddle":     {"legs": [("call", +1, "K1"), ("put",  +1, "K1")], "needs": ["K1"]},
    "Long strangle":     {"legs": [("put",  +1, "K1"), ("call", +1, "K2")], "needs": ["K1", "K2"]},
}


def render_strategy_lab(spot: float, tau: float, rate: float, sigma: float, strikes: list[float]) -> None:
    """Top level renderer. Reads strikes from the available chain so the
    user only picks via existing chain values.
    """
    st.markdown(section_bar("STRATEGY LAB", source="local"), unsafe_allow_html=True)
    if not strikes:
        st.caption("DATA OFF | no strikes in chain")
        return
    atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot))
    col_p, col_k1, col_k2 = st.columns([3, 2, 2])
    preset = col_p.selectbox("Strategy", options=list(PRESETS.keys()), key="strategy_preset")
    needs = PRESETS[preset]["needs"]
    k1 = col_k1.selectbox("K1", options=strikes, index=atm_idx,
                          format_func=lambda v: f"{v:,.2f}", key="strategy_k1")
    if "K2" in needs:
        default_k2 = min(len(strikes) - 1, atm_idx + 4)
        k2 = col_k2.selectbox("K2", options=strikes, index=default_k2,
                              format_func=lambda v: f"{v:,.2f}", key="strategy_k2")
    else:
        k2 = float(k1)
    legs = _build_legs(preset, float(k1), float(k2), spot, tau, rate, sigma)
    if not legs:
        return
    grid, total_pnl = _combined_payoff(spot, legs)
    combined = _combined_greeks(legs)
    _render_combined_kpis(combined, legs)
    _render_combined_chart(grid, total_pnl, spot, legs, preset)


def _build_legs(preset: str, k1: float, k2: float, spot: float, tau: float, rate: float, sigma: float) -> list[dict[str, Any]]:
    legs: list[dict[str, Any]] = []
    for opt_type, qty, strike_key in PRESETS[preset]["legs"]:
        strike = k1 if strike_key == "K1" else k2
        price = black_scholes(spot, strike, tau, rate, sigma, option_type=opt_type)
        g = all_greeks(spot, strike, tau, rate, sigma, option_type=opt_type)
        legs.append({"type": opt_type, "qty": qty, "strike": float(strike), "price": float(price), "greeks": g})
    return legs


def _combined_payoff(spot: float, legs: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    grid = np.linspace(spot * 0.7, spot * 1.3, 400)
    total = np.zeros_like(grid)
    for leg in legs:
        intrinsic = (
            np.maximum(grid - leg["strike"], 0.0) if leg["type"] == "call"
            else np.maximum(leg["strike"] - grid, 0.0)
        )
        total += leg["qty"] * (intrinsic - leg["price"])
    return grid, total


def _combined_greeks(legs: list[dict[str, Any]]) -> dict[str, float]:
    keys = ["delta", "gamma", "theta", "vega", "rho"]
    out = {k: 0.0 for k in keys}
    net_premium = 0.0
    for leg in legs:
        for k in keys:
            out[k] += leg["qty"] * float(leg["greeks"].get(k, 0.0))
        net_premium += leg["qty"] * leg["price"]
    out["net_premium"] = net_premium
    return out


def _render_combined_kpis(combined: dict[str, float], legs: list[dict[str, Any]]) -> None:
    items = [
        {"label": "NET DEBIT (CR-)", "value": f"${combined['net_premium']:+,.2f}",
         "value_color": TOKENS["accent_danger"] if combined["net_premium"] > 0 else TOKENS["accent_success"]},
        {"label": "DELTA",  "value": fmt_ratio(combined["delta"], decimals=3, suffix=""),
         "value_color": signed_color(combined["delta"])},
        {"label": "GAMMA",  "value": fmt_ratio(combined["gamma"], decimals=4, suffix="")},
        {"label": "THETA",  "value": f"${combined['theta']:.2f}",
         "value_color": signed_color(combined["theta"])},
        {"label": "VEGA",   "value": f"${combined['vega']:.2f}",
         "value_color": signed_color(combined["vega"])},
        {"label": "LEGS",   "value": str(len(legs))},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)


def _render_combined_chart(grid: np.ndarray, pnl: np.ndarray, spot: float, legs: list[dict[str, Any]], preset: str) -> None:
    breakevens = _find_breakevens(grid, pnl)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=grid, y=pnl, name="Combined P&L", mode="lines",
        line={"width": 1.8, "color": TOKENS["accent_primary"]},
        fill="tozeroy", fillcolor="rgba(255,138,42,0.07)",
    ))
    fig.add_hline(y=0, line={"color": TOKENS["text_muted"], "width": 1})
    fig.add_vline(x=spot, line={"color": TOKENS["accent_info"], "width": 1.4, "dash": "dot"},
                  annotation_text=f"SPOT {spot:,.2f}", annotation_position="top")
    for be in breakevens:
        fig.add_vline(x=be, line={"color": TOKENS["accent_warning"], "width": 1.2, "dash": "dash"},
                      annotation_text=f"BE {be:,.2f}", annotation_position="bottom")
    legs_label = ", ".join(f"{leg['qty']:+d} {leg['type'].upper()} {leg['strike']:,.0f}" for leg in legs)
    fig.update_xaxes(title_text="Spot at expiry ($)")
    fig.update_yaxes(title_text="P&L ($)")
    fig.update_layout(title={"text": f"{preset}. {legs_label}"}, height=320)
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)


def _find_breakevens(grid: np.ndarray, pnl: np.ndarray) -> list[float]:
    """Linear interpolation between zero crossings of the combined payoff."""
    out: list[float] = []
    for i in range(1, len(pnl)):
        if pnl[i - 1] == 0:
            out.append(float(grid[i - 1]))
            continue
        if pnl[i - 1] * pnl[i] < 0:
            x0, x1 = float(grid[i - 1]), float(grid[i])
            y0, y1 = float(pnl[i - 1]), float(pnl[i])
            out.append(x0 - y0 * (x1 - x0) / (y1 - y0))
    return out
