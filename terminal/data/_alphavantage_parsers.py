"""Alpha Vantage payload parsers.

Split out of ``provider_alphavantage.py`` to keep the provider class
under the per-module line budget. Pure functions, no I/O, no network.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


PERIOD_TO_DAYS = {"1mo": 21, "3mo": 63, "6mo": 126, "1y": 252, "2y": 504, "5y": 1260}


def safe_float(value: Any) -> float:
    """Coerce an Alpha Vantage scalar to float, mapping sentinels to NaN."""
    try:
        if value is None or value == "None" or value == "-":
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def parse_daily_series(payload: dict[str, Any], period: str) -> pd.DataFrame:
    """Convert ``Time Series (Daily)`` payload into an OHLCV DataFrame."""
    series = payload.get("Time Series (Daily)", {})
    rows: list[dict[str, Any]] = []
    for date_str, bar in series.items():
        rows.append({
            "date": pd.Timestamp(date_str),
            "open": float(bar["1. open"]),
            "high": float(bar["2. high"]),
            "low": float(bar["3. low"]),
            "close": float(bar["4. close"]),
            "adj_close": float(bar.get("5. adjusted close", bar["4. close"])),
            "volume": float(bar["6. volume"]),
        })
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume"])
    df = pd.DataFrame(rows).set_index("date").sort_index()
    n = PERIOD_TO_DAYS.get(period, 252)
    return df.tail(n)


def parse_statement(payload: dict[str, Any]) -> pd.DataFrame:
    """Convert an annual statement payload (income / balance / cashflow) into a DataFrame."""
    reports = payload.get("annualReports", [])
    if not reports:
        return pd.DataFrame()
    df = pd.DataFrame(reports)
    df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
    df = df.set_index("fiscalDateEnding").sort_index()
    for col in df.columns:
        if col != "reportedCurrency":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def compute_ratios(
    overview: dict[str, Any],
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> dict[str, float]:
    """Derive the terminal's canonical key_ratios dict from raw AV payloads.

    Keys must match the rest of the pipeline: ``pe_ratio``, ``ev_ebitda``,
    ``ebitda_margin``, ``roic``, ``dividend_yield``, ``beta``, plus the
    optional growth / FCF / leverage metrics when data is available.
    """
    ratios = {
        "pe_ratio": safe_float(overview.get("PERatio")),
        "ev_ebitda": safe_float(overview.get("EVToEBITDA")),
        "ebitda_margin": safe_float(overview.get("EBITDA")) / max(safe_float(overview.get("RevenueTTM")), 1.0),
        "roic": safe_float(overview.get("ReturnOnEquityTTM")),
        "dividend_yield": safe_float(overview.get("DividendYield")),
        "beta": safe_float(overview.get("Beta")),
    }
    if not income.empty and "totalRevenue" in income.columns:
        rev = income["totalRevenue"].dropna()
        if len(rev) >= 2:
            ratios["revenue_growth"] = float(rev.iloc[-1] / rev.iloc[-2] - 1.0)
    if not cashflow.empty:
        ocf = cashflow.get("operatingCashflow", pd.Series(dtype=float)).dropna()
        capex = cashflow.get("capitalExpenditures", pd.Series(dtype=float)).dropna()
        if not ocf.empty and not capex.empty:
            fcf = ocf.iloc[-1] - abs(capex.iloc[-1])
            ebitda = safe_float(overview.get("EBITDA"))
            ratios["fcf_conversion"] = float(fcf / ebitda) if ebitda else float("nan")
    if not balance.empty:
        total_debt = balance.get("shortLongTermDebtTotal", pd.Series(dtype=float)).dropna()
        cash = balance.get("cashAndCashEquivalentsAtCarryingValue", pd.Series(dtype=float)).dropna()
        ebitda = safe_float(overview.get("EBITDA"))
        if not total_debt.empty and ebitda:
            net_debt = total_debt.iloc[-1] - (cash.iloc[-1] if not cash.empty else 0)
            ratios["net_debt_ebitda"] = float(net_debt / ebitda)
    return ratios


def parse_options_chain(payload: dict[str, Any]) -> tuple[float, dict[str, pd.DataFrame]]:
    """Group the ``HISTORICAL_OPTIONS`` payload into per-expiry DataFrames."""
    contracts = payload.get("data", [])
    if not contracts:
        return float("nan"), {}
    df = pd.DataFrame(contracts)
    for col in ["strike", "bid", "ask", "last", "volume", "open_interest"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    chains: dict[str, pd.DataFrame] = {}
    if "expiration" in df.columns:
        keep_cols = [c for c in ["strike", "bid", "ask", "last", "volume", "open_interest", "type"] if c in df.columns]
        for expiry, group in df.groupby("expiration"):
            chains[str(expiry)] = group[keep_cols].reset_index(drop=True)
    spot = float(df.get("underlying_price", pd.Series([float("nan")])).iloc[0]) if "underlying_price" in df.columns else float("nan")
    return spot, chains
