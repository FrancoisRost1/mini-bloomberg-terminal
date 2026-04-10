"""ANALYTICS. Options Lab workspace.

Renders the Greeks dashboard, IV from the live chain, payoff diagram,
and a Greeks based P&L scenario. Helpers live in
``_options_lab_helpers.py``.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from style_inject import styled_header  # noqa: E402

from app.pages._options_lab_helpers import (  # noqa: E402
    render_greeks_kpis,
    render_iv_smile,
    render_payoff,
    render_scenario,
    resolve_rate,
    resolve_spot,
)
from terminal.adapters.options_adapter import all_greeks, black_scholes  # noqa: E402
from terminal.utils.density import section_bar  # noqa: E402
from terminal.utils.error_handling import degraded_card, is_error, unavailable_card  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    ticker = st.session_state.get("active_ticker", "AAPL")

    styled_header(f"Options Lab. {ticker}", "European vanilla | BS Greeks | Brent IV")
    st.sidebar.markdown("### Options Lab limitations")
    st.sidebar.caption(
        "European vanilla only. No delta hedging simulation. No early "
        "exercise. Greeks scenario is a local Taylor expansion, not a "
        "full repricing. IV surface is strike wise only (single expiry). "
        "Risk free rate is fetched from FRED (DGS2)."
    )

    chain = data_manager.get_options_chain(ticker)
    if is_error(chain):
        st.markdown(degraded_card(chain.reason, chain.provider), unsafe_allow_html=True)
        return
    if chain.is_empty():
        st.markdown(unavailable_card(f"No options chain available for {ticker}", "provider returned empty"), unsafe_allow_html=True)
        return

    expiries = chain.expiries()
    st.markdown(section_bar("CONTRACT INPUTS"), unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    expiry = col1.selectbox("Expiry", options=expiries)
    opt_type = col2.selectbox("Type", options=["call", "put"])
    sigma_default = float(config["options_lab"]["default_vol"])
    sigma = col3.number_input("Vol (annual)", min_value=0.01, max_value=5.0, value=sigma_default, step=0.01)

    expiry_chain = chain.chains[expiry]
    if expiry_chain.empty:
        st.markdown(degraded_card("empty chain for expiry", chain.provider), unsafe_allow_html=True)
        return

    spot = resolve_spot(data_manager, ticker, fallback=chain.spot)
    if spot is None or spot != spot or spot <= 0:
        st.markdown(degraded_card("could not resolve spot price for greeks", "registry"), unsafe_allow_html=True)
        return

    atm_strike = float(expiry_chain.iloc[(expiry_chain["strike"] - spot).abs().argsort().iloc[0]]["strike"])
    strike = st.slider(
        "Strike",
        min_value=float(expiry_chain["strike"].min()),
        max_value=float(expiry_chain["strike"].max()),
        value=atm_strike,
    )

    days_to_expiry = (pd.Timestamp(expiry) - pd.Timestamp(datetime.utcnow())).days
    tau = max(1 / 365.0, days_to_expiry / 365.0)
    rate = resolve_rate(data_manager, config)

    greeks = all_greeks(spot, strike, tau, rate, sigma, option_type=opt_type)
    price = black_scholes(spot, strike, tau, rate, sigma, option_type=opt_type)

    st.markdown(section_bar("GREEKS"), unsafe_allow_html=True)
    render_greeks_kpis(price, greeks)
    st.markdown(section_bar("PAYOFF"), unsafe_allow_html=True)
    render_payoff(spot, strike, price, opt_type, config)
    st.markdown(section_bar("SCENARIO"), unsafe_allow_html=True)
    render_scenario(greeks, spot)
    st.markdown(section_bar("IV SMILE"), unsafe_allow_html=True)
    render_iv_smile(expiry_chain, spot, tau, rate, config)


render()
