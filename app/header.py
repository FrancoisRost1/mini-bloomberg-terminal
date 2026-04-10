"""Global header. 2 row Bloomberg layout.

Row 1: ticker input + watchlist controls (input, dropdown, +/- buttons).
Row 2: full width Bloomberg style ticker tape with provider status,
       watchlist count, VIX (FRED), and 8 market tickers from yfinance
       with arrows and colored % change.

The tape never shows raw n/a once any prior fetch has succeeded.
Failed fetches fall through to the LastGoodCache and render with a
STALE marker so the header always reads as a live tape.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from style_inject import TOKENS  # noqa: F401  used by other helpers

from app.header_tape import build_tape_items
from terminal.managers.data_manager import SharedDataManager
from terminal.utils.error_handling import dev_mode_banner
from terminal.utils.marquee import build_marquee_html
from terminal.utils.last_good_cache import LastGoodCache
from terminal.utils.watchlist_io import WatchlistStore


def _cache(config: dict[str, Any]) -> LastGoodCache:
    root = Path(config["_meta"]["project_root"])
    return LastGoodCache(root / "data" / "header_last_good.json")


def render(data_manager: SharedDataManager, watchlist: WatchlistStore, config: dict[str, Any]) -> None:
    if data_manager.registry.is_dev_mode():
        st.markdown(dev_mode_banner(), unsafe_allow_html=True)

    # Row 1: ticker input + watchlist controls
    col_ticker, col_watchlist, col_actions = st.columns([3, 3, 3])
    _render_ticker_input(col_ticker)
    _render_watchlist_select(col_watchlist, watchlist)
    _render_watchlist_actions(col_actions, watchlist)

    # Row 2: custom HTML/JS scrolling marquee (CSS animation, no rerun).
    items = build_tape_items(data_manager, watchlist, config, _cache(config))
    components.html(build_marquee_html(items), height=36)


def _render_ticker_input(col) -> None:
    with col:
        active = st.session_state.get("active_ticker", "AAPL")
        ticker_input = st.text_input(
            "Active ticker",
            value=active,
            key="header_ticker",
            label_visibility="collapsed",
            placeholder="ACTIVE TICKER",
        )
        if ticker_input and ticker_input.upper() != active:
            st.session_state["active_ticker"] = ticker_input.upper()


def _render_watchlist_select(col, watchlist: WatchlistStore) -> None:
    with col:
        tickers = watchlist.list_tickers()
        chosen = st.selectbox(
            "Watchlist",
            options=["WATCHLIST"] + tickers,
            key="header_watchlist",
            label_visibility="collapsed",
        )
        if chosen and chosen != "WATCHLIST":
            st.session_state["active_ticker"] = chosen


def _render_watchlist_actions(col, watchlist: WatchlistStore) -> None:
    with col:
        active = st.session_state.get("active_ticker", "")
        a, b = st.columns(2)
        with a:
            if st.button(f"+ {active}", key="header_watchlist_add", use_container_width=True):
                watchlist.add(active)
                st.rerun()
        with b:
            if st.button(f"- {active}", key="header_watchlist_remove", use_container_width=True):
                watchlist.remove(active)
                st.rerun()
