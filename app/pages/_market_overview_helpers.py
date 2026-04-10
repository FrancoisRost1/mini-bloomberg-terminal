"""Market Overview page helpers."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from style_inject import TOKENS, styled_card

from terminal.adapters.regime_adapter import run_regime
from terminal.engines.breadth_engine import compute_breadth
from terminal.utils.chart_helpers import bar_chart, interpretation_callout_html, line_chart
from terminal.utils.density import (
    dense_kpi_row,
    period_returns_tape,
    section_bar,
    signed_color,
    ticker_tape,
)
from terminal.utils.error_handling import degraded_card, is_error
from terminal.utils.formatting import fmt_pct


def render_indices_strip(data_manager, config) -> None:
    indices = config["market"]["indices"]
    items: list[dict] = []
    for idx in indices:
        data = data_manager.get_prices(idx["ticker"], period="1mo")
        if is_error(data) or data.is_empty():
            items.append({"label": idx["label"], "value": "n/a"})
            continue
        last = data.last_close()
        start = float(data.prices["close"].iloc[0])
        change = (last / start - 1) if start else 0.0
        items.append({
            "label": idx["label"], "value": f"{last:,.2f}",
            "delta": f"{change * 100:+.2f}%", "delta_color": signed_color(change),
        })
    st.markdown(ticker_tape(items), unsafe_allow_html=True)


def render_rates_and_vol(data_manager, config) -> None:
    macro_cfg = config["market"]["macro_series"]
    series_ids = [r["series_id"] for r in macro_cfg["rates"]]
    macro = data_manager.get_macro(series_ids)
    if is_error(macro):
        st.markdown(section_bar("RATES AND VOLATILITY"), unsafe_allow_html=True)
        st.markdown(degraded_card(macro.reason, macro.provider), unsafe_allow_html=True)
        return
    rates_series = {r["label"]: macro.series.get(r["series_id"], pd.Series(dtype=float)) for r in macro_cfg["rates"]}
    ten_y = rates_series.get("US 10Y", pd.Series(dtype=float)).dropna()
    tape = period_returns_tape(ten_y) if not ten_y.empty else ""
    st.markdown(section_bar("RATES AND VOLATILITY", tape=tape), unsafe_allow_html=True)
    items = []
    for label, series in rates_series.items():
        clean = series.dropna()
        if clean.empty:
            items.append({"label": label, "value": "n/a"})
            continue
        latest = float(clean.iloc[-1])
        prior = float(clean.iloc[-2]) if len(clean) >= 2 else latest
        change_bps = (latest - prior) * 100
        items.append({
            "label": label, "value": f"{latest:.2f}%",
            "delta": f"{change_bps:+.0f}bp", "delta_color": signed_color(change_bps),
        })
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)
    chart_col, table_col = st.columns([2, 3])
    with table_col:
        latest_table = pd.DataFrame(
            [(label, f"{series.dropna().iloc[-1]:.2f}%" if not series.dropna().empty else "n/a")
             for label, series in rates_series.items()],
            columns=["Tenor", "Latest"],
        )
        st.dataframe(latest_table, use_container_width=True, hide_index=True)
    with chart_col:
        st.plotly_chart(line_chart(rates_series, title="US Rate Curve (FRED)", y_unit="yield (%)"), use_container_width=True)


def render_regime(data_manager, config) -> None:
    spy = data_manager.get_prices("SPY", period="2y")
    hy = data_manager.get_macro([config["market"]["macro_series"]["volatility"]["hy_spread_series"]])
    if is_error(spy):
        st.markdown(section_bar("REGIME CLASSIFIER"), unsafe_allow_html=True)
        st.markdown(degraded_card(spy.reason, spy.provider), unsafe_allow_html=True)
        return
    spy_close = spy.prices["close"] if not spy.is_empty() else pd.Series(dtype=float)
    hy_series = hy.series.get(config["market"]["macro_series"]["volatility"]["hy_spread_series"]) if not is_error(hy) else None
    regime = run_regime(spy_close, hy_series, config["market"]["regime"])
    label = regime["regime"]
    color_map = {"RISK_ON": TOKENS["accent_success"], "NEUTRAL": TOKENS["accent_warning"], "RISK_OFF": TOKENS["accent_danger"]}
    accent = color_map.get(label, TOKENS["accent_primary"])
    st.markdown(section_bar("REGIME CLASSIFIER", tape=period_returns_tape(spy_close)), unsafe_allow_html=True)
    sigs = regime["signals"]
    items = [
        {"label": "REGIME", "value": label, "delta": f"conf {regime['confidence']:.2f}", "delta_color": accent, "value_color": accent},
        {"label": "TREND", "value": f"{sigs['trend_return_pct'] * 100:+.1f}%", "value_color": signed_color(sigs["trend_return_pct"])},
        {"label": "VOL ANN", "value": f"{sigs['annualized_vol'] * 100:.1f}%" if sigs["annualized_vol"] == sigs["annualized_vol"] else "n/a"},
        {"label": "DRAWDOWN", "value": f"{sigs['drawdown_pct'] * 100:+.1f}%", "value_color": signed_color(sigs["drawdown_pct"])},
        {"label": "HY SPREAD", "value": f"{sigs['hy_spread']:.2f}%" if sigs["hy_spread"] == sigs["hy_spread"] else "n/a"},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)
    chart_col, table_col = st.columns([2, 3])
    with table_col:
        scores_df = pd.DataFrame([(k.upper(), v) for k, v in regime["scores"].items()], columns=["Signal", "Score"])
        st.dataframe(scores_df, use_container_width=True, hide_index=True)
    with chart_col:
        st.plotly_chart(
            bar_chart(regime["scores"], title="Regime Signal Decomposition", y_unit="score", color_by_sign=True),
            use_container_width=True,
        )
    styled_card(
        interpretation_callout_html(
            observation=f"Composite score {regime['scores']['composite']:+d} across trend, vol, drawdown, and credit.",
            interpretation="Each signal scored in {-1, 0, +1}; sum maps to the regime label.",
            implication="Regime transitions are slower than headlines. Treat as a filter, not a timing signal.",
        ),
        accent_color=accent,
    )


def render_breadth(data_manager, config) -> None:
    universe = config["market"]["breadth"]["universe"]
    closes: dict[str, pd.Series] = {}
    for ticker in universe:
        data = data_manager.get_prices(ticker, period="1y")
        if is_error(data) or data.is_empty():
            continue
        closes[ticker] = data.prices["close"]
    st.markdown(section_bar("MARKET BREADTH"), unsafe_allow_html=True)
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
        {"label": "ADV / DECL", "value": f"{ad:.2f}" if ad == ad else "n/a", "value_color": signed_color((ad or 0) - 1.0) if ad == ad else None},
        {"label": "NEW HIGHS", "value": str(nhl["new_highs"]), "value_color": TOKENS["accent_success"]},
        {"label": "NEW LOWS", "value": str(nhl["new_lows"]), "value_color": TOKENS["accent_danger"]},
        {"label": "NET HIGH LOW", "value": f"{nhl['net']:+d}", "value_color": signed_color(nhl["net"])},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)
