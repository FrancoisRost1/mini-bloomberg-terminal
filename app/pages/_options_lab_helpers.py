"""Options Lab page helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from style_inject import TOKENS, styled_card

from terminal.adapters.options_adapter import implied_vol
from terminal.engines.pnl_engine import compute_option_payoff, compute_option_scenario
from terminal.utils.chart_helpers import interpretation_callout_html, line_chart
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


def render_payoff(spot: float, strike: float, premium: float, opt_type: str, config: dict[str, Any]) -> None:
    payoff_cfg = config["options_lab"]["payoff"]
    df = compute_option_payoff(
        spot=spot, strike=strike, premium=premium, option_type=opt_type,
        spot_range_pct=float(payoff_cfg["spot_range_pct"]), points=int(payoff_cfg["spot_points"]),
    )
    chart_col, table_col = st.columns([2, 3])
    with chart_col:
        fig = line_chart({"P&L": df["pnl"]}, title="Expiration Payoff", y_unit="P&L ($)", x_unit="Spot at expiry ($)")
        st.plotly_chart(fig, use_container_width=True)
    with table_col:
        sample = df.iloc[::max(1, len(df) // 8)].head(8)
        sample_table = pd.DataFrame({
            "Spot": [f"${idx:,.0f}" for idx in sample.index],
            "P&L": [f"${v:+,.0f}" for v in sample["pnl"].values],
        })
        st.dataframe(sample_table, use_container_width=True, hide_index=True)
    breakeven = strike + premium if opt_type == "call" else strike - premium
    styled_card(
        interpretation_callout_html(
            observation=f"Breakeven at ${breakeven:.2f}, spot ${spot:.2f}.",
            interpretation="Expiration payoff isolates intrinsic value minus premium, ignoring time and vol risk.",
            implication="Use the scenario row below for pre expiry Greeks based P&L.",
        ),
        accent_color=TOKENS["accent_primary"],
    )


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
        for p in pct_levels:
            target = spot * (1 + p)
            nearest = df.index[(df.index - target).abs().argmin()]
            pnl = df.loc[nearest, "pnl"]
            rows.append((f"{p * 100:+.0f}%", f"${pnl:+,.0f}"))
        st.dataframe(pd.DataFrame(rows, columns=["Move", "P&L"]), use_container_width=True, hide_index=True)


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
    chart_col, table_col = st.columns([2, 3])
    with chart_col:
        fig = line_chart(
            {"Implied Vol": df.set_index("strike")["iv"]},
            title="IV Smile (selected expiry)", y_unit="vol", x_unit="Strike ($)",
        )
        st.plotly_chart(fig, use_container_width=True)
    with table_col:
        smile_table = pd.DataFrame({
            "Strike": [f"${s:,.0f}" for s in df["strike"]],
            "IV": [f"{v * 100:.1f}%" for v in df["iv"]],
        })
        st.dataframe(smile_table, use_container_width=True, hide_index=True)


def resolve_spot(data_manager, ticker: str, fallback: float | None) -> float | None:
    prices = data_manager.get_prices(ticker, period="1mo")
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
