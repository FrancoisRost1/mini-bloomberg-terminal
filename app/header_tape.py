"""Header ticker tape item builder.

Pulled out of header.py so the page module stays under the line
budget. Builds the list of dicts that the marquee component consumes:
fixed market tickers (SPY, QQQ, AAPL, DJI, VIX, EURUSD, BTCUSD, CL,
GLD) with arrows and signed % change.

Each item served from the cache when fresh fetch fails carries an
asterisk in its label so the tape always reads as a live tape.
"""

from __future__ import annotations

from typing import Any

from terminal.managers.data_manager import SharedDataManager
from terminal.utils.error_handling import is_error
from terminal.utils.last_good_cache import LastGoodCache
from terminal.utils.watchlist_io import WatchlistStore  # noqa: F401  imported for type compat


# Display label, fetch symbol, route ("index" / "stock" / "vix" / "macro").
# Target is 11 items with no gaps. If any one of these fails, it is
# dropped from the tape silently; the CSS marquee still animates on
# whatever items did fetch so the tape never reads as sparse.
TAPE_TICKERS: list[tuple[str, str, str]] = [
    ("SPY",     "SPY",      "index"),
    ("QQQ",     "QQQ",      "index"),
    ("DJI",     "^DJI",     "index"),
    ("AAPL",    "AAPL",     "stock"),
    ("MSFT",    "MSFT",     "stock"),
    ("NVDA",    "NVDA",     "stock"),
    ("EURUSD",  "EURUSD=X", "index"),
    ("BTCUSD",  "BTC-USD",  "index"),
    ("CL",      "CL=F",     "index"),
    ("GLD",     "GLD",      "index"),
    ("VIX",     "VIXCLS",   "vix"),
]


def build_tape_items(
    data_manager: SharedDataManager,
    watchlist,  # accepted for backward compat with header.render signature
    config: dict[str, Any],
    cache: LastGoodCache,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for label, symbol, route in TAPE_TICKERS:
        if route == "vix":
            item = _vix_item(data_manager, config, cache)
        elif route == "stock":
            item = _stock_item(data_manager, cache, symbol, label)
        else:
            item = _index_item(data_manager, cache, symbol, label)
        # Skip entries that have no price and no fallback. The marquee
        # reads better with 9 live items than with 11 where two are
        # visible as "n/a" holes.
        if item.get("price") == "n/a" or item.get("price") is None:
            continue
        items.append(item)
    return items


def _vix_item(data_manager: SharedDataManager, config: dict[str, Any], cache: LastGoodCache) -> dict[str, Any]:
    series_id = config["market"]["macro_series"]["volatility"]["vix_series"]
    macro = data_manager.get_macro([series_id])
    if not is_error(macro):
        series = macro.series.get(series_id)
        if series is not None and not series.dropna().empty:
            clean = series.dropna()
            v = float(clean.iloc[-1])
            prev = float(clean.iloc[-2]) if len(clean) >= 2 else v
            chg = (v - prev) / prev if prev else 0.0
            cache.put("VIX", {"value": v, "change": chg})
            return {"label": "VIX", "price": f"{v:.2f}", "change_pct": chg}
    cached = cache.get("VIX")
    if cached:
        c = cached[0]
        return {"label": "VIX*", "price": f"{c['value']:.2f}", "change_pct": c.get("change", 0.0)}
    return {"label": "VIX", "price": "n/a", "change_pct": None}


def _stock_item(data_manager: SharedDataManager, cache: LastGoodCache, ticker: str, label: str) -> dict[str, Any]:
    data = data_manager.get_any_prices(ticker, period="1mo")
    return _build_market_dict(data, cache, label)


def _index_item(data_manager: SharedDataManager, cache: LastGoodCache, ticker: str, label: str) -> dict[str, Any]:
    data = data_manager.get_index_prices(ticker, period="1mo")
    return _build_market_dict(data, cache, label)


def _build_market_dict(data, cache: LastGoodCache, label: str) -> dict[str, Any]:
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
