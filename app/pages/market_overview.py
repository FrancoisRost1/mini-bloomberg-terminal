"""MARKET: Market Overview workspace.

Answers: what regime are we in? Renders global indices, rates, vol,
cross-asset strip, the rule-based regime classifier, and breadth.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap project root for the streamlit-as-script load path.
# See app/app.py docstring for the rationale.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from terminal.adapters.regime_adapter import run_regime  # noqa: E402
from terminal.engines.breadth_engine import compute_breadth  # noqa: E402
from terminal.utils.chart_helpers import bar_chart, interpretation_callout, line_chart  # noqa: E402
from terminal.utils.error_handling import degraded_card, is_error  # noqa: E402
from terminal.utils.formatting import fmt_pct, styled_kpi  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]

    st.title("Market Overview")
    st.caption("What regime are we in?")

    _render_indices_strip(data_manager, config)
    st.markdown("### Rates and Volatility")
    _render_rates_and_vol(data_manager, config)
    st.markdown("### Regime Classifier")
    _render_regime(data_manager, config)
    st.markdown("### Market Breadth")
    _render_breadth(data_manager, config)


def _render_indices_strip(data_manager, config) -> None:
    indices = config["market"]["indices"]
    cols = st.columns(len(indices))
    for col, idx in zip(cols, indices):
        with col:
            data = data_manager.get_prices(idx["ticker"], period="1mo")
            if is_error(data) or data.is_empty():
                st.markdown(styled_kpi(idx["label"], "n/a"), unsafe_allow_html=True)
                continue
            last = data.last_close()
            start = float(data.prices["close"].iloc[0])
            change = (last / start - 1) if start else 0.0
            st.markdown(styled_kpi(idx["label"], f"{last:,.2f}  ({change * 100:+.2f}%)"), unsafe_allow_html=True)


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
    st.markdown(
        interpretation_callout(
            observation=f"Latest 10Y at {fmt_pct((rates_series['US 10Y'].dropna().iloc[-1] / 100) if not rates_series['US 10Y'].dropna().empty else float('nan'))}",
            interpretation="Curve shape signals the market's growth and inflation outlook.",
            implication="Inverted curves have historically preceded recessions with long and variable lags.",
        ),
        unsafe_allow_html=True,
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
    color_map = {"RISK_ON": "#00C853", "NEUTRAL": "#FFAB00", "RISK_OFF": "#FF3D57"}
    st.markdown(styled_kpi("Composite Regime", f"{label}  (confidence {regime['confidence']:.2f})", color_map.get(label, "#FF8C00")), unsafe_allow_html=True)
    st.plotly_chart(
        bar_chart(regime["scores"], title="Regime Signal Decomposition", y_unit="signal score", color_by_sign=True),
        use_container_width=True,
    )
    st.markdown(
        interpretation_callout(
            observation=f"Composite score {regime['scores']['composite']:+d} across trend, vol, drawdown, and credit.",
            interpretation="Each signal is scored in {-1, 0, +1}; the sum maps to the regime label.",
            implication="Regime transitions are slower than headlines -- treat this as a filter, not a timing signal.",
        ),
        unsafe_allow_html=True,
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
        st.markdown(styled_kpi("% above 200d MA", fmt_pct(breadth["pct_above_ma"])), unsafe_allow_html=True)
    with cols[1]:
        ad = breadth["adv_decl_ratio"]
        st.markdown(styled_kpi("Advance/Decline", f"{ad:.2f}" if ad == ad else "n/a"), unsafe_allow_html=True)
    with cols[2]:
        nhl = breadth["new_highs_lows"]
        st.markdown(styled_kpi("Net New Highs", f"{nhl['net']:+d}"), unsafe_allow_html=True)


render()
