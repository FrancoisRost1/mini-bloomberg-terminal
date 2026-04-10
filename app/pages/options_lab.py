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

    expiry, opt_type, sigma = _render_inputs(chain, config)
    expiry_chain = chain.chains.get(expiry)
    if expiry_chain is None or expiry_chain.empty:
        st.markdown(inline_status_line("PARTIAL", source="yfinance"), unsafe_allow_html=True)
        return

    spot = resolve_spot(data_manager, ticker, fallback=chain.spot)
    if spot is None or spot != spot or spot <= 0:
        st.markdown(inline_status_line("PARTIAL", source="registry"), unsafe_allow_html=True)
        return

    atm_strike = float(expiry_chain.iloc[(expiry_chain["strike"] - spot).abs().argsort().iloc[0]]["strike"])
    strike = _render_strike_selector(expiry_chain, atm_strike)

    days = (pd.Timestamp(expiry) - pd.Timestamp(datetime.utcnow())).days
    tau = max(1 / 365.0, days / 365.0)
    rate = resolve_rate(data_manager, config)

    greeks = all_greeks(spot, strike, tau, rate, sigma, option_type=opt_type)
    price = black_scholes(spot, strike, tau, rate, sigma, option_type=opt_type)

    st.markdown(section_bar("GREEKS", source="yfinance + FRED"), unsafe_allow_html=True)
    safe_render(lambda: render_greeks_kpis(price, greeks), label="greeks", source="local")

    tab_p, tab_s, tab_iv = st.tabs(["PAYOFF", "SCENARIO", "IV SMILE"])
    with tab_p:
        safe_render(lambda: render_payoff(spot, strike, price, opt_type, config), label="payoff", source="local")
    with tab_s:
        safe_render(lambda: render_scenario(greeks, spot), label="scenario", source="local")
    with tab_iv:
        safe_render(lambda: render_iv_smile(expiry_chain, spot, tau, rate, config), label="iv_smile", source="yfinance")


def _render_strike_selector(expiry_chain, atm_strike: float) -> float:
    """Two ways to pick a strike: a selectbox of actual chain strikes,
    and a numeric input as an alternative for off chain values.
    """
    strikes = sorted({float(s) for s in expiry_chain["strike"].dropna().tolist()})
    if not strikes:
        return atm_strike
    atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - atm_strike))
    col_a, col_b = st.columns([3, 2])
    with col_a:
        chosen = st.selectbox(
            "Strike (chain)",
            options=strikes,
            index=atm_idx,
            format_func=lambda v: f"{v:,.2f}",
            key="opt_strike_select",
        )
    with col_b:
        manual = st.number_input(
            "Strike (manual)",
            min_value=float(strikes[0]),
            max_value=float(strikes[-1]),
            value=float(chosen),
            step=max(0.5, (strikes[-1] - strikes[0]) / 100.0),
            key="opt_strike_manual",
        )
    return float(manual)


def _render_inputs(chain, config) -> tuple[str, str, float]:
    expiries = chain.expiries()
    col_e, col_t, col_v = st.columns([3, 2, 2])
    expiry = col_e.selectbox("Expiry", options=expiries, label_visibility="collapsed")
    opt_type = col_t.selectbox("Type", options=["call", "put"], label_visibility="collapsed")
    sigma_default = float(config["options_lab"]["default_vol"])
    sigma = col_v.number_input(
        "Vol",
        min_value=0.01, max_value=5.0, value=sigma_default, step=0.01,
        label_visibility="collapsed",
    )
    return expiry, opt_type, float(sigma)


render()
