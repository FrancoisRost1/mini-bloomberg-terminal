"""Market Overview extras: yield curve mini chart.

The FX / commodities / gainers-losers KPI rows live in _market_rows.py
and are re-exported from here so existing import sites keep working.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme

from app.pages._market_rows import (  # noqa: F401  re export
    FX_PAIRS,
    COMMODITY_TICKERS,
    render_commodities_row,
    render_fx_row,
    render_gainers_losers,
)
from terminal.utils.density import section_bar
from terminal.utils.error_handling import degraded_card, is_error


# US Treasury tenors plotted as a single yield curve. DGS5 is the only
# tenor not already in config.market.macro_series.rates so it has to
# be fetched alongside the configured series.
CURVE_TENORS: list[tuple[str, str, float]] = [
    # FRED series, label, x position in years
    ("DGS2",  "2Y",  2.0),
    ("DGS5",  "5Y",  5.0),
    ("DGS10", "10Y", 10.0),
    ("DGS30", "30Y", 30.0),
]


def render_yield_curve(data_manager) -> None:
    """Mini line chart of the 2Y / 5Y / 10Y / 30Y Treasury curve."""
    st.markdown(section_bar("US TREASURY CURVE", source="FRED"), unsafe_allow_html=True)
    series_ids = [s[0] for s in CURVE_TENORS]
    macro = data_manager.get_macro(series_ids)
    if is_error(macro):
        st.markdown(degraded_card(macro.reason, macro.provider), unsafe_allow_html=True)
        return
    xs: list[float] = []
    ys: list[float] = []
    labels: list[str] = []
    for sid, lbl, x in CURVE_TENORS:
        s = macro.series.get(sid)
        if s is None:
            continue
        clean = s.dropna()
        if clean.empty:
            continue
        xs.append(x)
        ys.append(float(clean.iloc[-1]))
        labels.append(lbl)
    if not xs:
        st.markdown(degraded_card("no curve data from FRED", "fred"), unsafe_allow_html=True)
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines+markers+text",
        line={"width": 2, "color": TOKENS["accent_primary"]},
        marker={"size": 7, "color": TOKENS["accent_primary"]},
        text=[f"{y:.2f}%" for y in ys], textposition="top center",
        textfont={"family": "JetBrains Mono, monospace", "size": 10,
                  "color": TOKENS["text_primary"]},
        name="UST yield",
    ))
    fig.update_xaxes(title_text="Maturity (years)", tickmode="array", tickvals=xs, ticktext=labels)
    fig.update_yaxes(title_text="Yield (%)", ticksuffix="%")
    fig.update_layout(title={"text": "US Treasury Yield Curve. latest close"},
                      height=240, showlegend=False)
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
