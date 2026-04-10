"""Options Lab. Chain table, moneyness IV smile, payoff annotations.

Pulled out of _options_lab_helpers.py so the helpers module stays
under the per module budget. All renderers are tolerant of missing
columns and degrade to inline status text instead of raising.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme

from terminal.adapters.options_adapter import implied_vol
from terminal.engines.pnl_engine import compute_option_payoff
from terminal.utils.density import section_bar
from terminal.utils.error_handling import inline_status_line


def render_chain_table(expiry_chain: pd.DataFrame, spot: float) -> None:
    """Calls + puts side by side: strike, bid, ask, volume, OI, IV."""
    st.markdown(section_bar("FULL CHAIN", source="yfinance"), unsafe_allow_html=True)
    if expiry_chain is None or expiry_chain.empty:
        st.markdown(inline_status_line("OFF", source="yfinance"), unsafe_allow_html=True)
        return
    calls = _side_frame(expiry_chain, "call")
    puts = _side_frame(expiry_chain, "put")
    if calls.empty and puts.empty:
        st.markdown(inline_status_line("OFF", source="yfinance"), unsafe_allow_html=True)
        return
    merged = pd.merge(calls, puts, on="Strike", how="outer", suffixes=("", "")).sort_values("Strike")
    merged["Strike"] = merged["Strike"].map(lambda v: f"{v:,.2f}")
    # Order: call columns, strike (centered), put columns
    col_order = ["C Bid", "C Ask", "C Vol", "C OI", "C IV", "Strike", "P Bid", "P Ask", "P Vol", "P OI", "P IV"]
    merged = merged.reindex(columns=[c for c in col_order if c in merged.columns])
    st.dataframe(merged, use_container_width=True, hide_index=True)
    st.caption(f"Spot {spot:,.2f}. Strikes inside the ATM band tend to have the tightest bid ask.")


def _side_frame(chain: pd.DataFrame, side: str) -> pd.DataFrame:
    df = chain[chain["type"] == side].copy()
    if df.empty:
        return pd.DataFrame()
    prefix = "C " if side == "call" else "P "
    out = pd.DataFrame({
        "Strike": df["strike"].astype(float),
        f"{prefix}Bid": df.get("bid", pd.Series(dtype=float)).map(lambda v: f"{v:,.2f}" if v == v else "n/a"),
        f"{prefix}Ask": df.get("ask", pd.Series(dtype=float)).map(lambda v: f"{v:,.2f}" if v == v else "n/a"),
        f"{prefix}Vol": df.get("volume", pd.Series(dtype=float)).fillna(0).astype(int).map(lambda v: f"{v:,}"),
        f"{prefix}OI":  df.get("open_interest", pd.Series(dtype=float)).fillna(0).astype(int).map(lambda v: f"{v:,}"),
    })
    iv = df.get("implied_volatility")
    if iv is not None:
        out[f"{prefix}IV"] = iv.map(lambda v: f"{v * 100:.1f}%" if v == v and v > 0 else "n/a")
    return out


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


def render_payoff_with_lines(spot: float, strike: float, premium: float, opt_type: str, config: dict[str, Any]) -> None:
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
    fig.update_layout(title={"text": f"Expiration Payoff. {opt_type.upper()} K {strike:,.2f}"}, height=300)
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
