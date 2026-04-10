"""MARKET. Market Overview workspace. Renders indices, rates, regime, breadth."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from style_inject import (  # noqa: E402
    TOKENS,
    styled_card,
    styled_divider,
    styled_header,
    styled_kpi,
    styled_section_label,
)

from terminal.adapters.regime_adapter import run_regime  # noqa: E402
from terminal.engines.breadth_engine import compute_breadth  # noqa: E402
from terminal.utils.chart_helpers import bar_chart, interpretation_callout_html, line_chart  # noqa: E402
from terminal.utils.error_handling import degraded_card, is_error  # noqa: E402
from terminal.utils.formatting import fmt_pct  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]

    styled_header("Market Overview", "Cross asset regime context")

    _render_indices_strip(data_manager, config)
    styled_divider()
    styled_section_label("RATES AND VOLATILITY")
    _render_rates_and_vol(data_manager, config)
    styled_divider()
    styled_section_label("REGIME CLASSIFIER")
    _render_regime(data_manager, config)
    styled_divider()
    styled_section_label("MARKET BREADTH")
    _render_breadth(data_manager, config)


def _render_indices_strip(data_manager, config) -> None:
    indices = config["market"]["indices"]
    cols = st.columns(len(indices))
    for col, idx in zip(cols, indices):
        with col:
            data = data_manager.get_prices(idx["ticker"], period="1mo")
            if is_error(data) or data.is_empty():
                styled_kpi(idx["label"], "n/a")
                continue
            last = data.last_close()
            start = float(data.prices["close"].iloc[0])
            change = (last / start - 1) if start else 0.0
            color = TOKENS["accent_success"] if change >= 0 else TOKENS["accent_danger"]
            styled_kpi(
                idx["label"],
                f"{last:,.2f}",
                delta=f"{change * 100:+.2f}%",
                delta_color=color,
            )


def _render_rates_and_vol(data_manager, config) -> None:
    macro_cfg = config["market"]["macro_series"]
    series_ids = [r["series_id"] for r in macro_cfg["rates"]]
    macro = data_manager.get_macro(series_ids)
    if is_error(macro):
        st.markdown(degraded_card(macro.reason, macro.provider), unsafe_allow_html=True)
        return
    rates_series = {r["label"]: macro.series.get(r["series_id"], pd.Series(dtype=float)) for r in macro_cfg["rates"]}
    fig = line_chart(rates_series, title="US Rate Curve (FRED)", y_unit="yield (%)")
    st.plotly_chart(fig, use_container_width=True)
    ten_y = rates_series.get("US 10Y", pd.Series(dtype=float)).dropna()
    latest_10y = float(ten_y.iloc[-1]) if not ten_y.empty else float("nan")
    styled_card(
        interpretation_callout_html(
            observation=f"Latest 10Y yield {fmt_pct(latest_10y / 100)}.",
            interpretation="Curve shape signals the market growth and inflation outlook.",
            implication="Inverted curves have historically preceded recessions with long and variable lags.",
        ),
        accent_color=TOKENS["accent_primary"],
    )


def _render_regime(data_manager, config) -> None:
    spy = data_manager.get_prices("SPY", period="2y")
    hy = data_manager.get_macro([config["market"]["macro_series"]["volatility"]["hy_spread_series"]])
    if is_error(spy):
        st.markdown(degraded_card(spy.reason, spy.provider), unsafe_allow_html=True)
        return
    spy_close = spy.prices["close"] if not spy.is_empty() else pd.Series(dtype=float)
    hy_series = hy.series.get(config["market"]["macro_series"]["volatility"]["hy_spread_series"]) if not is_error(hy) else None
    regime = run_regime(spy_close, hy_series, config["market"]["regime"])
    label = regime["regime"]
    color_map = {"RISK_ON": TOKENS["accent_success"], "NEUTRAL": TOKENS["accent_warning"], "RISK_OFF": TOKENS["accent_danger"]}
    accent = color_map.get(label, TOKENS["accent_primary"])
    styled_kpi("Composite Regime", label, delta=f"confidence {regime['confidence']:.2f}", delta_color=accent)
    st.plotly_chart(
        bar_chart(regime["scores"], title="Regime Signal Decomposition", y_unit="score", color_by_sign=True),
        use_container_width=True,
    )
    styled_card(
        interpretation_callout_html(
            observation=f"Composite score {regime['scores']['composite']:+d} across trend, vol, drawdown, and credit.",
            interpretation="Each signal is scored in {-1, 0, +1}; the sum maps to the regime label.",
            implication="Regime transitions are slower than headlines. Treat as a filter, not a timing signal.",
        ),
        accent_color=accent,
    )


def _render_breadth(data_manager, config) -> None:
    universe = config["market"]["breadth"]["universe"]
    closes: dict[str, pd.Series] = {}
    for ticker in universe:
        data = data_manager.get_prices(ticker, period="1y")
        if is_error(data) or data.is_empty():
            continue
        closes[ticker] = data.prices["close"]
    if not closes:
        st.markdown(degraded_card("no breadth universe data", "registry"), unsafe_allow_html=True)
        return
    df = pd.DataFrame(closes).dropna(how="all")
    breadth = compute_breadth(df, config["market"]["breadth"])
    cols = st.columns(3)
    with cols[0]:
        styled_kpi("% Above 200d MA", fmt_pct(breadth["pct_above_ma"]))
    with cols[1]:
        ad = breadth["adv_decl_ratio"]
        styled_kpi("Advance Decline", f"{ad:.2f}" if ad == ad else "n/a")
    with cols[2]:
        nhl = breadth["new_highs_lows"]
        styled_kpi("Net New Highs", f"{nhl['net']:+d}")


render()
