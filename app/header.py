"""Global header. Bloomberg style ticker tape strip.

Single line. Never shows n/a. If FMP fails on a refresh, the header
serves the last good value from disk and marks it STALE inline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from style_inject import TOKENS

from terminal.managers.data_manager import SharedDataManager
from terminal.utils.density import signed_color, ticker_tape
from terminal.utils.error_handling import dev_mode_banner, is_error
from terminal.utils.last_good_cache import LastGoodCache
from terminal.utils.watchlist_io import WatchlistStore


def _cache(config: dict[str, Any]) -> LastGoodCache:
    root = Path(config["_meta"]["project_root"])
    return LastGoodCache(root / "data" / "header_last_good.json")


def render(data_manager: SharedDataManager, watchlist: WatchlistStore, config: dict[str, Any]) -> None:
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
        ticker_input = st.text_input("Active ticker", value=active, key="header_ticker", label_visibility="collapsed")
        if ticker_input and ticker_input.upper() != active:
            st.session_state["active_ticker"] = ticker_input.upper()


def _render_watchlist_select(col, watchlist: WatchlistStore) -> None:
    with col:
        tickers = watchlist.list_tickers()
        chosen = st.selectbox("Watchlist", options=["select"] + tickers, key="header_watchlist", label_visibility="collapsed")
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
    cache = _cache(config)
    items: list[dict[str, Any]] = []

    provider = data_manager.registry.equity()
    provider_label = provider.name.upper() if provider else "OFFLINE"
    items.append({
        "label": "PROVIDER", "value": provider_label,
        "delta_color": TOKENS["accent_success"] if provider else TOKENS["accent_danger"],
    })
    cap = config["watchlist"]["max_tickers"]
    items.append({
        "label": "WATCH", "value": f"{len(watchlist.list_tickers())}/{cap}",
        "delta": watchlist.backend().upper(), "delta_color": TOKENS["accent_info"],
    })

    vix_id = config["market"]["macro_series"]["volatility"]["vix_series"]
    items.append(_macro_item(data_manager, cache, vix_id, "VIX"))

    for ticker, label in [("SPY", "SPY"), ("QQQ", "QQQ"), ("UUP", "DXY"), ("GLD", "GOLD"), ("USO", "OIL")]:
        items.append(_market_item(data_manager, cache, ticker, label))

    return ticker_tape(items)


def _macro_item(data_manager, cache: LastGoodCache, series_id: str, label: str) -> dict[str, Any]:
    macro = data_manager.get_macro([series_id])
    if not is_error(macro):
        v = macro.latest(series_id)
        if v == v:
            cache.put(label, {"value": float(v)})
            return {"label": label, "value": f"{v:.2f}"}
    cached = cache.get(label)
    if cached:
        v = cached[0]["value"]
        return {"label": label, "value": f"{v:.2f}", "delta": "STALE", "delta_color": TOKENS["text_muted"]}
    return {"label": label, "value": "n/a"}


def _market_item(data_manager, cache: LastGoodCache, ticker: str, label: str) -> dict[str, Any]:
    data = data_manager.get_index_prices(ticker, period="1mo")
    if not is_error(data) and not data.is_empty():
        last = data.last_close()
        prev = float(data.prices["close"].iloc[-2]) if len(data.prices) >= 2 else last
        change = ((last - prev) / prev) if prev else 0.0
        cache.put(label, {"value": float(last), "change": float(change)})
        return {
            "label": label, "value": f"{last:,.2f}",
            "delta": f"{change * 100:+.2f}%", "delta_color": signed_color(change),
        }
    cached = cache.get(label)
    if cached:
        v = cached[0]
        change = v.get("change", 0.0)
        return {
            "label": label, "value": f"{v['value']:,.2f}",
            "delta": f"STALE {change * 100:+.2f}%",
            "delta_color": signed_color(change),
        }
    return {"label": label, "value": "n/a"}
