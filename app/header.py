"""Global header.

Rendered on every page. Surfaces: active ticker bar, watchlist quick
access, live market context (SPY/VIX/DXY last), DEV MODE indicator,
and the data provider label.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from terminal.managers.data_manager import SharedDataManager
from terminal.utils.error_handling import dev_mode_banner, is_error
from terminal.utils.formatting import badge, styled_kpi
from terminal.utils.watchlist_io import WatchlistStore


def render(data_manager: SharedDataManager, watchlist: WatchlistStore, config: dict[str, Any]) -> None:
    """Render the global header. Call at the top of every page."""
    if data_manager.registry.is_dev_mode():
        st.markdown(dev_mode_banner(), unsafe_allow_html=True)

    col_ticker, col_watchlist, col_market = st.columns([2, 2, 4])

    with col_ticker:
        active = st.session_state.get("active_ticker", "AAPL")
        ticker_input = st.text_input("Active ticker", value=active, key="header_ticker", label_visibility="collapsed")
        if ticker_input and ticker_input.upper() != active:
            st.session_state["active_ticker"] = ticker_input.upper()
        provider = data_manager.registry.equity()
        provider_label = provider.name if provider else "no provider"
        st.markdown(badge(f"PROVIDER: {provider_label.upper()}", "#00B0FF"), unsafe_allow_html=True)

    with col_watchlist:
        tickers = watchlist.list_tickers()
        chosen = st.selectbox(
            "Watchlist",
            options=["-- watchlist --"] + tickers,
            key="header_watchlist",
            label_visibility="collapsed",
        )
        if chosen and chosen != "-- watchlist --":
            st.session_state["active_ticker"] = chosen
        add_col, remove_col = st.columns(2)
        active = st.session_state.get("active_ticker", "")
        with add_col:
            if st.button(f"+ Add {active}", key="header_watchlist_add", use_container_width=True):
                watchlist.add(active)
                st.rerun()
        with remove_col:
            if st.button(f"- Drop {active}", key="header_watchlist_remove", use_container_width=True):
                watchlist.remove(active)
                st.rerun()
        st.markdown(
            badge(f"WATCHLIST: {len(tickers)}/{config['watchlist']['max_tickers']}  [{watchlist.backend().upper()}]", "#FF8C00"),
            unsafe_allow_html=True,
        )

    with col_market:
        _render_market_strip(data_manager, config)

    st.markdown("---")


def _render_market_strip(data_manager: SharedDataManager, config: dict[str, Any]) -> None:
    tickers = [config["market"]["macro_series"]["volatility"]["vix_ticker"], "SPY", "UUP"]
    cols = st.columns(3)
    for col, ticker in zip(cols, tickers):
        with col:
            data = data_manager.get_prices(ticker, period="1mo")
            if is_error(data) or data.is_empty():
                st.markdown(styled_kpi(ticker, "n/a"), unsafe_allow_html=True)
                continue
            last = data.last_close()
            prev = float(data.prices["close"].iloc[-2]) if len(data.prices) >= 2 else last
            change_pct = (last - prev) / prev * 100 if prev else 0.0
            st.markdown(styled_kpi(ticker, f"{last:,.2f}  ({change_pct:+.2f}%)"), unsafe_allow_html=True)
