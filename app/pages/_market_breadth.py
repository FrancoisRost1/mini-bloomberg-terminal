"""Market Overview breadth pane.

Split out of _market_overview_helpers.py so the helpers module stays
under the 150 line budget after the multi-timeframe columns and the
tz-aware YTD handling. Renders:

- breadth KPI strip (% above 200D, adv/decl, new highs/lows, net)
- sector ETF table with 1D / 1W / 1M / YTD / 1Y columns and a 60D
  sparkline
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from style_inject import TOKENS

from terminal.engines.breadth_engine import compute_breadth
from terminal.utils.density import (
    colored_dataframe,
    dense_kpi_row,
    section_bar,
    signed_color,
)
from terminal.utils.error_handling import degraded_card, is_error
from terminal.utils.formatting import fmt_pct


def _pct_change_bars(series: pd.Series, bars: int) -> float:
    """Percent change over the last ``bars`` trading days, nan if too short."""
    if series is None or len(series) <= bars:
        return float("nan")
    last = float(series.iloc[-1])
    prior = float(series.iloc[-1 - bars])
    if prior == 0:
        return float("nan")
    return (last / prior - 1.0) * 100.0


def _ytd_pct(series: pd.Series) -> float:
    """Year-to-date percent return from the last observation before Jan 1.

    yfinance sometimes returns a tz-aware DatetimeIndex
    (America/New_York). Comparing such an index against a naive
    pd.Timestamp raises ``Cannot compare tz-naive and tz-aware
    datetime-like objects``. We normalize by stripping tz on a local
    copy before slicing.
    """
    if series is None or series.empty:
        return float("nan")
    try:
        idx = pd.DatetimeIndex(series.index)
    except (TypeError, ValueError):
        return float("nan")
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    local = series.copy()
    local.index = idx
    try:
        year = int(idx[-1].year)
    except (AttributeError, IndexError):
        return float("nan")
    jan1 = pd.Timestamp(f"{year}-01-01")
    prior_segment = local[local.index < jan1]
    if prior_segment.empty:
        start = float(local.iloc[0])
    else:
        start = float(prior_segment.iloc[-1])
    if start == 0:
        return float("nan")
    return (float(local.iloc[-1]) / start - 1.0) * 100.0


def _fmt_signed_pct(value: float) -> str:
    if value != value:  # nan
        return "n/a"
    return f"{value:+.2f}%"


def render_breadth(data_manager, config) -> None:
    universe = config["market"]["breadth"]["universe"]
    closes: dict[str, pd.Series] = {}
    for ticker in universe:
        data = data_manager.get_index_prices(ticker, period="1y")
        if is_error(data) or data.is_empty():
            continue
        closes[ticker] = data.prices["close"]
    st.markdown(section_bar("MARKET BREADTH", source="yfinance"), unsafe_allow_html=True)
    if not closes:
        st.markdown(degraded_card("no breadth universe data", "registry"), unsafe_allow_html=True)
        return
    df = pd.DataFrame(closes).dropna(how="all")
    breadth = compute_breadth(df, config["market"]["breadth"])
    pct = breadth["pct_above_ma"]
    ad = breadth["adv_decl_ratio"]
    nhl = breadth["new_highs_lows"]
    items = [
        {"label": "% ABOVE 200D", "value": fmt_pct(pct),
         "value_color": signed_color((pct or 0) - 0.5) if pct == pct else None},
        {"label": "ADV / DECL", "value": f"{ad:.2f}" if ad == ad else "n/a"},
        {"label": "NEW HIGHS", "value": str(nhl["new_highs"]),
         "value_color": TOKENS["accent_success"]},
        {"label": "NEW LOWS", "value": str(nhl["new_lows"]),
         "value_color": TOKENS["accent_danger"]},
        {"label": "NET HL", "value": f"{nhl['net']:+d}",
         "value_color": signed_color(nhl["net"])},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=135), unsafe_allow_html=True)
    rows = [
        {
            "Sector":   t,
            "Last":     f"{float(s.iloc[-1]):,.2f}",
            "1D %":     _fmt_signed_pct(_pct_change_bars(s, 1)),
            "1W %":     _fmt_signed_pct(_pct_change_bars(s, 5)),
            "1M %":     _fmt_signed_pct(_pct_change_bars(s, 21)),
            "YTD %":    _fmt_signed_pct(_ytd_pct(s)),
            "1Y %":     _fmt_signed_pct(_pct_change_bars(s, min(252, len(s) - 1))),
            "60D Trend": s.tail(60).tolist(),
        }
        for t, s in closes.items()
    ]
    color_cols = ["1D %", "1W %", "1M %", "YTD %", "1Y %"]
    st.dataframe(
        colored_dataframe(pd.DataFrame(rows), color_cols),
        use_container_width=True,
        hide_index=True,
        column_config={"60D Trend": st.column_config.LineChartColumn("60D", width="small")},
    )
