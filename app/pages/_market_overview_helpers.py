"""Market Overview page helpers."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from style_inject import TOKENS, styled_card

from terminal.adapters.regime_adapter import run_regime
from terminal.engines.breadth_engine import compute_breadth
from terminal.utils.chart_helpers import bar_chart, interpretation_callout_html
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


def render_regime(data_manager, config) -> None:
    spy = data_manager.get_index_prices("SPY", period="2y")
    hy_id = config["market"]["macro_series"]["volatility"]["hy_spread_series"]
    hy = data_manager.get_macro([hy_id])
    if is_error(spy):
        st.markdown(section_bar("REGIME CLASSIFIER", source="yfinance + FRED"), unsafe_allow_html=True)
        st.markdown(degraded_card(spy.reason, spy.provider), unsafe_allow_html=True)
        return
    spy_close = spy.prices["close"] if not spy.is_empty() else pd.Series(dtype=float)
    hy_series = hy.series.get(hy_id) if not is_error(hy) else None
    regime = run_regime(spy_close, hy_series, config["market"]["regime"])
    label = regime["regime"]
    color_map = {"RISK_ON": TOKENS["accent_success"], "NEUTRAL": TOKENS["accent_warning"], "RISK_OFF": TOKENS["accent_danger"]}
    accent = color_map.get(label, TOKENS["accent_primary"])
    st.markdown(section_bar("REGIME CLASSIFIER", tape=period_returns_tape(spy_close), source="yfinance + FRED"), unsafe_allow_html=True)
    sigs = regime["signals"]
    nan_check = lambda v: v == v
    items = [
        {"label": "REGIME", "value": label, "delta": f"conf {regime['confidence']:.2f}", "delta_color": accent, "value_color": accent},
        {"label": "TREND", "value": f"{sigs['trend_return_pct'] * 100:+.1f}%", "value_color": signed_color(sigs["trend_return_pct"])},
        {"label": "VOL ANN", "value": f"{sigs['annualized_vol'] * 100:.1f}%" if nan_check(sigs["annualized_vol"]) else "n/a"},
        {"label": "DRAWDOWN", "value": f"{sigs['drawdown_pct'] * 100:+.1f}%", "value_color": signed_color(sigs["drawdown_pct"])},
        {"label": "HY SPREAD", "value": f"{sigs['hy_spread']:.2f}%" if nan_check(sigs["hy_spread"]) else "n/a"},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)
    chart_col, table_col = st.columns([2, 3])
    with chart_col:
        st.plotly_chart(bar_chart(regime["scores"], title="Regime Signal Decomposition", y_unit="score", color_by_sign=True), use_container_width=True)
    with table_col:
        scores_df = pd.DataFrame([(k.upper(), v) for k, v in regime["scores"].items()], columns=["Signal", "Score"])
        st.dataframe(colored_dataframe(scores_df, ["Score"]), use_container_width=True, hide_index=True)
    styled_card(
        interpretation_callout_html(
            observation=f"Composite score {regime['scores']['composite']:+d}.",
            interpretation="Each signal scored in {-1, 0, +1}; sum maps to the regime label.",
            implication="Regime transitions are slower than headlines. Treat as a filter, not a timing signal.",
        ),
        accent_color=accent,
    )


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
    rows = [{"Sector": t, "Last": f"{float(s.iloc[-1]):,.2f}",
             "1Y %": f"{(float(s.iloc[-1]) / float(s.iloc[0]) - 1) * 100:+.1f}%" if float(s.iloc[0]) else "0.0%",
             "60D Trend": s.tail(60).tolist()} for t, s in closes.items()]
    st.dataframe(colored_dataframe(pd.DataFrame(rows), ["1Y %"]),
                 use_container_width=True, hide_index=True,
                 column_config={"60D Trend": st.column_config.LineChartColumn("60D", width="small")})
