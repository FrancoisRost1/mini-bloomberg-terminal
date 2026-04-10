"""Header ticker tape item builder.

Pulled out of header.py so the page module stays under the line
budget. Builds the list of dicts that ``bloomberg_tape`` consumes:
provider status, watchlist count, VIX (FRED), and the configured
market tickers from yfinance with arrows and signed % change.

Each item served from the cache when fresh fetch fails carries a
STALE prefix in its label.
"""

from __future__ import annotations

from typing import Any

from terminal.managers.data_manager import SharedDataManager
from terminal.utils.error_handling import is_error
from terminal.utils.last_good_cache import LastGoodCache
from terminal.utils.watchlist_io import WatchlistStore


# Display label, yfinance symbol. Active ticker is injected at runtime.
TAPE_TICKERS: list[tuple[str, str]] = [
    ("SPY",     "SPY"),
    ("QQQ",     "QQQ"),
    ("DJI",     "^DJI"),
    ("EURUSD",  "EURUSD=X"),
    ("BTCUSD",  "BTC-USD"),
    ("CL",      "CL=F"),
    ("GLD",     "GLD"),
]


def build_tape_items(
    data_manager: SharedDataManager,
    watchlist: WatchlistStore,
    config: dict[str, Any],
    cache: LastGoodCache,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    items.append(_provider_pill(data_manager))
    items.append(_watchlist_pill(watchlist, config))
    items.append(_vix_item(data_manager, config, cache))

    active = (str(_active_ticker_safe()) or "AAPL").upper()
    items.append(_active_ticker_item(data_manager, cache, active))

    for label, ticker in TAPE_TICKERS:
        items.append(_market_item(data_manager, cache, ticker, label))

    return items


def _active_ticker_safe() -> str:
    """Read st.session_state.active_ticker without importing streamlit at module level."""
    import streamlit as st
    return st.session_state.get("active_ticker", "AAPL")


def _provider_pill(data_manager: SharedDataManager) -> dict[str, Any]:
    provider = data_manager.registry.equity()
    label = provider.name.upper() if provider else "OFFLINE"
    return {"label": "SRC", "price": label, "change_pct": None}


def _watchlist_pill(watchlist: WatchlistStore, config: dict[str, Any]) -> dict[str, Any]:
    cap = config["watchlist"]["max_tickers"]
    return {"label": "WATCH", "price": f"{len(watchlist.list_tickers())}/{cap}", "change_pct": None}


def _vix_item(data_manager: SharedDataManager, config: dict[str, Any], cache: LastGoodCache) -> dict[str, Any]:
    series_id = config["market"]["macro_series"]["volatility"]["vix_series"]
    macro = data_manager.get_macro([series_id])
    if not is_error(macro):
        v = macro.latest(series_id)
        if v == v:
            cache.put("VIX", {"value": float(v)})
            return {"label": "VIX", "price": f"{v:.2f}", "change_pct": None}
    cached = cache.get("VIX")
    if cached:
        return {"label": "VIX*", "price": f"{cached[0]['value']:.2f}", "change_pct": None}
    return {"label": "VIX", "price": "n/a", "change_pct": None}


def _active_ticker_item(data_manager: SharedDataManager, cache: LastGoodCache, ticker: str) -> dict[str, Any]:
    """Active ticker may be a stock or an ETF. Use the any_prices cascade."""
    data = data_manager.get_any_prices(ticker, period="1mo")
    return _build_market_dict(data, cache, ticker, ticker)


def _market_item(data_manager: SharedDataManager, cache: LastGoodCache, ticker: str, label: str) -> dict[str, Any]:
    data = data_manager.get_index_prices(ticker, period="1mo")
    return _build_market_dict(data, cache, ticker, label)


def _build_market_dict(data, cache: LastGoodCache, ticker: str, label: str) -> dict[str, Any]:
    if not is_error(data) and not data.is_empty():
        last = data.last_close()
        prev = float(data.prices["close"].iloc[-2]) if len(data.prices) >= 2 else last
        change = ((last - prev) / prev) if prev else 0.0
        cache.put(label, {"value": float(last), "change": float(change)})
        return {"label": label, "price": f"{last:,.2f}", "change_pct": change}
    cached = cache.get(label)
    if cached:
        v = cached[0]
        return {"label": f"{label}*", "price": f"{v['value']:,.2f}", "change_pct": v.get("change", 0.0)}
    return {"label": label, "price": "n/a", "change_pct": None}
