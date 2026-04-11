"""Options Lab. Chain table and payoff annotations.

Pulled out of _options_lab_helpers.py so the helpers module stays
under the per module budget. The IV smile helper lives in
_options_iv_smile.py and is re-exported from here so existing call
sites can import from this module.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme

from app.pages._options_iv_smile import render_iv_smile_moneyness as render_iv_smile_moneyness  # noqa: F401  re export
from terminal.engines.pnl_engine import compute_option_payoff
from terminal.utils.density import section_bar
from terminal.utils.error_handling import inline_status_line


def render_chain_table(expiry_chain: pd.DataFrame, spot: float) -> None:
    """Calls + puts side by side: strike, bid, ask, volume, OI, IV.

    ITM rows get a faint amber background on their side (ITM calls
    below spot, ITM puts above spot). The strike nearest to spot is
    highlighted with the project accent so the ATM anchor is obvious.
    Numeric columns are right-aligned in monospace via the Styler.
    """
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
    # pd.merge(how="outer") inserts NaN / None for rows where one
    # side has no entry. Those leak as the string "None" when a pandas
    # Styler renders them. Normalise every missing cell to a dash so
    # the table reads cleanly.
    string_cols = [c for c in merged.columns if c != "Strike"]
    for c in string_cols:
        merged[c] = merged[c].fillna(_DASH)
    # Drop any strike where every quote column on both sides is a
    # dash. A row like that carries no information.
    if string_cols:
        row_has_data = merged[string_cols].apply(
            lambda row: any(str(v) != _DASH for v in row),
            axis=1,
        )
        merged = merged[row_has_data]
    merged = merged.sort_values("Strike").reset_index(drop=True)
    if merged.empty:
        st.markdown(inline_status_line("PARTIAL", source="yfinance"), unsafe_allow_html=True)
        return
    raw_strikes = merged["Strike"].astype(float).to_numpy()
    atm_idx = int(np.argmin(np.abs(raw_strikes - spot))) if len(raw_strikes) else -1
    merged["Strike"] = merged["Strike"].map(lambda v: f"{v:,.2f}")
    col_order = ["C Bid", "C Ask", "C Vol", "C OI", "C IV", "Strike", "P Bid", "P Ask", "P Vol", "P OI", "P IV"]
    merged = merged.reindex(columns=[c for c in col_order if c in merged.columns])

    call_cols = [c for c in merged.columns if c.startswith("C ")]
    put_cols = [c for c in merged.columns if c.startswith("P ")]
    numeric_cols = call_cols + put_cols + ["Strike"]
    accent = TOKENS["accent_primary"]
    itm_tint = "rgba(224,112,32,0.10)"

    def _row_style(row):
        styles: list[str] = []
        strike_val = raw_strikes[row.name] if row.name < len(raw_strikes) else float("nan")
        is_atm = (row.name == atm_idx)
        for col in merged.columns:
            css = ""
            if col in numeric_cols:
                css += "text-align:right;font-family:'JetBrains Mono',monospace;"
            if is_atm:
                css += f"background-color:rgba(224,112,32,0.22);color:{accent};font-weight:700;"
            else:
                if col.startswith("C ") and strike_val < spot:
                    css += f"background-color:{itm_tint};"
                elif col.startswith("P ") and strike_val > spot:
                    css += f"background-color:{itm_tint};"
            styles.append(css)
        return styles

    styled = merged.style.apply(_row_style, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)
    st.caption(f"Spot {spot:,.2f}. ATM row accent orange, ITM side amber tint. Strikes inside the ATM band usually have the tightest bid ask.")


_DASH = "-"


def _fmt_price(v) -> str:
    return f"{v:,.2f}" if v is not None and v == v else _DASH


def _fmt_int(v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return _DASH
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return _DASH


def _fmt_iv(v) -> str:
    if v is None or (isinstance(v, float) and v != v) or not (v > 0):
        return _DASH
    return f"{v * 100:.1f}%"


def _side_frame(chain: pd.DataFrame, side: str) -> pd.DataFrame:
    df = chain[chain["type"] == side].copy()
    if df.empty:
        return pd.DataFrame()
    # Drop rows where bid AND ask are both missing on this side. Those
    # strikes carry no quotes and only bloat the chain table.
    bid = df.get("bid", pd.Series(dtype=float))
    ask = df.get("ask", pd.Series(dtype=float))
    has_quote = bid.notna() | ask.notna()
    df = df[has_quote].copy()
    if df.empty:
        return pd.DataFrame()
    prefix = "C " if side == "call" else "P "
    out = pd.DataFrame({
        "Strike": df["strike"].astype(float),
        f"{prefix}Bid": df.get("bid", pd.Series(dtype=float)).map(_fmt_price),
        f"{prefix}Ask": df.get("ask", pd.Series(dtype=float)).map(_fmt_price),
        f"{prefix}Vol": df.get("volume", pd.Series(dtype=float)).map(_fmt_int),
        f"{prefix}OI":  df.get("open_interest", pd.Series(dtype=float)).map(_fmt_int),
    })
    iv = df.get("implied_volatility")
    if iv is not None:
        out[f"{prefix}IV"] = iv.map(_fmt_iv)
    return out


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
    fig.update_layout(title={"text": f"Expiration Payoff. {opt_type.upper()} K {strike:,.2f}"}, height=260)
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
