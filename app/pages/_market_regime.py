"""Market Overview regime classifier pane.

Pulled out of _market_overview_helpers.py so the helpers module stays
under the 150 line budget. Wraps the rule-based regime engine (P5) and
renders the decomposition in a chart + table pair plus an observation
card. Shows raw signal values (not just integer scores) so the NEUTRAL
case does not read as if nothing is being computed.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from style_inject import TOKENS, styled_card

from terminal.adapters.regime_adapter import run_regime
from terminal.utils.chart_helpers import bar_chart, interpretation_callout_html
from terminal.utils.density import (
    colored_dataframe,
    dense_kpi_row,
    period_returns_tape,
    section_bar,
    signed_color,
)
from terminal.utils.error_handling import degraded_card, is_error


def _is_num(v: float) -> bool:
    return v == v  # nan-safe truthiness


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
    color_map = {
        "RISK_ON": TOKENS["accent_success"],
        "NEUTRAL": TOKENS["accent_warning"],
        "RISK_OFF": TOKENS["accent_danger"],
    }
    accent = color_map.get(label, TOKENS["accent_primary"])
    st.markdown(
        section_bar("REGIME CLASSIFIER", tape=period_returns_tape(spy_close), source="yfinance + FRED"),
        unsafe_allow_html=True,
    )
    sigs = regime["signals"]
    items = [
        {"label": "REGIME", "value": label, "delta": f"conf {regime['confidence']:.2f}",
         "delta_color": accent, "value_color": accent},
        {"label": "TREND", "value": f"{sigs['trend_return_pct'] * 100:+.1f}%",
         "value_color": signed_color(sigs["trend_return_pct"])},
        {"label": "VOL ANN", "value": f"{sigs['annualized_vol'] * 100:.1f}%"
         if _is_num(sigs["annualized_vol"]) else "n/a"},
        {"label": "DRAWDOWN", "value": f"{sigs['drawdown_pct'] * 100:+.1f}%",
         "value_color": signed_color(sigs["drawdown_pct"])},
        {"label": "HY SPREAD", "value": f"{sigs['hy_spread']:.2f}%"
         if _is_num(sigs["hy_spread"]) else "n/a"},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)

    # Raw signals tell the story. Integer scores collapse to zero when no
    # stress threshold is breached, which reads like the engine is broken.
    # Show the raw magnitudes vs thresholds so every signal has visible
    # weight in the decomposition chart even when the label is NEUTRAL.
    trend_cfg = config["market"]["regime"]
    raw_signals_pct: dict[str, float] = {
        "trend %": (sigs["trend_return_pct"] * 100.0) if _is_num(sigs["trend_return_pct"]) else 0.0,
        "vol vs stress %": (
            (sigs["annualized_vol"] - trend_cfg["vol_stress_threshold"]) * 100.0
            if _is_num(sigs["annualized_vol"]) else 0.0
        ),
        "drawdown %": (sigs["drawdown_pct"] * 100.0) if _is_num(sigs["drawdown_pct"]) else 0.0,
        "hy vs stress %": (
            (sigs["hy_spread"] - trend_cfg["credit_spread_threshold"])
            if _is_num(sigs["hy_spread"]) else 0.0
        ),
    }
    chart_col, table_col = st.columns([2, 3])
    with chart_col:
        st.plotly_chart(
            bar_chart(
                raw_signals_pct,
                title="Regime Signal Decomposition (raw vs stress thresholds)",
                y_unit="% deviation",
                color_by_sign=True,
            ),
            use_container_width=True,
        )
    with table_col:
        rows = [
            ("TREND",    f"{sigs['trend_return_pct'] * 100:+.2f}%" if _is_num(sigs["trend_return_pct"]) else "n/a", regime["scores"]["trend"]),
            ("VOL",      f"{sigs['annualized_vol'] * 100:.2f}%"    if _is_num(sigs["annualized_vol"])    else "n/a", regime["scores"]["vol_stress"]),
            ("DRAWDOWN", f"{sigs['drawdown_pct'] * 100:+.2f}%"     if _is_num(sigs["drawdown_pct"])      else "n/a", regime["scores"]["drawdown"]),
            ("CREDIT",   f"{sigs['hy_spread']:.2f}%"               if _is_num(sigs["hy_spread"])         else "n/a", regime["scores"]["credit"]),
        ]
        scores_df = pd.DataFrame(rows, columns=["Signal", "Raw", "Score"])
        st.dataframe(colored_dataframe(scores_df, ["Score"]), use_container_width=True, hide_index=True)
    hy_text = f"HY {sigs['hy_spread']:.2f}%" if _is_num(sigs["hy_spread"]) else "HY n/a"
    styled_card(
        interpretation_callout_html(
            observation=(
                f"Composite score {regime['scores']['composite']:+d} from "
                f"trend {sigs['trend_return_pct'] * 100:+.1f}%, "
                f"vol {sigs['annualized_vol'] * 100:.1f}%, "
                f"drawdown {sigs['drawdown_pct'] * 100:+.1f}%, {hy_text}."
            ),
            interpretation=(
                "Each signal categorises as {-1, 0, +1}; the sum maps to the regime label. "
                "NEUTRAL is the modal state when no stress threshold is breached."
            ),
            implication="Regime transitions are slower than headlines. Treat as a filter, not a timing signal.",
        ),
        accent_color=accent,
    )
