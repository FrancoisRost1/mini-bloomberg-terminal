"""Financial Modeling Prep payload parsers (stable/ endpoints).

Pure functions, no I/O. Defensive about field names because the
``stable/`` API uses slightly different keys than the legacy v3/ API
in places (mktCap vs marketCap, dividend yield naming, etc).
"""

from __future__ import annotations

from typing import Any

import pandas as pd


PERIOD_TO_DAYS = {"1mo": 21, "3mo": 63, "6mo": 126, "1y": 252, "2y": 504, "5y": 1260}


def safe_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def parse_historical(payload: list[dict[str, Any]] | dict[str, Any], period: str) -> pd.DataFrame:
    """Convert FMP historical payload to OHLCV DataFrame.

    Handles three observed shapes:
    - flat list of bars (stable/historical-price-eod/full)
    - dict with ``historical`` key (older v3 shape, kept for safety)
    - dict with ``data`` key (some stable variants)
    """
    if isinstance(payload, dict):
        rows = payload.get("historical") or payload.get("data") or []
    else:
        rows = payload or []
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume"])
    df = pd.DataFrame(rows)
    if "date" not in df.columns:
        return pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    rename = {"adjClose": "adj_close"}
    df = df.rename(columns=rename)
    if "adj_close" not in df.columns and "close" in df.columns:
        df["adj_close"] = df["close"]
    keep = [c for c in ["open", "high", "low", "close", "adj_close", "volume"] if c in df.columns]
    df = df[keep]
    for c in keep:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    n = PERIOD_TO_DAYS.get(period, 252)
    return df.tail(n)


def parse_statement(payload: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert an annual statement array (income / balance / cash flow)."""
    if not payload:
        return pd.DataFrame()
    df = pd.DataFrame(payload)
    if "date" not in df.columns:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col], errors="ignore")
            except (TypeError, ValueError):
                pass
    return df


def _first(d: dict, *keys: str) -> Any:
    """Return d[key] for the first key that exists."""
    for k in keys:
        if k in d:
            return d[k]
    return None


# compute_ratios lives in _fmp_ratios.py. Do NOT re-import it here.
# That would create a circular import because _fmp_ratios.py imports
# helpers from this module. Callers should import compute_ratios
# directly from terminal.data._fmp_ratios.
