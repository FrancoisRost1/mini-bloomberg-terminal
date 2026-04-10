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


def compute_ratios(
    profile: dict[str, Any],
    quote: dict[str, Any],
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> dict[str, float]:
    """Build the canonical key_ratios dict from FMP stable/ payloads.

    Defensive about field names: stable/profile uses ``mktCap`` or
    ``marketCap`` depending on version, ``lastDiv`` or ``lastDividend``,
    etc. Same for stable/quote ``pe`` or ``peRatio``.
    """
    price = safe_float(_first(quote, "price", "lastPrice"))
    last_div = safe_float(_first(profile, "lastDiv", "lastDividend"))
    ratios: dict[str, float] = {
        "pe_ratio": safe_float(_first(quote, "pe", "peRatio", "priceEarningsRatio")),
        "beta": safe_float(profile.get("beta")),
        "dividend_yield": (last_div / price) if price > 0 and last_div == last_div else float("nan"),
    }
    revenue = ebitda = float("nan")
    net_income_latest = float("nan")
    if not income.empty:
        rev_col = "revenue" if "revenue" in income.columns else None
        if rev_col:
            rev = income[rev_col].dropna()
            if not rev.empty:
                revenue = safe_float(rev.iloc[-1])
            if len(rev) >= 2 and rev.iloc[-2] > 0:
                ratios["revenue_growth"] = float(rev.iloc[-1] / rev.iloc[-2] - 1.0)
        if "ebitda" in income.columns:
            eb = income["ebitda"].dropna()
            if not eb.empty:
                ebitda = safe_float(eb.iloc[-1])
        ni_series = income.get("netIncome", pd.Series(dtype=float)).dropna()
        if not ni_series.empty:
            net_income_latest = safe_float(ni_series.iloc[-1])
        ebit_col = "operatingIncome" if "operatingIncome" in income.columns else "ebit"
        ebit = income.get(ebit_col, pd.Series(dtype=float)).dropna()
        interest = income.get("interestExpense", pd.Series(dtype=float)).dropna()
        if not ebit.empty and not interest.empty and abs(interest.iloc[-1]) > 0:
            # FMP reports interestExpense as positive in some sectors, negative in others.
            ratios["interest_coverage"] = float(ebit.iloc[-1] / abs(interest.iloc[-1]))
    # P/E fallback: if FMP returned no quote.pe, derive from net income / shares outstanding.
    pe_native = ratios.get("pe_ratio", float("nan"))
    if (pe_native != pe_native) or pe_native <= 0:
        shares = safe_float(_first(quote, "sharesOutstanding", "outstandingShares"))
        if shares != shares or shares <= 0:
            mcap = safe_float(_first(profile, "mktCap", "marketCap"))
            if mcap == mcap and price > 0:
                shares = mcap / price
        if (shares == shares and shares > 0
                and net_income_latest == net_income_latest and net_income_latest > 0
                and price > 0):
            eps = net_income_latest / shares
            if eps > 0:
                ratios["pe_ratio"] = float(price / eps)
    if revenue == revenue and revenue > 0 and ebitda == ebitda:
        ratios["ebitda_margin"] = float(ebitda / revenue)
    market_cap = safe_float(_first(profile, "mktCap", "marketCap"))
    if market_cap == market_cap and ebitda == ebitda and ebitda > 0 and not balance.empty:
        debt = balance.get("totalDebt", pd.Series(dtype=float)).dropna()
        cash_col = "cashAndCashEquivalents" if "cashAndCashEquivalents" in balance.columns else "cashAndShortTermInvestments"
        cash = balance.get(cash_col, pd.Series(dtype=float)).dropna()
        if not debt.empty:
            net_debt = float(debt.iloc[-1]) - (float(cash.iloc[-1]) if not cash.empty else 0.0)
            ratios["ev_ebitda"] = float((market_cap + net_debt) / ebitda)
            ratios["net_debt_ebitda"] = float(net_debt / ebitda)
    if not balance.empty and not income.empty:
        equity = balance.get("totalStockholdersEquity", pd.Series(dtype=float)).dropna()
        net_income = income.get("netIncome", pd.Series(dtype=float)).dropna()
        if not equity.empty and not net_income.empty and equity.iloc[-1] > 0:
            ratios["roe"] = float(net_income.iloc[-1] / equity.iloc[-1])
    if not cashflow.empty and ebitda == ebitda and ebitda > 0:
        ocf = cashflow.get("operatingCashFlow", pd.Series(dtype=float)).dropna()
        capex = cashflow.get("capitalExpenditure", pd.Series(dtype=float)).dropna()
        if not ocf.empty and not capex.empty:
            fcf = float(ocf.iloc[-1]) - abs(float(capex.iloc[-1]))
            ratios["fcf_conversion"] = float(fcf / ebitda)
    return ratios
