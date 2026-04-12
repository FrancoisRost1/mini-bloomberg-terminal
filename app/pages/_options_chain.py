"""Options Lab. Chain table with ITM/ATM highlighting and IV smile re-export."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from style_inject import TOKENS

from app.pages._options_iv_smile import render_iv_smile_moneyness as render_iv_smile_moneyness  # noqa: F401  re export
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
    col_order = ["C Last", "C Chg", "C %Chg", "C Bid", "C Ask", "C Vol", "C OI", "C IV", "Strike", "P Last", "P Chg", "P %Chg", "P Bid", "P Ask", "P Vol", "P OI", "P IV"]
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


def _fmt_signed(v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return _DASH
    return f"{v:+.2f}"


def _fmt_signed_pct(v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return _DASH
    return f"{v:+.2f}%"


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
        f"{prefix}Last": df.get("last", pd.Series(dtype=float)).map(_fmt_price),
        f"{prefix}Chg": df.get("change", pd.Series(dtype=float)).map(_fmt_signed),
        f"{prefix}%Chg": df.get("pct_change", pd.Series(dtype=float)).map(_fmt_signed_pct),
        f"{prefix}Bid": df.get("bid", pd.Series(dtype=float)).map(_fmt_price),
        f"{prefix}Ask": df.get("ask", pd.Series(dtype=float)).map(_fmt_price),
        f"{prefix}Vol": df.get("volume", pd.Series(dtype=float)).map(_fmt_int),
        f"{prefix}OI":  df.get("open_interest", pd.Series(dtype=float)).map(_fmt_int),
    })
    iv = df.get("implied_volatility")
    if iv is not None:
        out[f"{prefix}IV"] = iv.map(_fmt_iv)
    return out


from app.pages._options_payoff import render_payoff_with_lines as render_payoff_with_lines  # noqa: F401,E402  re-export
