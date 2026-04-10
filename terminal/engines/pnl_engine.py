"""P&L interpretation layer.

Used contextually by Options Lab (payoffs, Greeks scenarios), LBO Quick
Calc (equity bridge), Portfolio (factor attribution), and Research
(structured bull/base/bear scenario payoffs fed into the LLM memo).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def compute_option_payoff(
    spot: float,
    strike: float,
    premium: float,
    option_type: str,
    quantity: int = 1,
    spot_range_pct: float = 0.30,
    points: int = 200,
) -> pd.DataFrame:
    """Expiration-date payoff for a single option leg.

    Returns a DataFrame indexed by underlying price with columns
    ``intrinsic`` and ``pnl`` (net of premium paid, in dollar terms).
    """
    low = spot * (1 - spot_range_pct)
    high = spot * (1 + spot_range_pct)
    grid = np.linspace(low, high, points)
    if option_type.lower() == "call":
        intrinsic = np.maximum(grid - strike, 0.0)
    else:
        intrinsic = np.maximum(strike - grid, 0.0)
    pnl = (intrinsic - premium) * quantity
    return pd.DataFrame({"spot": grid, "intrinsic": intrinsic, "pnl": pnl}).set_index("spot")


def compute_option_scenario(
    greeks: dict[str, float],
    spot_range: np.ndarray,
    vol_shift: float = 0.0,
    time_decay_days: int = 0,
) -> pd.DataFrame:
    """Greeks-based pre-expiry P&L across a spot grid.

    Approximation: ``dP ~= delta*dS + 0.5*gamma*dS^2 + vega*dSigma + theta*dT``.
    Good enough for the Options Lab scenario widget; not intended to
    replace a full repricing engine.
    """
    spot0 = float(greeks.get("spot", 0.0))
    delta = float(greeks.get("delta", 0.0))
    gamma = float(greeks.get("gamma", 0.0))
    vega = float(greeks.get("vega", 0.0))
    theta = float(greeks.get("theta", 0.0))
    dS = spot_range - spot0
    pnl = delta * dS + 0.5 * gamma * dS ** 2 + vega * vol_shift + theta * (time_decay_days / 365.0)
    return pd.DataFrame({"spot": spot_range, "pnl": pnl}).set_index("spot")


def compute_lbo_equity_bridge(lbo_snapshot: dict[str, Any]) -> dict[str, float]:
    """Decompose entry-to-exit equity value into four attributable legs.

    Legs: EBITDA growth, multiple expansion/contraction, debt paydown,
    and fees/transaction friction. The sum equals exit equity minus
    sponsor equity at entry (modulo rounding).
    """
    entry_ebitda = float(lbo_snapshot.get("entry_ebitda", 0.0))
    exit_ebitda = float(lbo_snapshot.get("exit_ebitda", entry_ebitda))
    entry_multiple = float(lbo_snapshot.get("entry_multiple", 0.0))
    exit_multiple = float(lbo_snapshot.get("exit_multiple", entry_multiple))
    entry_debt = float(lbo_snapshot.get("entry_debt", 0.0))
    exit_debt = float(lbo_snapshot.get("exit_debt", entry_debt))
    fees = float(lbo_snapshot.get("fees", 0.0))
    ebitda_growth = (exit_ebitda - entry_ebitda) * entry_multiple
    multiple_change = exit_ebitda * (exit_multiple - entry_multiple)
    debt_paydown = entry_debt - exit_debt
    return {
        "ebitda_growth": ebitda_growth,
        "multiple_expansion": multiple_change,
        "debt_paydown": debt_paydown,
        "fees_drag": -fees,
        "total_value_creation": ebitda_growth + multiple_change + debt_paydown - fees,
    }


def compute_portfolio_attribution(
    weights: dict[str, float],
    returns: pd.DataFrame,
    factor_exposures: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Contribution-to-return decomposition.

    If ``factor_exposures`` is provided, also returns a factor-level
    attribution; otherwise it reports per-asset contribution only.
    """
    w = pd.Series(weights).reindex(returns.columns).fillna(0.0)
    port_returns = returns.dot(w)
    asset_contrib = (returns.multiply(w, axis=1)).sum(axis=0)
    result: dict[str, Any] = {
        "portfolio_return": float(port_returns.sum()),
        "asset_contribution": asset_contrib.to_dict(),
    }
    if factor_exposures is not None and not factor_exposures.empty:
        port_exposure = factor_exposures.T.dot(w)
        result["factor_exposure"] = port_exposure.to_dict()
    return result


def compute_scenario_payoffs(
    ticker_data: dict[str, Any],
    scenarios: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    """Bull/base/bear dollar outcomes for the Research workspace.

    ``scenarios`` is the ``pnl.scenarios`` dict from config.yaml. This is
    the structured payload the LLM memo receives, so its shape is stable
    and documented -- do not rename keys casually.
    """
    spot = float(ticker_data.get("spot", 0.0))
    shares = float(ticker_data.get("shares", 100.0))
    out: list[dict[str, Any]] = []
    for key, params in scenarios.items():
        price_change = float(params.get("price_change_pct", 0.0))
        target = spot * (1 + price_change)
        dollar_pnl = (target - spot) * shares
        out.append({
            "scenario": key,
            "label": str(params.get("label", key)),
            "price_target": target,
            "dollar_pnl": dollar_pnl,
            "return_pct": price_change,
        })
    return out
