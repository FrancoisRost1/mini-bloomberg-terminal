"""Live Signals page.

MARKET > Live Signals. Today's actionable signals across regime, TSMOM,
and breadth. All data cached with 15-minute TTL.
"""

import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import TOKENS, styled_divider, styled_header  # noqa: E402
from terminal.config_loader import load_config  # noqa: E402
from terminal.managers.data_manager import SharedDataManager  # noqa: E402

from app.pages._signals_breadth import compute_breadth_signals, render_breadth_signals  # noqa: E402
from app.pages._signals_regime import compute_regime_state, render_regime_status  # noqa: E402
from app.pages._signals_tsmom import compute_tsmom_signals  # noqa: E402
from app.pages._signals_tsmom_render import render_tsmom_table  # noqa: E402


config = st.session_state.get("_config") or load_config()
data_manager = st.session_state.get("_data_manager") or SharedDataManager(config)

styled_header("LIVE SIGNALS", "TSMOM (Moskowitz, Ooi, Pedersen 2012) + regime + breadth. Refreshes every 15 min.")

with st.spinner("Loading regime classification..."):
    regime_state = compute_regime_state(config, data_manager)
render_regime_status(regime_state)

styled_divider()

col_tsmom, col_breadth = st.columns([3, 2])

with col_tsmom:
    with st.spinner("Computing TSMOM signals across 13 ETFs..."):
        tsmom_df = compute_tsmom_signals(config, data_manager)
    render_tsmom_table(tsmom_df)

with col_breadth:
    with st.spinner("Computing breadth metrics..."):
        breadth = compute_breadth_signals(config, data_manager)
    render_breadth_signals(breadth)

styled_divider()

now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
accent = TOKENS.get("accent_primary", "#FF8C00")
st.markdown(
    f'<div style="color:#555;font-family:monospace;font-size:11px;text-align:right;">Last computed: {now} | Cache TTL: 15 min | Data: yfinance (ETFs) + FRED (macro)</div>',
    unsafe_allow_html=True,
)

with st.expander("Signal methodology and limitations"):
    st.markdown(
        "**TSMOM Signal**: 12-month cumulative return, skipping the most recent month (12-1 momentum). "
        "LONG if return > 1%, SHORT if < -1%, FLAT otherwise. Based on Moskowitz, Ooi and Pedersen (2012).\n\n"
        "**Regime**: Composite classification from trend direction, volatility stress, drawdown depth, "
        "and credit conditions (HY OAS spread). Rule-based, not predictive.\n\n"
        "**Breadth**: Percentage of S&P 500 sector ETFs trading above their 200-day simple moving average.\n\n"
        "**Limitations**: Signals are computed from daily close prices (not intraday). TSMOM uses ETF proxies, "
        "not futures (no leverage cost or roll yield). FLAT threshold (1%) is configurable but not optimized. "
        "Regime classification is backward-looking, not predictive. No transaction cost or slippage reflected "
        "in signal direction. Breadth uses sector ETFs as proxy, not individual stock-level data."
    )
