"""Header ticker tape item builder.

Builds the marquee item list for the global header. Uses a single
batched yfinance download via ``header_tape_batch.fetch_tape_batch``
so a 30+ ticker tape costs one HTTP round trip, not one per item.

Tickers that fail to come back are dropped silently; the marquee
still animates on whatever did fetch so the tape is never empty.
The ``LastGoodCache`` is used as a cross-session fallback so the
first render after a deploy never shows a short tape.
"""

from __future__ import annotations

from typing import Any

from app.header_tape_batch import TAPE_UNIVERSE, fetch_tape_batch
from terminal.managers.data_manager import SharedDataManager
from terminal.utils.last_good_cache import LastGoodCache
from terminal.utils.watchlist_io import WatchlistStore  # noqa: F401  imported for type compat


def build_tape_items(
    data_manager: SharedDataManager,
    watchlist,  # accepted for backward compat with header.render signature
    config: dict[str, Any],
    cache: LastGoodCache,
) -> list[dict[str, Any]]:
    """Return the list of dicts the marquee component consumes.

    Each dict: ``label`` (str), ``price`` (str), ``change_pct``
    (float or None). A trailing asterisk on the label indicates
    the value came from the LastGoodCache fallback rather than a
    fresh fetch, so the tape never reads as sparse.
    """
    batch = fetch_tape_batch()
    items: list[dict[str, Any]] = []
    for label, _symbol in TAPE_UNIVERSE:
        entry = batch.get(label)
        if entry is not None:
            price = float(entry["price"])
            change = float(entry["change_pct"])
            cache.put(label, {"value": price, "change": change})
            items.append({
                "label": label,
                "price": _fmt_price(label, price),
                "change_pct": change,
            })
            continue
        cached = cache.get(label)
        if cached:
            payload = cached[0]
            if isinstance(payload, dict) and "value" in payload:
                items.append({
                    "label": f"{label}*",
                    "price": _fmt_price(label, float(payload["value"])),
                    "change_pct": float(payload.get("change", 0.0)),
                })
    return items


def _fmt_price(label: str, value: float) -> str:
    """Format a tape price with sensible decimals per asset class."""
    if label in {"EURUSD", "USDJPY"}:
        return f"{value:,.4f}"
    if label == "BTCUSD":
        return f"{value:,.0f}"
    if label == "VIX":
        return f"{value:.2f}"
    return f"{value:,.2f}"
