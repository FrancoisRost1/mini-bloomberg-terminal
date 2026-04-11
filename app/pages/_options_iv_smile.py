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

from style_inject import TOKENS, apply_plotly_theme, styled_card

from terminal.adapters.options_adapter import implied_vol
from terminal.utils.chart_helpers import interpretation_callout_html
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
    fig.update_layout(title={"text": "IV Smile. selected expiry"}, height=260,
                      legend={"orientation": "h", "y": 1.1, "x": 0})
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

    # Skew readout. Fills the vertical gap between the IV smile chart
    # and the full-width chain section so the left column ends at the
    # same level as the strategy lab on the right.
    observation, interpretation, implication = _skew_narrative(rows)
    styled_card(
        interpretation_callout_html(
            observation=observation,
            interpretation=interpretation,
            implication=implication,
        ),
        accent_color=TOKENS["accent_primary"],
    )


def _skew_narrative(rows: pd.DataFrame) -> tuple[str, str, str]:
    """Observation / interpretation / implication for the IV smile.

    Reads the 25 delta proxy (rough ~10 percent away from ATM on
    either side) and reports the put over call premium as the
    directional skew so the callout is grounded in real numbers.
    """
    if rows is None or rows.empty:
        return (
            "Smile not available for this expiry.",
            "Provider did not return enough strikes with valid IVs.",
            "Fall back to the default vol input for scenario and strategy math.",
        )
    puts = rows[rows["type"] == "put"]
    calls = rows[rows["type"] == "call"]
    atm_iv = float("nan")
    if not rows.empty:
        atm_row = rows.iloc[rows["moneyness"].abs().argsort()[:1]]
        atm_iv = float(atm_row["iv"].iloc[0]) * 100.0
    put_wing = _wing_iv(puts, target=-0.10)
    call_wing = _wing_iv(calls, target=0.10)
    pcs = put_wing - call_wing if (put_wing == put_wing and call_wing == call_wing) else float("nan")
    pcs_txt = f"{pcs * 100:+.1f} IV pts" if pcs == pcs else "n/a"
    atm_txt = f"{atm_iv:.1f}%" if atm_iv == atm_iv else "n/a"
    direction = "down" if (pcs == pcs and pcs > 0) else ("up" if (pcs == pcs and pcs < 0) else "flat")
    observation = f"ATM IV {atm_txt}. Put vs call wing skew {pcs_txt}."
    interpretation = (
        f"Skew reads {direction}. Put side priced {'richer' if direction == 'down' else ('cheaper' if direction == 'up' else 'in line')} "
        f"than equidistant calls, consistent with the market pricing "
        f"{'downside protection' if direction == 'down' else ('upside speculation' if direction == 'up' else 'symmetric tail risk')}."
    )
    implication = (
        "A defined risk put spread vs a long put captures premium "
        "when the wing is rich; an outright call is the better "
        "expression when the wing is cheap."
    )
    return observation, interpretation, implication


def _wing_iv(side: pd.DataFrame, target: float) -> float:
    """Return the IV of the strike nearest to ``target`` moneyness on
    a single-side frame. ``target`` is in log-moneyness units (e.g.
    -0.10 for ~10% OTM puts). Falls back to NaN on an empty frame.
    """
    if side is None or side.empty:
        return float("nan")
    idx = (side["moneyness"] - target).abs().idxmin()
    return float(side.loc[idx, "iv"])


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
