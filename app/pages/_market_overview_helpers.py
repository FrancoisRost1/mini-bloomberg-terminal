"""Market Overview page helpers."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from style_inject import TOKENS

from app.pages._market_heatmap import render_sector_heatmap as render_sector_heatmap  # noqa: F401  re export
from app.pages._market_regime import render_regime as render_regime  # noqa: F401  re export
from terminal.engines.breadth_engine import compute_breadth
from terminal.utils.density import (
    colored_dataframe,
    dense_kpi_row,
    period_returns_tape,
    section_bar,
    signed_color,
)
from terminal.utils.error_handling import degraded_card, is_error
from terminal.utils.formatting import fmt_pct


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
        rows.append({"Index": idx["label"], "Last": f"{last:,.2f}",
                     "Chg %": f"{chg:+.2f}%", "60D Trend": closes.tail(60).tolist()})
    if not rows:
        from terminal.utils.error_handling import inline_status_line
        st.markdown(inline_status_line("OFF", source="yfinance"), unsafe_allow_html=True)
        return
    st.dataframe(colored_dataframe(pd.DataFrame(rows), ["Chg %"]),
                 use_container_width=True, hide_index=True,
                 column_config={"60D Trend": st.column_config.LineChartColumn("60D", width="medium")})


def render_rates_and_vol(data_manager, config) -> None:
    macro_cfg = config["market"]["macro_series"]
    series_ids = [r["series_id"] for r in macro_cfg["rates"]]
    macro = data_manager.get_macro(series_ids)
    if is_error(macro):
        st.markdown(section_bar("RATES AND VOLATILITY", source="FRED"), unsafe_allow_html=True)
        st.markdown(degraded_card(macro.reason, macro.provider), unsafe_allow_html=True)
        return
    rates_series = {r["label"]: macro.series.get(r["series_id"], pd.Series(dtype=float)) for r in macro_cfg["rates"]}
    ten_y = rates_series.get("US 10Y", pd.Series(dtype=float)).dropna()
    tape = period_returns_tape(ten_y) if not ten_y.empty else ""
    st.markdown(section_bar("RATES AND VOLATILITY", tape=tape, source="FRED"), unsafe_allow_html=True)
    rows = []
    for label, series in rates_series.items():
        clean = series.dropna()
        if clean.empty:
            continue
        latest = float(clean.iloc[-1])
        prior = float(clean.iloc[-2]) if len(clean) >= 2 else latest
        rows.append({"Tenor": label, "Latest": f"{latest:.2f}%",
                     "1D bp": f"{(latest - prior) * 100:+.0f}",
                     "60D Trend": clean.tail(60).tolist()})
    if not rows:
        from terminal.utils.error_handling import inline_status_line
        st.markdown(inline_status_line("OFF", source="FRED"), unsafe_allow_html=True)
        return
    st.dataframe(colored_dataframe(pd.DataFrame(rows), ["1D bp"]),
                 use_container_width=True, hide_index=True,
                 column_config={"60D Trend": st.column_config.LineChartColumn("60D", width="medium")})


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
        {"label": "% ABOVE 200D", "value": fmt_pct(pct), "value_color": signed_color((pct or 0) - 0.5) if pct == pct else None},
        {"label": "ADV / DECL", "value": f"{ad:.2f}" if ad == ad else "n/a"},
        {"label": "NEW HIGHS", "value": str(nhl["new_highs"]), "value_color": TOKENS["accent_success"]},
        {"label": "NEW LOWS", "value": str(nhl["new_lows"]), "value_color": TOKENS["accent_danger"]},
        {"label": "NET HL", "value": f"{nhl['net']:+d}", "value_color": signed_color(nhl["net"])},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)
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
