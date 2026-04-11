"""Last-good fallback helpers for FRED macro series.

Keeps ``SharedDataManager.get_macro`` short by moving the persist +
back-fill logic into its own module. The UI surface never sees these
functions; the manager calls them directly.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..data.schemas import MacroData
from ..utils.last_good_cache import LastGoodCache


def persist_last_good(cache: LastGoodCache, data: MacroData, series: list[str]) -> None:
    """Store the latest non-NaN observation for every successful id."""
    for sid in series:
        s = data.series.get(sid)
        if s is None or s.empty:
            continue
        clean = s.dropna()
        if clean.empty:
            continue
        ts = clean.index[-1]
        cache.put(
            f"fred::{sid}",
            {
                "value": float(clean.iloc[-1]),
                "as_of": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            },
        )


def backfill_from_last_good(
    cache: LastGoodCache,
    data: MacroData,
    series: list[str],
) -> set[str]:
    """Fill empty series with the last good value and return the stale set.

    Every id that comes back empty from the live fetch and has a
    matching last-good entry is replaced with a one-row series anchored
    at the stored ``as_of``. The set of stale ids is merged into
    ``data.stale`` so the UI can annotate them with a STALE marker.
    """
    stale: set[str] = set()
    for sid in series:
        s = data.series.get(sid)
        if s is not None and not s.dropna().empty:
            continue
        entry = cache.get(f"fred::{sid}")
        if not entry:
            continue
        payload, _ts_stored = entry
        if not isinstance(payload, dict):
            continue
        value = payload.get("value")
        as_of_str = payload.get("as_of")
        if value is None:
            continue
        try:
            idx = pd.to_datetime(as_of_str)
        except Exception:
            idx = pd.Timestamp.utcnow()
        data.series[sid] = pd.Series([float(value)], index=[idx], name=sid)
        stale.add(sid)
    if stale:
        data.stale = (data.stale or set()) | stale
    return stale
