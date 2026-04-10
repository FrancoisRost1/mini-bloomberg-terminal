"""ANALYTICS: Options Lab workspace.

Renders: Greeks dashboard, IV from the live chain, vol surface preview,
payoff diagram, and a Greeks-based P&L scenario grid.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from terminal.adapters.options_adapter import all_greeks, black_scholes, implied_vol
from terminal.engines.pnl_engine import compute_option_payoff, compute_option_scenario
from terminal.utils.chart_helpers import interpretation_callout, line_chart
from terminal.utils.error_handling import degraded_card, is_error, unavailable_card
from terminal.utils.formatting import fmt_ratio, styled_kpi


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    ticker = st.session_state.get("active_ticker", "AAPL")

    st.title(f"Options Lab: {ticker}")
    st.caption("What is the options risk and reward math?")
    st.sidebar.markdown("### Options Lab limitations")
    st.sidebar.caption(
        "European vanilla only. No delta hedging simulation. No early "
        "exercise. Greeks scenario is a local Taylor expansion, not a full "
        "repricing. IV surface is strike-wise only (single expiry)."
    )

    chain = data_manager.get_options_chain(ticker)
    if is_error(chain):
        st.markdown(degraded_card(chain.reason, chain.provider), unsafe_allow_html=True)
        return
    if chain.is_empty():
        st.markdown(unavailable_card(f"No options chain available for {ticker}", "provider returned empty"), unsafe_allow_html=True)
        return

    expiries = chain.expiries()
    col1, col2, col3 = st.columns(3)
    expiry = col1.selectbox("Expiry", options=expiries)
    opt_type = col2.selectbox("Type", options=["call", "put"])
    sigma_default = float(config["options_lab"]["default_vol"])
    sigma = col3.number_input("Vol (annual)", min_value=0.01, max_value=5.0, value=sigma_default, step=0.01)

    expiry_chain = chain.chains[expiry]
    spot = chain.spot or 100.0
    if expiry_chain.empty:
        st.markdown(degraded_card("empty chain for expiry", chain.provider), unsafe_allow_html=True)
        return
    atm_strike = float(expiry_chain.iloc[(expiry_chain["strike"] - spot).abs().argsort().iloc[0]]["strike"])
    strike = st.slider("Strike", min_value=float(expiry_chain["strike"].min()),
                       max_value=float(expiry_chain["strike"].max()), value=atm_strike)

    tau = max(1 / 365.0, (pd.Timestamp(expiry) - pd.Timestamp.utcnow()).days / 365.0)
    rate = 0.04
    greeks = all_greeks(spot, strike, tau, rate, sigma, option_type=opt_type)
    price = black_scholes(spot, strike, tau, rate, sigma, option_type=opt_type)

    _render_greeks_kpis(price, greeks)
    _render_payoff(spot, strike, price, opt_type, config)
    _render_scenario(greeks, spot, config)
    _render_iv_from_chain(expiry_chain, spot, tau, rate, config)


def _render_greeks_kpis(price, greeks) -> None:
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


def _render_payoff(spot, strike, premium, opt_type, config) -> None:
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


def _render_scenario(greeks, spot, config) -> None:
    spot_range = np.linspace(spot * 0.8, spot * 1.2, 100)
    df = compute_option_scenario(greeks, spot_range, vol_shift=0.0, time_decay_days=7)
    fig = line_chart({"7d Greeks P&L": df["pnl"]}, title="Greeks Scenario (7d forward)", y_unit="P&L ($)", x_unit="Spot ($)")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        interpretation_callout(
            observation=f"Greeks-based P&L over a +/-20% spot move, 7 days forward.",
            interpretation="Local Taylor expansion: delta + 0.5*gamma*dS^2 + vega*dSigma + theta*dT.",
            implication="Use for intuition, not pricing. Large moves need a full reprice.",
        ),
        unsafe_allow_html=True,
    )


def _render_iv_from_chain(chain_df, spot, tau, rate, config) -> None:
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
    fig = line_chart({"Implied Vol": df.set_index("strike")["iv"]}, title="IV Smile (selected expiry)", y_unit="vol", x_unit="Strike ($)")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        interpretation_callout(
            observation="Implied vol by strike for the selected expiry.",
            interpretation="A convex smile reflects fat tails priced into out-of-the-money strikes.",
            implication="Asymmetric skew (left side richer) is the market pricing crash risk.",
        ),
        unsafe_allow_html=True,
    )


render()
