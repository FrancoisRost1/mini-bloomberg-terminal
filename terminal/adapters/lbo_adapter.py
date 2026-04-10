"""LBO adapter (wraps P1 LBO Engine, base case only).

Runs a single base-case LBO snapshot from user-adjustable inputs and
returns the standard output dict for the LBO Quick Calc page and the
Research pipeline. No Monte Carlo, no covenant breach detection.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy_financial as npf


SOURCE_PROJECT = "P1: LBO Engine"
SIMPLIFICATIONS = ["Base case only", "No Monte Carlo", "No scenario lab"]


def run_base_case(assumptions: dict[str, Any]) -> dict[str, Any]:
    """Compute entry -> exit LBO mechanics from an assumptions dict.

    Financial rationale: PE returns decompose into EBITDA growth, multiple
    expansion, and debt paydown. The function returns each leg separately
    so the P&L equity bridge can attribute value creation.
    """
    entry_ebitda = float(assumptions["entry_ebitda"])
    entry_multiple = float(assumptions["entry_multiple"])
    exit_multiple = float(assumptions["exit_multiple"])
    leverage = float(assumptions["leverage"])
    hold = int(assumptions["hold_period"])
    rev_growth = float(assumptions["revenue_growth"])
    margin = float(assumptions["ebitda_margin"])
    capex_pct = float(assumptions["capex_pct_revenue"])
    tax = float(assumptions["tax_rate"])
    nwc_pct = float(assumptions["nwc_pct_revenue"])
    debt_rate = float(assumptions["debt_rate"])
    amort_rate = float(assumptions["amort_rate"])
    sweep = float(assumptions["cash_sweep"])
    fees_pct = float(assumptions["fees_pct"])

    entry_ev = entry_ebitda * entry_multiple
    fees = entry_ev * fees_pct
    entry_debt = entry_ebitda * leverage
    sponsor_equity = entry_ev + fees - entry_debt

    revenue_0 = entry_ebitda / margin if margin > 0 else entry_ebitda
    debt = entry_debt
    ebitda_path = []
    for year in range(1, hold + 1):
        revenue = revenue_0 * (1 + rev_growth) ** year
        ebitda = revenue * margin
        capex = revenue * capex_pct
        taxes = max(0.0, (ebitda - debt * debt_rate) * tax)
        nwc_change = revenue * nwc_pct * rev_growth
        fcf = ebitda - capex - taxes - nwc_change
        mandatory = debt * amort_rate
        interest = debt * debt_rate
        optional = max(0.0, (fcf - interest - mandatory) * sweep)
        debt = max(0.0, debt - mandatory - optional)
        ebitda_path.append(ebitda)

    exit_ebitda = ebitda_path[-1]
    exit_ev = exit_ebitda * exit_multiple
    equity_at_exit = max(0.0, exit_ev - debt)
    cashflows = [-sponsor_equity] + [0.0] * (hold - 1) + [equity_at_exit]
    irr = _safe_irr(cashflows)
    moic = equity_at_exit / sponsor_equity if sponsor_equity > 0 else float("nan")

    return {
        "status": "success",
        "source_project": SOURCE_PROJECT,
        "entry_ev": entry_ev,
        "entry_ebitda": entry_ebitda,
        "entry_multiple": entry_multiple,
        "exit_ebitda": exit_ebitda,
        "exit_multiple": exit_multiple,
        "exit_ev": exit_ev,
        "entry_debt": entry_debt,
        "exit_debt": debt,
        "sponsor_equity": sponsor_equity,
        "equity_at_exit": equity_at_exit,
        "fees": fees,
        "irr": irr,
        "moic": moic,
        "ebitda_path": ebitda_path,
    }


def sensitivity_grid(
    assumptions: dict[str, Any],
    exit_multiples: list[float],
    growth_rates: list[float],
) -> list[list[float]]:
    """IRR across (exit multiple, revenue growth) for the sensitivity table."""
    grid: list[list[float]] = []
    for growth in growth_rates:
        row: list[float] = []
        for mult in exit_multiples:
            tweaked = dict(assumptions)
            tweaked["exit_multiple"] = mult
            tweaked["revenue_growth"] = growth
            result = run_base_case(tweaked)
            row.append(result["irr"])
        grid.append(row)
    return grid


def _safe_irr(cashflows: list[float]) -> float:
    try:
        irr = npf.irr(cashflows)
    except Exception:
        return float("nan")
    if irr is None or np.isnan(irr):
        return float("nan")
    return float(irr)
