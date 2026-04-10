"""FMP key ratios builder.

Pulled out of _fmp_parsers.py so the parsers module stays under the
~150 line budget. Pure functions, no I/O. Defensive about field names
because the stable/ API uses slightly different keys than the legacy
v3/ API in places.

Every metric here has at least one fallback path so the Research and
Comps pages avoid n/a whenever the underlying data is present.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ._fmp_parsers import _first, safe_float


def derive_dividend_yield(profile: dict, quote: dict, cashflow: pd.DataFrame, price: float) -> float:
    """Best effort dividend yield. Sources, in order:

    1. profile.lastDiv / lastDividend / lastAnnualDividend divided by spot.
    2. quote.lastDiv divided by spot.
    3. cashflow.dividendsPaid divided by quote.sharesOutstanding (or
       mktCap / price if shares missing), then divided by spot.

    Returns NaN when no source is usable.
    """
    if price <= 0 or price != price:
        return float("nan")
    last_div = safe_float(_first(profile, "lastDiv", "lastDividend", "lastAnnualDividend"))
    if last_div == last_div and last_div > 0:
        return float(last_div / price)
    last_div_q = safe_float(_first(quote, "lastDiv", "lastDividend"))
    if last_div_q == last_div_q and last_div_q > 0:
        return float(last_div_q / price)
    if not cashflow.empty:
        divs = cashflow.get("dividendsPaid", pd.Series(dtype=float)).dropna()
        if not divs.empty:
            paid = abs(float(divs.iloc[-1]))
            shares = safe_float(_first(quote, "sharesOutstanding", "outstandingShares"))
            if (shares != shares or shares <= 0):
                mcap = safe_float(_first(profile, "mktCap", "marketCap"))
                if mcap == mcap and mcap > 0:
                    shares = mcap / price
            if shares == shares and shares > 0:
                return float((paid / shares) / price)
    return float("nan")


def _resolve_ebitda(income: pd.DataFrame) -> float:
    """Direct ebitda field, falling back to operatingIncome + D&A."""
    if "ebitda" in income.columns:
        eb = income["ebitda"].dropna()
        if not eb.empty:
            v = safe_float(eb.iloc[-1])
            if v == v and v != 0:
                return float(v)
    op_inc = income.get("operatingIncome", pd.Series(dtype=float)).dropna()
    da = income.get("depreciationAndAmortization", pd.Series(dtype=float)).dropna()
    if not op_inc.empty and not da.empty:
        return float(op_inc.iloc[-1]) + float(da.iloc[-1])
    return float("nan")


def _resolve_pe(price: float, profile: dict, quote: dict, net_income_latest: float) -> float:
    """Native quote.pe, falling back to price * shares / net income."""
    pe_native = safe_float(_first(quote, "pe", "peRatio", "priceEarningsRatio"))
    if pe_native == pe_native and pe_native > 0:
        return float(pe_native)
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
            return float(price / eps)
    return float("nan")


def compute_ratios(
    profile: dict[str, Any],
    quote: dict[str, Any],
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> dict[str, float]:
    """Build the canonical key_ratios dict from FMP stable/ payloads."""
    price = safe_float(_first(quote, "price", "lastPrice"))
    ratios: dict[str, float] = {
        "pe_ratio": float("nan"),
        "beta": safe_float(profile.get("beta")),
        "dividend_yield": derive_dividend_yield(profile, quote, cashflow, price),
        # Always seeded so the KPI strip can distinguish "truly nan" from
        # "key absent because the compute path bailed early". Populated
        # below where the data supports it.
        "interest_coverage": float("nan"),
    }
    notes: dict[str, str] = {}
    revenue = ebitda = float("nan")
    net_income_latest = float("nan")
    if not income.empty:
        rev = income.get("revenue", pd.Series(dtype=float)).dropna()
        if not rev.empty:
            revenue = safe_float(rev.iloc[-1])
        if len(rev) >= 2 and rev.iloc[-2] > 0:
            ratios["revenue_growth"] = float(rev.iloc[-1] / rev.iloc[-2] - 1.0)
        ebitda = _resolve_ebitda(income)
        ni_series = income.get("netIncome", pd.Series(dtype=float)).dropna()
        if not ni_series.empty:
            net_income_latest = safe_float(ni_series.iloc[-1])
        ebit = income.get("operatingIncome", pd.Series(dtype=float)).dropna()
        if ebit.empty:
            ebit = income.get("ebit", pd.Series(dtype=float)).dropna()
        interest_col = income.get("interestExpense", pd.Series(dtype=float))
        interest = interest_col.dropna() if interest_col is not None else pd.Series(dtype=float)
        if not ebit.empty and not interest.empty and abs(interest.iloc[-1]) > 0:
            ratios["interest_coverage"] = float(ebit.iloc[-1] / abs(interest.iloc[-1]))
        elif not ebit.empty and (interest.empty or abs(interest.iloc[-1]) == 0):
            # EBIT is fine but there is no interest expense to divide by.
            # Either FMP did not return the field for this filer, or the
            # company is debt free. The KPI cell is narrow so we use
            # the abbreviated "N/R" sentinel rather than spelling out
            # "not reported" (which would clip on the Research strip).
            notes["interest_coverage"] = "N/R"
    ratios["pe_ratio"] = _resolve_pe(price, profile, quote, net_income_latest)
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
        ni = income.get("netIncome", pd.Series(dtype=float)).dropna()
        if not equity.empty and not ni.empty and equity.iloc[-1] > 0:
            ratios["roe"] = float(ni.iloc[-1] / equity.iloc[-1])
    if not cashflow.empty and ebitda == ebitda and ebitda > 0:
        ocf = cashflow.get("operatingCashFlow", pd.Series(dtype=float)).dropna()
        capex = cashflow.get("capitalExpenditure", pd.Series(dtype=float)).dropna()
        if not ocf.empty and not capex.empty:
            fcf = float(ocf.iloc[-1]) - abs(float(capex.iloc[-1]))
            ratios["fcf_conversion"] = float(fcf / ebitda)
    if notes:
        ratios["_notes"] = notes  # type: ignore[assignment]
    return ratios
