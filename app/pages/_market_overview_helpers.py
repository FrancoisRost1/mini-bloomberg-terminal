"""Market Overview page helpers.

Thin module that owns the indices strip and rates table, and
re-exports sibling renderers (sector heatmap, regime, breadth) so
``market_overview.py`` has a single import surface.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.pages._market_breadth import render_breadth as render_breadth  # noqa: F401  re export
from app.pages._market_heatmap import render_sector_heatmap as render_sector_heatmap  # noqa: F401  re export
from app.pages._market_regime import render_regime as render_regime  # noqa: F401  re export
from terminal.utils.density import (
    colored_dataframe,
    period_returns_tape,
    section_bar,
)
from terminal.utils.error_handling import degraded_card, inline_status_line, is_error


def render_indices_strip(data_manager, config) -> None:
    """Indices dataframe with inline 60d sparklines. n/a rows are dropped."""
    st.markdown(section_bar("GLOBAL INDICES", source="yfinance"), unsafe_allow_html=True)
    rows = []
    for idx in config["market"]["indices"]:
        data = data_manager.get_index_prices(idx["ticker"], period="3mo")
        if is_error(data) or data.is_empty():
            continue
        closes = data.prices["close"]
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2]) if len(closes) >= 2 else last
        chg = (last / prev - 1) * 100 if prev else 0.0
        rows.append({
            "Index": idx["label"],
            "Last": f"{last:,.2f}",
            "Chg %": f"{chg:+.2f}%",
            "60D Trend": closes.tail(60).tolist(),
        })
    if not rows:
        st.markdown(inline_status_line("OFF", source="yfinance"), unsafe_allow_html=True)
        return
    st.dataframe(
        colored_dataframe(pd.DataFrame(rows), ["Chg %"]),
        use_container_width=True, hide_index=True,
        column_config={"60D Trend": st.column_config.LineChartColumn("60D", width="medium")},
    )


def render_rates_and_vol(data_manager, config) -> None:
    macro_cfg = config["market"]["macro_series"]
    series_ids = [r["series_id"] for r in macro_cfg["rates"]]
    macro = data_manager.get_macro(series_ids)
    if is_error(macro):
        st.markdown(section_bar("RATES AND VOLATILITY", source="FRED"), unsafe_allow_html=True)
        st.markdown(degraded_card(macro.reason, macro.provider), unsafe_allow_html=True)
        return
    rates_series = {
        r["label"]: macro.series.get(r["series_id"], pd.Series(dtype=float))
        for r in macro_cfg["rates"]
    }
    ten_y = rates_series.get("US 10Y", pd.Series(dtype=float)).dropna()
    tape = period_returns_tape(ten_y) if not ten_y.empty else ""
    st.markdown(
        section_bar("RATES AND VOLATILITY", tape=tape, source="FRED"),
        unsafe_allow_html=True,
    )
    rows = []
    for label, series in rates_series.items():
        clean = series.dropna()
        if clean.empty:
            continue
        latest = float(clean.iloc[-1])
        prior = float(clean.iloc[-2]) if len(clean) >= 2 else latest
        rows.append({
            "Tenor": label,
            "Latest": f"{latest:.2f}%",
            "1D bp": f"{(latest - prior) * 100:+.0f}",
            "60D Trend": clean.tail(60).tolist(),
        })
    if not rows:
        st.markdown(inline_status_line("OFF", source="FRED"), unsafe_allow_html=True)
        return
    st.dataframe(
        colored_dataframe(pd.DataFrame(rows), ["1D bp"]),
        use_container_width=True, hide_index=True,
        column_config={"60D Trend": st.column_config.LineChartColumn("60D", width="medium")},
    )
