"""Market Overview extras: yield curve mini chart + FX row.

Pulled out of _market_overview_helpers.py so the helpers module
stays under the line budget. Both renderers are tolerant of missing
provider data and degrade to inline status lines.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme

from terminal.utils.density import dense_kpi_row, section_bar, signed_color
from terminal.utils.error_handling import degraded_card, is_error


# US Treasury tenors plotted as a single yield curve. DGS5 is the only
# tenor not already in config.market.macro_series.rates so it has to be
# fetched alongside the configured series.
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


# yfinance FX symbols. Inverted USDJPY so all three pairs read in
# the natural finance convention (price of base in quote).
FX_PAIRS: list[tuple[str, str]] = [
    ("EURUSD", "EURUSD=X"),
    ("GBPUSD", "GBPUSD=X"),
    ("USDJPY", "JPY=X"),
]


def render_gainers_losers(data_manager, config) -> None:
    """Top 3 gainers and losers from the sector ETF universe by 1D return.

    Reuses ``config.market.breadth.universe`` so the source list stays
    config driven and the same 11 ETFs that drive the heatmap drive
    this row.
    """
    from terminal.utils.density import dense_kpi_row, signed_color
    from terminal.utils.error_handling import is_error
    from terminal.utils.density import section_bar as _bar  # noqa: F811  local alias

    universe = config["market"]["breadth"]["universe"]
    rows: list[tuple[str, float, float]] = []
    for ticker in universe:
        data = data_manager.get_index_prices(ticker, period="1mo")
        if is_error(data) or data.is_empty() or len(data.prices) < 2:
            continue
        closes = data.prices["close"]
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])
        if prev == 0:
            continue
        rows.append((ticker, last, (last / prev) - 1.0))
    rows.sort(key=lambda r: r[2], reverse=True)
    gainers = rows[:3]
    losers = list(reversed(rows[-3:])) if len(rows) >= 3 else []

    st.markdown(_bar("TOP MOVERS (SECTOR ETF, 1D)", source="yfinance"), unsafe_allow_html=True)
    items: list[dict] = []
    for tkr, px, chg in gainers:
        items.append({
            "label": f"GAIN {tkr}", "value": f"{px:,.2f}",
            "delta": f"+{chg * 100:.2f}%", "delta_color": signed_color(chg),
            "value_color": signed_color(chg),
        })
    for tkr, px, chg in losers:
        items.append({
            "label": f"LOSS {tkr}", "value": f"{px:,.2f}",
            "delta": f"{chg * 100:+.2f}%", "delta_color": signed_color(chg),
            "value_color": signed_color(chg),
        })
    if not items:
        st.caption("DATA OFF | no sector ETF data available")
        return
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)


def render_fx_row(data_manager) -> None:
    """KPI row for the three majors with 1D move."""
    st.markdown(section_bar("FX MAJORS", source="yfinance"), unsafe_allow_html=True)
    items: list[dict] = []
    for label, ticker in FX_PAIRS:
        data = data_manager.get_index_prices(ticker, period="1mo")
        if is_error(data) or data.is_empty() or len(data.prices) < 2:
            items.append({"label": label, "value": "n/a"})
            continue
        closes = data.prices["close"]
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])
        chg = (last / prev - 1.0) if prev else 0.0
        items.append({
            "label": label,
            "value": f"{last:,.4f}",
            "delta": f"{chg * 100:+.2f}%",
            "delta_color": signed_color(chg),
            "value_color": signed_color(chg),
        })
    st.markdown(dense_kpi_row(items, min_cell_px=130), unsafe_allow_html=True)
