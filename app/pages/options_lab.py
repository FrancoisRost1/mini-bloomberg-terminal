"""ANALYTICS. Options Lab workspace.

Layout:
- compact input row (expiry, type, vol, strike) all on one line
- Greeks KPI strip immediately below the inputs
- compact subpanels for payoff, scenario, IV smile via tabs
- no raw tracebacks: failures become inline status text via safe_render
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

from app.pages._options_chain import (  # noqa: E402
    render_chain_table,
    render_iv_smile_moneyness,
    render_payoff_with_lines,
)
from app.pages._options_lab_helpers import (  # noqa: E402
    render_greeks_kpis,
    render_inputs_row,
    render_scenario,
    render_strike_selector,
    resolve_rate,
    resolve_spot,
)
from app.pages._options_strategies import render_strategy_lab  # noqa: E402
from terminal.adapters.options_adapter import all_greeks, black_scholes  # noqa: E402
from terminal.utils.density import section_bar  # noqa: E402
from terminal.utils.error_handling import (  # noqa: E402
    inline_status_line,
    is_error,
    safe_render,
)


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    ticker = st.session_state.get("active_ticker", "AAPL")

    styled_header(f"Options Lab. {ticker}", "European vanilla | BS Greeks | Brent IV")
    st.sidebar.markdown("### Options Lab")
    st.sidebar.caption(
        "European vanilla only. Greeks scenario is a local Taylor expansion. "
        "IV surface is strike wise per expiry. Risk free rate from FRED."
    )

    st.markdown(section_bar("CHAIN", source="yfinance"), unsafe_allow_html=True)
    chain = data_manager.get_options_chain(ticker)
    if is_error(chain) or chain.is_empty():
        st.markdown(inline_status_line("OFF", source="yfinance"), unsafe_allow_html=True)
        return

    expiry, opt_type, sigma = render_inputs_row(chain, config)
    expiry_chain = chain.chains.get(expiry)
    if expiry_chain is None or expiry_chain.empty:
        st.markdown(inline_status_line("PARTIAL", source="yfinance"), unsafe_allow_html=True)
        return

    spot = resolve_spot(data_manager, ticker, fallback=chain.spot)
    if spot is None or spot != spot or spot <= 0:
        st.markdown(inline_status_line("PARTIAL", source="registry"), unsafe_allow_html=True)
        return

    atm_strike = float(expiry_chain.iloc[(expiry_chain["strike"] - spot).abs().argsort().iloc[0]]["strike"])
    strike = render_strike_selector(expiry_chain, atm_strike)

    days = (pd.Timestamp(expiry) - pd.Timestamp(datetime.utcnow())).days
    tau = max(1 / 365.0, days / 365.0)
    rate = resolve_rate(data_manager, config)

    greeks = all_greeks(spot, strike, tau, rate, sigma, option_type=opt_type)
    price = black_scholes(spot, strike, tau, rate, sigma, option_type=opt_type)

    st.markdown(section_bar("GREEKS", source="yfinance + FRED"), unsafe_allow_html=True)
    safe_render(lambda: render_greeks_kpis(price, greeks), label="greeks", source="local")

    # Flat scrollable layout. Every section is visible without clicks;
    # the Bloomberg density goal is zero dead vertical space.
    row1_l, row1_r = st.columns([1, 1])
    with row1_l:
        st.markdown(section_bar("PAYOFF", source="local"), unsafe_allow_html=True)
        safe_render(
            lambda: render_payoff_with_lines(spot, strike, price, opt_type, config),
            label="payoff", source="local",
        )
    with row1_r:
        st.markdown(section_bar("SCENARIO (7D FWD)", source="local"), unsafe_allow_html=True)
        safe_render(lambda: render_scenario(greeks, spot, price), label="scenario", source="local")

    row2_l, row2_r = st.columns([1, 1])
    with row2_l:
        safe_render(
            lambda: render_iv_smile_moneyness(expiry_chain, spot, tau, rate, config),
            label="iv_smile", source="yfinance",
        )
    with row2_r:
        strikes_sorted = sorted({float(s) for s in expiry_chain["strike"].dropna().tolist()})
        safe_render(
            lambda: render_strategy_lab(spot, tau, rate, sigma, strikes_sorted),
            label="strategy", source="local",
        )

    safe_render(lambda: render_chain_table(expiry_chain, spot), label="chain", source="yfinance")


render()
