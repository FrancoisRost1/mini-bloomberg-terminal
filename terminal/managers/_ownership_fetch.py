"""Fetch institutional holders and insider transactions from yfinance.

Returns a dict with 'institutions' (list of dicts) and 'insiders'
(list of dicts). Never raises -- returns empty lists on failure.
"""

from __future__ import annotations

import math
from functools import lru_cache

from terminal.data._yfinance_session import get_hardened_session


@lru_cache(maxsize=1)
def _session():
    return get_hardened_session()


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


def _safe_str(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def fetch_ownership(ticker: str) -> dict:
    """Pull institutional holders and insider transactions."""
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker, session=_session())
        ih = tk.institutional_holders
        it = tk.insider_transactions
    except Exception:
        return {"institutions": [], "insiders": []}

    institutions: list[dict] = []
    if ih is not None and not ih.empty:
        for _, row in ih.head(5).iterrows():
            institutions.append({
                "holder": _safe_str(row.get("Holder")),
                "shares": _safe_float(row.get("Shares")),
                "pct_held": _safe_float(row.get("pctHeld")),
            })

    insiders: list[dict] = []
    if it is not None and not it.empty:
        for _, row in it.head(5).iterrows():
            date_val = row.get("Start Date")
            date_str = ""
            if date_val is not None:
                try:
                    date_str = str(date_val)[:10]
                except Exception:
                    pass
            txn_text = _safe_str(row.get("Text")) or _safe_str(row.get("Transaction"))
            insiders.append({
                "date": date_str,
                "insider": _safe_str(row.get("Insider")),
                "transaction": txn_text,
                "shares": _safe_float(row.get("Shares")),
                "value": _safe_float(row.get("Value")),
            })

    return {"institutions": institutions, "insiders": insiders}
