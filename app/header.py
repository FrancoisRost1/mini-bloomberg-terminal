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

from app.header_sidebar_toggle import render_sidebar_toggle as _render_sidebar_toggle
from app.header_status import render_status_bar
from app.header_tape import build_tape_items
from terminal.managers.data_manager import SharedDataManager
from terminal.utils.error_handling import dev_mode_banner
from terminal.utils.marquee import build_marquee_html
from terminal.utils.last_good_cache import LastGoodCache
from terminal.utils.watchlist_io import WatchlistStore


def _cache(config: dict[str, Any]) -> LastGoodCache:
    root = Path(config["_meta"]["project_root"])
    return LastGoodCache(root / "data" / "header_last_good.json")


def render(
    data_manager: SharedDataManager,
    watchlist: WatchlistStore,
    config: dict[str, Any],
    ticker_state: dict[str, float | None] | None = None,
) -> None:
    if data_manager.registry.is_dev_mode():
        st.markdown(dev_mode_banner(), unsafe_allow_html=True)

    # Row 1: sidebar toggle + ticker input + 1D change badge +
    # watchlist controls. Toggle lives at the far left so it reads
    # like a terminal F-key row, not a nav element.
    col_toggle, col_ticker, col_change, col_watchlist, col_actions = st.columns([1, 3, 2, 3, 3])
    _render_sidebar_toggle(col_toggle)
    _render_ticker_input(col_ticker)
    _render_ticker_change(col_change, ticker_state or {})
    _render_watchlist_select(col_watchlist, watchlist)
    _render_watchlist_actions(col_actions, watchlist)

    # Row 2: custom HTML/JS scrolling marquee (CSS animation, no rerun).
    # Scroll speed scales with item count: ~4.5s per item so a 35-item
    # tape reads at a comfortable pace (~160s full sweep) while a
    # shorter tape after partial fetch failures is not dragged out.
    items = build_tape_items(data_manager, watchlist, config, _cache(config))
    scroll_seconds = max(90, int(len(items) * 4.5)) if items else 90
    components.html(build_marquee_html(items, scroll_seconds=scroll_seconds), height=36)

    # Row 3: one-line status strip. Market status, NY clock, UTC clock,
    # data freshness tag. Fills the gap between the tape and the first
    # page section so there is no dead vertical zone.
    render_status_bar(data_manager)


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


def _render_ticker_change(col, state: dict[str, float | None]) -> None:
    """Render the active ticker's last close + signed 1D change. Lives
    next to the ticker input so the active name + price + delta read
    as a single Bloomberg style line.
    """
    last = state.get("last")
    chg = state.get("chg")
    if last is None or chg is None:
        col.markdown(
            f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.78rem;'
            f'color:{TOKENS["text_muted"]};padding:0.35rem 0.4rem;">no data</div>',
            unsafe_allow_html=True,
        )
        return
    if chg > 0:
        color = TOKENS["accent_success"]
        arrow = "\u25B2"
    elif chg < 0:
        color = TOKENS["accent_danger"]
        arrow = "\u25BC"
    else:
        color = TOKENS["text_muted"]
        arrow = "\u00B7"
    col.markdown(
        f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.86rem;'
        f'font-weight:700;padding:0.32rem 0.4rem;color:{TOKENS["text_primary"]};'
        f'border:1px solid rgba(255,255,255,0.06);border-radius:3px;'
        f'background-color:{TOKENS["bg_surface"]};'
        f'display:flex;align-items:center;gap:0.5rem;justify-content:center;">'
        f'<span>{last:,.2f}</span>'
        f'<span style="color:{color};">{arrow}{abs(chg) * 100:.2f}%</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_watchlist_select(col, watchlist: WatchlistStore) -> None:
    with col:
        tickers = watchlist.list_tickers()
        chosen = st.selectbox(
            "Watchlist",
            options=["WATCHLIST"] + tickers,
            key="header_watchlist",
            label_visibility="collapsed",
        )
        # Picking a ticker from the watchlist jumps the user to Research
        # on that name, matching CLAUDE.md section 7. The previous
        # behavior only updated session_state and left the user on the
        # current page, which made the dropdown feel inert.
        if chosen and chosen != "WATCHLIST" and chosen != st.session_state.get("active_ticker"):
            st.session_state["active_ticker"] = chosen
            try:
                st.switch_page("pages/ticker_deep_dive.py")
            except Exception:
                # st.switch_page is only valid inside a navigation runtime;
                # fall back to a soft rerun on the current page.
                st.rerun()


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
