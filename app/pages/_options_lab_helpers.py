"""Options Lab page helpers.

The chain table, IV smile, and payoff with breakeven / spot lines
live in ``_options_chain.py``. Strategy presets live in
``_options_strategies.py``. This module keeps the Greeks KPIs, the
Greeks scenario panel, and the spot / rate resolvers.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from terminal.engines.pnl_engine import compute_option_scenario
from terminal.utils.chart_helpers import line_chart
from terminal.utils.density import dense_kpi_row, signed_color
from terminal.utils.error_handling import is_error
from terminal.utils.formatting import fmt_ratio


def render_greeks_kpis(price: float, greeks: dict[str, float]) -> None:
    items = [
        {"label": "BS PRICE", "value": f"${price:,.2f}"},
        {"label": "DELTA", "value": fmt_ratio(greeks["delta"], decimals=3, suffix=""),
         "delta_color": signed_color(greeks["delta"])},
        {"label": "GAMMA", "value": fmt_ratio(greeks["gamma"], decimals=4, suffix=""),
         "delta_color": signed_color(greeks["gamma"])},
        {"label": "THETA / DAY", "value": f"${greeks['theta']:.2f}",
         "delta_color": signed_color(greeks["theta"])},
        {"label": "VEGA / 1%", "value": f"${greeks['vega']:.2f}",
         "delta_color": signed_color(greeks["vega"])},
        {"label": "RHO / 1%", "value": f"${greeks['rho']:.2f}",
         "delta_color": signed_color(greeks["rho"])},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)


def render_scenario(greeks: dict[str, float], spot: float) -> None:
    spot_range = np.linspace(spot * 0.8, spot * 1.2, 100)
    df = compute_option_scenario(greeks, spot_range, vol_shift=0.0, time_decay_days=7)
    chart_col, table_col = st.columns([2, 3])
    with chart_col:
        fig = line_chart(
            {"7d Greeks P&L": df["pnl"]},
            title="Greeks Scenario (7 days forward)",
            y_unit="P&L ($)", x_unit="Spot ($)",
        )
        st.plotly_chart(fig, use_container_width=True)
    with table_col:
        pct_levels = [-0.2, -0.1, -0.05, 0, 0.05, 0.1, 0.2]
        rows = []
        idx_values = df.index.to_numpy()
        for p in pct_levels:
            target = spot * (1 + p)
            nearest_pos = int(np.abs(idx_values - target).argmin())
            nearest = df.index[nearest_pos]
            pnl = df.loc[nearest, "pnl"]
            rows.append((f"{p * 100:+.0f}%", f"${pnl:+,.0f}"))
        st.dataframe(pd.DataFrame(rows, columns=["Move", "P&L"]), use_container_width=True, hide_index=True)


def render_strike_selector(expiry_chain: pd.DataFrame, atm_strike: float) -> float:
    """Two ways to pick a strike: a selectbox of actual chain strikes,
    and a number input as an alternative for off chain values.
    """
    strikes = sorted({float(s) for s in expiry_chain["strike"].dropna().tolist()})
    if not strikes:
        return atm_strike
    atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - atm_strike))
    col_a, col_b = st.columns([3, 2])
    with col_a:
        chosen = st.selectbox(
            "Strike (chain)", options=strikes, index=atm_idx,
            format_func=lambda v: f"{v:,.2f}", key="opt_strike_select",
        )
    with col_b:
        manual = st.number_input(
            "Strike (manual)",
            min_value=float(strikes[0]), max_value=float(strikes[-1]),
            value=float(chosen),
            step=max(0.5, (strikes[-1] - strikes[0]) / 100.0),
            key="opt_strike_manual",
        )
    return float(manual)


def render_inputs_row(chain, config: dict[str, Any]) -> tuple[str, str, float]:
    expiries = chain.expiries()
    col_e, col_t, col_v = st.columns([3, 2, 2])
    expiry = col_e.selectbox("Expiry", options=expiries, label_visibility="collapsed")
    opt_type = col_t.selectbox("Type", options=["call", "put"], label_visibility="collapsed")
    sigma_default = float(config["options_lab"]["default_vol"])
    sigma = col_v.number_input(
        "Vol", min_value=0.01, max_value=5.0, value=sigma_default, step=0.01,
        label_visibility="collapsed",
    )
    return expiry, opt_type, float(sigma)


def resolve_spot(data_manager, ticker: str, fallback: float | None) -> float | None:
    prices = data_manager.get_any_prices(ticker, period="1mo")
    if not is_error(prices) and not prices.is_empty():
        return prices.last_close()
    if fallback and fallback == fallback and fallback > 0:
        return float(fallback)
    return None


def resolve_rate(data_manager, config: dict[str, Any]) -> float:
    series_id = config["options_lab"]["risk_free_rate_series"]
    macro = data_manager.get_macro([series_id])
    if is_error(macro):
        return 0.04
    latest = macro.latest(series_id)
    if latest != latest:
        return 0.04
    return float(latest) / 100.0
