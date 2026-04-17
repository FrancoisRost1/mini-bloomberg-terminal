"""PORTFOLIO. Portfolio Builder workspace.

Orchestrator only. The progressive render pipeline (skeleton shell,
data fetch, optimizer, per slot hydration) lives in
``_portfolio_progressive.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import styled_header  # noqa: E402

from app.pages._portfolio_progressive import render_progressive  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    styled_header("Portfolio Builder", "MV and HRP | Concentration | Risk decomposition")
    st.sidebar.markdown("### Portfolio")
    st.sidebar.caption("MV and HRP optimizers with Ledoit Wolf covariance. Backtest is no-rebalance, no-TC.")

    tickers = _ticker_input()
    min_assets = int(config["portfolio"]["optimizer"]["min_assets"])
    if len(tickers) < min_assets:
        st.info(f"Enter at least {min_assets} tickers to build a portfolio.")
        return
    render_progressive(data_manager, config, tickers)


def _ticker_input() -> list[str]:
    watchlist = st.session_state.get("_watchlist")
    existing = watchlist.list_tickers() if watchlist is not None else []
    default = ", ".join(existing) if existing else "SPY, QQQ, TLT, GLD, EFA"
    raw = st.text_input("Tickers (comma separated)", value=default)
    return [t.strip().upper() for t in raw.split(",") if t.strip()]


render()
