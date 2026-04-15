"""Fetch earnings data from yfinance.

Uses ticker.calendar for next earnings date and estimates, and
ticker.earnings_history for last 4 quarters of EPS actual vs
estimate. Never raises -- returns empty structure on failure.
"""

from __future__ import annotations

import math
from datetime import date


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


def fetch_earnings(ticker: str) -> dict:
    """Return earnings calendar and history for *ticker*."""
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        cal = tk.calendar or {}
        hist = tk.earnings_history
    except Exception:
        return {"next_date": None, "eps_estimate": None, "history": []}

    # Next earnings date from calendar.
    next_date = None
    dates = cal.get("Earnings Date", [])
    if isinstance(dates, list) and dates:
        d = dates[0]
        next_date = d.isoformat() if isinstance(d, date) else str(d)[:10]
    elif isinstance(dates, date):
        next_date = dates.isoformat()

    eps_est = _safe_float(cal.get("Earnings Average"))

    # Historical quarters.
    history: list[dict] = []
    if hist is not None and not hist.empty:
        for qtr, row in hist.iterrows():
            qtr_label = str(qtr)[:10] if qtr is not None else ""
            history.append({
                "quarter": qtr_label,
                "eps_actual": _safe_float(row.get("epsActual")),
                "eps_estimate": _safe_float(row.get("epsEstimate")),
                "surprise_pct": _safe_float(row.get("surprisePercent")),
            })

    return {"next_date": next_date, "eps_estimate": eps_est, "history": history}
