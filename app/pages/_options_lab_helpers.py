"""Options Lab page helpers.

Split out of ``options_lab.py`` to keep the page under the per-module
line budget. Pure rendering helpers and value resolvers; no widgets.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from terminal.adapters.options_adapter import implied_vol
from terminal.engines.pnl_engine import compute_option_payoff, compute_option_scenario
from terminal.utils.chart_helpers import interpretation_callout, line_chart
from terminal.utils.error_handling import is_error
from terminal.utils.formatting import fmt_ratio, styled_kpi


def render_greeks_kpis(price: float, greeks: dict[str, float]) -> None:
    cols = st.columns(6)
    with cols[0]:
        st.markdown(styled_kpi("BS Price", f"${price:,.2f}"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(styled_kpi("Delta", fmt_ratio(greeks["delta"], decimals=3, suffix="")), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(styled_kpi("Gamma", fmt_ratio(greeks["gamma"], decimals=4, suffix="")), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(styled_kpi("Theta/day", f"${greeks['theta']:.2f}"), unsafe_allow_html=True)
    with cols[4]:
        st.markdown(styled_kpi("Vega/1%", f"${greeks['vega']:.2f}"), unsafe_allow_html=True)
    with cols[5]:
        st.markdown(styled_kpi("Rho/1%", f"${greeks['rho']:.2f}"), unsafe_allow_html=True)


def render_payoff(spot: float, strike: float, premium: float, opt_type: str, config: dict[str, Any]) -> None:
    payoff_cfg = config["options_lab"]["payoff"]
    df = compute_option_payoff(
        spot=spot, strike=strike, premium=premium, option_type=opt_type,
        spot_range_pct=float(payoff_cfg["spot_range_pct"]), points=int(payoff_cfg["spot_points"]),
    )
    fig = line_chart({"P&L": df["pnl"]}, title="Expiration Payoff", y_unit="P&L ($)", x_unit="Spot at expiry ($)")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        interpretation_callout(
            observation=f"Breakeven vs spot ${spot:.2f}.",
            interpretation="Expiration payoff isolates intrinsic value minus premium, ignoring time and vol risk.",
            implication="Use the scenario grid below for pre-expiry Greeks-based P&L.",
        ),
        unsafe_allow_html=True,
    )


def render_scenario(greeks: dict[str, float], spot: float) -> None:
    spot_range = np.linspace(spot * 0.8, spot * 1.2, 100)
    df = compute_option_scenario(greeks, spot_range, vol_shift=0.0, time_decay_days=7)
    fig = line_chart({"7d Greeks P&L": df["pnl"]}, title="Greeks Scenario (7d forward)", y_unit="P&L ($)", x_unit="Spot ($)")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        interpretation_callout(
            observation="Greeks-based P&L over a +/-20% spot move, 7 days forward.",
            interpretation="Local Taylor expansion: delta + 0.5*gamma*dS^2 + vega*dSigma + theta*dT.",
            implication="Use for intuition, not pricing. Large moves need a full reprice.",
        ),
        unsafe_allow_html=True,
    )


def render_iv_smile(chain_df: pd.DataFrame, spot: float, tau: float, rate: float, config: dict[str, Any]) -> None:
    solver = config["options_lab"]["iv_solver"]
    sample = chain_df[chain_df["type"] == "call"].head(15)
    if sample.empty:
        return
    ivs = []
    for _, row in sample.iterrows():
        mid = 0.5 * (row.get("bid", np.nan) + row.get("ask", np.nan))
        iv = implied_vol(mid, spot, float(row["strike"]), tau, rate, 0.0, "call", solver)
        ivs.append({"strike": float(row["strike"]), "iv": iv})
    df = pd.DataFrame(ivs).dropna()
    if df.empty:
        return
    fig = line_chart(
        {"Implied Vol": df.set_index("strike")["iv"]},
        title="IV Smile (selected expiry)", y_unit="vol", x_unit="Strike ($)",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        interpretation_callout(
            observation="Implied vol by strike for the selected expiry.",
            interpretation="A convex smile reflects fat tails priced into out-of-the-money strikes.",
            implication="Asymmetric skew (left side richer) is the market pricing crash risk.",
        ),
        unsafe_allow_html=True,
    )


def resolve_spot(data_manager, ticker: str, fallback: float | None) -> float | None:
    """Pull the latest close from the equity provider; never trust the chain payload alone."""
    prices = data_manager.get_prices(ticker, period="1mo")
    if not is_error(prices) and not prices.is_empty():
        return prices.last_close()
    if fallback and fallback == fallback and fallback > 0:
        return float(fallback)
    return None


def resolve_rate(data_manager, config: dict[str, Any]) -> float:
    """Fetch the risk-free rate from FRED via the macro provider.

    Treasury yields are percent units (4.25 for 4.25%); divide by 100
    to get a decimal. Falls back to 4% if FRED is unreachable so the
    page still renders.
    """
    series_id = config["options_lab"]["risk_free_rate_series"]
    macro = data_manager.get_macro([series_id])
    if is_error(macro):
        return 0.04
    latest = macro.latest(series_id)
    if latest != latest:
        return 0.04
    return float(latest) / 100.0
