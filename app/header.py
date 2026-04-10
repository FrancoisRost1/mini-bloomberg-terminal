"""Global header.

Rendered on every page. Surfaces the active ticker bar, watchlist
quick access, market context strip (SPY / VIX / DXY), provider label,
and the DEV MODE warning when applicable.

Uses the canonical design system helpers (``styled_kpi``,
``styled_section_label``, ``styled_divider``) so the header looks
identical to the section labels and KPIs on every page.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from style_inject import TOKENS, styled_divider, styled_kpi, styled_section_label

from terminal.managers.data_manager import SharedDataManager
from terminal.utils.error_handling import dev_mode_banner, is_error, status_pill
from terminal.utils.watchlist_io import WatchlistStore


def render(data_manager: SharedDataManager, watchlist: WatchlistStore, config: dict[str, Any]) -> None:
    """Render the global header. Call at the top of every page."""
    if data_manager.registry.is_dev_mode():
        st.markdown(dev_mode_banner(), unsafe_allow_html=True)

    col_ticker, col_watchlist, col_market = st.columns([2, 2, 4])
    _render_ticker_bar(col_ticker, data_manager)
    _render_watchlist(col_watchlist, watchlist, config)
    _render_market_strip(col_market, data_manager, config)
    styled_divider()


def _render_ticker_bar(col, data_manager: SharedDataManager) -> None:
    with col:
        styled_section_label("ACTIVE TICKER")
        active = st.session_state.get("active_ticker", "AAPL")
        ticker_input = st.text_input(
            "Active ticker",
            value=active,
            key="header_ticker",
            label_visibility="collapsed",
        )
        if ticker_input and ticker_input.upper() != active:
            st.session_state["active_ticker"] = ticker_input.upper()
        provider = data_manager.registry.equity()
        provider_label = provider.name if provider else "no provider"
        st.markdown(
            status_pill(f"PROVIDER {provider_label.upper()}", "success" if provider else "failed"),
            unsafe_allow_html=True,
        )


def _render_watchlist(col, watchlist: WatchlistStore, config: dict[str, Any]) -> None:
    with col:
        styled_section_label("WATCHLIST")
        tickers = watchlist.list_tickers()
        chosen = st.selectbox(
            "Watchlist",
            options=["select"] + tickers,
            key="header_watchlist",
            label_visibility="collapsed",
        )
        if chosen and chosen != "select":
            st.session_state["active_ticker"] = chosen
        add_col, remove_col = st.columns(2)
        active = st.session_state.get("active_ticker", "")
        with add_col:
            if st.button(f"Add {active}", key="header_watchlist_add", use_container_width=True):
                watchlist.add(active)
                st.rerun()
        with remove_col:
            if st.button(f"Drop {active}", key="header_watchlist_remove", use_container_width=True):
                watchlist.remove(active)
                st.rerun()
        cap = config["watchlist"]["max_tickers"]
        backend = watchlist.backend().upper()
        st.markdown(
            status_pill(f"{len(tickers)}/{cap} | {backend}", "success"),
            unsafe_allow_html=True,
        )


def _render_market_strip(col, data_manager: SharedDataManager, config: dict[str, Any]) -> None:
    """Header market strip.

    VIX comes from FRED ``VIXCLS`` (Yahoo style ``^VIX`` is not a valid
    equity provider symbol). SPY and DXY proxy come from the equity
    provider via ``get_prices``.
    """
    with col:
        styled_section_label("MARKET CONTEXT")
        cols = st.columns(3)
        vix_series_id = config["market"]["macro_series"]["volatility"]["vix_series"]
        with cols[0]:
            macro = data_manager.get_macro([vix_series_id])
            vix_value = float("nan") if is_error(macro) else macro.latest(vix_series_id)
            if vix_value != vix_value:
                styled_kpi("VIX", "n/a")
            else:
                styled_kpi("VIX", f"{vix_value:,.2f}")
        for c, ticker in zip(cols[1:], ["SPY", "UUP"]):
            with c:
                _render_ticker_kpi(ticker, data_manager)


def _render_ticker_kpi(ticker: str, data_manager: SharedDataManager) -> None:
    data = data_manager.get_prices(ticker, period="1mo")
    if is_error(data) or data.is_empty():
        styled_kpi(ticker, "n/a")
        return
    last = data.last_close()
    prev = float(data.prices["close"].iloc[-2]) if len(data.prices) >= 2 else last
    change_pct = (last - prev) / prev * 100 if prev else 0.0
    delta_color = TOKENS["accent_success"] if change_pct >= 0 else TOKENS["accent_danger"]
    styled_kpi(ticker, f"{last:,.2f}", delta=f"{change_pct:+.2f}%", delta_color=delta_color)
