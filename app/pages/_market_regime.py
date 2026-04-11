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

from app.pages._market_calendar import render_event_calendar_strip
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


def _fmt_raw_pct(value: float, signed: bool = True) -> str:
    """Format a raw signal value as a percentage string."""
    if value is None or not _is_num(value):
        return "n/a"
    if signed:
        return f"{value * 100:+.2f}%"
    return f"{value * 100:.2f}%"


def _thr_ratio(value: float, threshold: float) -> str:
    """Signal strength as a signed ratio vs its stress threshold.

    Returns the value divided by the threshold, signed. 1.00x means
    the signal is exactly at the stress threshold; below 1 means
    below stress; above 1 means the threshold is breached. For
    downside signals (drawdown below a negative threshold) the ratio
    is reported as a positive number when the signal is benign and
    > 1 when stressed so the column reads consistently.
    """
    if value is None or not _is_num(value) or threshold == 0:
        return "n/a"
    ratio = float(value) / float(threshold)
    return f"{ratio:+.2f}x"


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
    st.markdown(dense_kpi_row(items, min_cell_px=135), unsafe_allow_html=True)

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
    # Chart and table side by side (nested columns). Every cell in the
    # table expresses its signal as a ratio vs the stress threshold so
    # the column is never just a wall of 0s in the NEUTRAL regime.
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
            ("TREND",    _fmt_raw_pct(sigs["trend_return_pct"]),
             _thr_ratio(sigs["trend_return_pct"], trend_cfg["trend_score_threshold"])),
            ("VOL",      _fmt_raw_pct(sigs["annualized_vol"], signed=False),
             _thr_ratio(sigs["annualized_vol"], trend_cfg["vol_stress_threshold"])),
            ("DRAWDOWN", _fmt_raw_pct(sigs["drawdown_pct"]),
             _thr_ratio(sigs["drawdown_pct"], trend_cfg["drawdown_threshold"])),
            ("CREDIT",   _fmt_raw_pct(sigs["hy_spread"] / 100.0) if _is_num(sigs["hy_spread"]) else "n/a",
             _thr_ratio(sigs["hy_spread"], trend_cfg["credit_spread_threshold"])),
        ]
        scores_df = pd.DataFrame(rows, columns=["Signal", "Raw", "vs Thr"])
        st.dataframe(colored_dataframe(scores_df, ["vs Thr"]),
                     use_container_width=True, hide_index=True)
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

    # Fills the vertical gap between the regime callout and the
    # RATES AND VOLATILITY row. Static strip for v1; live connector
    # lands in v2.
    render_event_calendar_strip()
