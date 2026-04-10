"""Global header. Bloomberg style ticker tape strip.

Single line. The widgets row (ticker input, watchlist) is collapsed
into the leftmost columns; the rest of the row is a horizontal market
context tape with monospace, colored deltas, and pipe separators.
Provider status and watchlist count appear as inline pills inside the
tape itself, not as separate column blocks.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from style_inject import TOKENS

from terminal.managers.data_manager import SharedDataManager
from terminal.utils.density import signed_color, ticker_tape
from terminal.utils.error_handling import dev_mode_banner, is_error
from terminal.utils.watchlist_io import WatchlistStore


def render(data_manager: SharedDataManager, watchlist: WatchlistStore, config: dict[str, Any]) -> None:
    """Render the global header. Call at the top of every page."""
    if data_manager.registry.is_dev_mode():
        st.markdown(dev_mode_banner(), unsafe_allow_html=True)

    col_ticker, col_watchlist, col_actions, col_tape = st.columns([2, 2, 2, 8])
    _render_ticker_input(col_ticker)
    _render_watchlist_select(col_watchlist, watchlist)
    _render_watchlist_actions(col_actions, watchlist)
    with col_tape:
        st.markdown(_build_tape(data_manager, watchlist, config), unsafe_allow_html=True)


def _render_ticker_input(col) -> None:
    with col:
        active = st.session_state.get("active_ticker", "AAPL")
        ticker_input = st.text_input(
            "Active ticker",
            value=active,
            key="header_ticker",
            label_visibility="collapsed",
        )
        if ticker_input and ticker_input.upper() != active:
            st.session_state["active_ticker"] = ticker_input.upper()


def _render_watchlist_select(col, watchlist: WatchlistStore) -> None:
    with col:
        tickers = watchlist.list_tickers()
        chosen = st.selectbox(
            "Watchlist",
            options=["select"] + tickers,
            key="header_watchlist",
            label_visibility="collapsed",
        )
        if chosen and chosen != "select":
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


def _build_tape(data_manager: SharedDataManager, watchlist: WatchlistStore, config: dict[str, Any]) -> str:
    """Assemble the inline ticker tape items."""
    items: list[dict[str, Any]] = []

    # Provider + watchlist status
    provider = data_manager.registry.equity()
    provider_label = provider.name.upper() if provider else "NONE"
    provider_color = TOKENS["accent_success"] if provider else TOKENS["accent_danger"]
    items.append({"label": "PROVIDER", "value": provider_label, "delta_color": provider_color})
    cap = config["watchlist"]["max_tickers"]
    items.append({
        "label": "WATCHLIST",
        "value": f"{len(watchlist.list_tickers())}/{cap}",
        "delta": watchlist.backend().upper(),
        "delta_color": TOKENS["accent_info"],
    })

    # VIX from FRED
    vix_series_id = config["market"]["macro_series"]["volatility"]["vix_series"]
    macro = data_manager.get_macro([vix_series_id])
    vix_value = float("nan") if is_error(macro) else macro.latest(vix_series_id)
    items.append({
        "label": "VIX",
        "value": "n/a" if vix_value != vix_value else f"{vix_value:.2f}",
    })

    # Ticker tape: SPY, QQQ, DXY proxy, gold, oil
    for ticker, label in [("SPY", "SPY"), ("QQQ", "QQQ"), ("UUP", "DXY"), ("GLD", "GOLD"), ("USO", "OIL")]:
        items.append(_market_item(data_manager, ticker, label))

    return ticker_tape(items)


def _market_item(data_manager: SharedDataManager, ticker: str, label: str) -> dict[str, Any]:
    data = data_manager.get_prices(ticker, period="1mo")
    if is_error(data) or data.is_empty():
        return {"label": label, "value": "n/a"}
    last = data.last_close()
    prev = float(data.prices["close"].iloc[-2]) if len(data.prices) >= 2 else last
    change_pct = ((last - prev) / prev) if prev else 0.0
    return {
        "label": label,
        "value": f"{last:,.2f}",
        "delta": f"{change_pct * 100:+.2f}%",
        "delta_color": signed_color(change_pct),
    }
