"""Comps page historical valuation range.

Computes annual EV/EBITDA for the last five fiscal years using the
FMP income / balance statements and the year-end share price pulled
from the cached 5-year price series. Renders a horizontal range bar
showing 5Y low, median, high, and the current multiple marker so the
user can see whether the stock is expensive vs its own history.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme

from terminal.utils.density import section_bar
from terminal.utils.error_handling import is_error


def _annual_ev_ebitda(fundamentals, close_series: pd.Series) -> pd.DataFrame:
    """Year, EV/EBITDA pairs across the available annual statements.

    EV = market cap at fiscal year end + net debt (total debt - cash)
    Market cap = price on (or before) fiscal period end * shares outstanding
    shares outstanding = latest known (approx; FMP stable/ does not give
    per-year counts reliably, so we use the profile mktCap / current
    price as a shares proxy).
    """
    income = getattr(fundamentals, "income_statement", pd.DataFrame())
    balance = getattr(fundamentals, "balance_sheet", pd.DataFrame())
    if income is None or balance is None or income.empty or balance.empty:
        return pd.DataFrame(columns=["year", "ev_ebitda"])

    mkt_cap = float(getattr(fundamentals, "market_cap", float("nan")) or float("nan"))
    if close_series is None or close_series.empty or math.isnan(mkt_cap) or mkt_cap <= 0:
        return pd.DataFrame(columns=["year", "ev_ebitda"])
    last_price = float(close_series.iloc[-1])
    if last_price <= 0:
        return pd.DataFrame(columns=["year", "ev_ebitda"])
    shares_approx = mkt_cap / last_price

    rows: list[dict] = []
    ebitda_col = "ebitda" if "ebitda" in income.columns else None
    op_inc = income.get("operatingIncome") if "operatingIncome" in income.columns else None
    da = income.get("depreciationAndAmortization") if "depreciationAndAmortization" in income.columns else None
    cash_col = "cashAndCashEquivalents" if "cashAndCashEquivalents" in balance.columns else "cashAndShortTermInvestments"

    # Align on the income statement index (DatetimeIndex of fiscal period end)
    for period_end in income.index:
        if ebitda_col is not None:
            ebitda_val = float(income.at[period_end, ebitda_col]) if not pd.isna(income.at[period_end, ebitda_col]) else float("nan")
        elif op_inc is not None and da is not None:
            op = income.at[period_end, "operatingIncome"]
            dep = income.at[period_end, "depreciationAndAmortization"]
            ebitda_val = float(op) + float(dep) if not (pd.isna(op) or pd.isna(dep)) else float("nan")
        else:
            ebitda_val = float("nan")
        if math.isnan(ebitda_val) or ebitda_val <= 0:
            continue
        # Debt and cash on the matching balance sheet row if present
        if period_end in balance.index:
            total_debt = balance.at[period_end, "totalDebt"] if "totalDebt" in balance.columns else float("nan")
            cash = balance.at[period_end, cash_col] if cash_col in balance.columns else 0.0
        else:
            total_debt = float("nan")
            cash = 0.0
        if pd.isna(total_debt):
            net_debt = 0.0
        else:
            net_debt = float(total_debt) - (float(cash) if not pd.isna(cash) else 0.0)
        # Price closest to (and on or before) the fiscal period end
        ts = pd.Timestamp(period_end)
        prior = close_series[close_series.index <= ts]
        if prior.empty:
            continue
        year_end_price = float(prior.iloc[-1])
        year_end_mkt_cap = year_end_price * shares_approx
        ev = year_end_mkt_cap + net_debt
        if ev <= 0:
            continue
        rows.append({"year": ts.year, "ev_ebitda": ev / ebitda_val})
    return pd.DataFrame(rows)


def render_historical_valuation(fundamentals, close_series: pd.Series, current_multiple: float) -> None:
    """Range bar: 5Y low / median / high of EV/EBITDA with the current
    multiple marked. If there is not enough annual data, render a short
    caption and bail.
    """
    st.markdown(section_bar("HISTORICAL EV/EBITDA RANGE (5Y)", source="FMP"), unsafe_allow_html=True)
    if fundamentals is None or is_error(fundamentals):
        st.caption("DATA OFF | fundamentals unavailable for historical range")
        return
    hist = _annual_ev_ebitda(fundamentals, close_series)
    if hist.empty or len(hist) < 2:
        st.caption("DATA PARTIAL | need at least 2 annual statements for a range")
        return
    lo = float(hist["ev_ebitda"].min())
    hi = float(hist["ev_ebitda"].max())
    median = float(hist["ev_ebitda"].median())
    current = float(current_multiple) if current_multiple is not None and not (isinstance(current_multiple, float) and math.isnan(current_multiple)) else median
    if hi <= lo:
        hi = lo + 1e-6

    percentile = float(np.mean(hist["ev_ebitda"].values <= current)) * 100.0

    accent = TOKENS["accent_primary"]
    success = TOKENS["accent_success"]
    danger = TOKENS["accent_danger"]
    muted = TOKENS["text_muted"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[lo, hi], y=["EV/EBITDA"], mode="lines",
        line={"color": muted, "width": 8},
        hoverinfo="skip", name="5Y range",
    ))
    fig.add_trace(go.Scatter(
        x=[lo, median, hi], y=["EV/EBITDA"] * 3, mode="markers+text",
        marker={"color": [success, muted, danger], "size": 14, "symbol": "line-ns", "line": {"color": "#080808", "width": 1}},
        text=[f"LOW {lo:.1f}x", f"MED {median:.1f}x", f"HIGH {hi:.1f}x"],
        textposition="top center",
        textfont={"family": "JetBrains Mono, monospace", "size": 10, "color": TOKENS["text_secondary"]},
        hoverinfo="skip", name="markers",
    ))
    fig.add_trace(go.Scatter(
        x=[current], y=["EV/EBITDA"], mode="markers+text",
        marker={"color": accent, "size": 22, "symbol": "diamond",
                "line": {"color": "#080808", "width": 1}},
        text=[f"CURRENT {current:.1f}x ({percentile:.0f}%ile)"],
        textposition="bottom center",
        textfont={"family": "JetBrains Mono, monospace", "size": 11, "color": accent},
        hoverinfo="skip", name="current",
    ))
    fig.update_xaxes(title_text="EV / EBITDA")
    fig.update_yaxes(showticklabels=False)
    fig.update_layout(
        title={"text": f"Historical EV/EBITDA across {len(hist)} annual statements"},
        height=220, showlegend=False,
    )
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
    # Small table below the bar
    table = hist.copy()
    table["ev_ebitda"] = table["ev_ebitda"].apply(lambda v: f"{v:.1f}x")
    table = table.rename(columns={"year": "Year", "ev_ebitda": "EV/EBITDA"})
    st.dataframe(table, use_container_width=True, hide_index=True)
