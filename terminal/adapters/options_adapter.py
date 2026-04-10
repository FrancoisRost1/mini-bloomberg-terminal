"""Options adapter (wraps P9 Options Pricing Engine).

Provides: Black-Scholes analytical Greeks, implied vol extraction via
Brent's method, and a vol surface builder from a live chain. No delta
hedging simulation in v1 (see CLAUDE.md simplifications).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm


SOURCE_PROJECT = "P9: Options Pricing Engine"
SIMPLIFICATIONS = ["No delta hedging simulation", "European options only"]


def black_scholes(
    spot: float, strike: float, tau: float, rate: float,
    sigma: float, dividend: float = 0.0, option_type: str = "call",
) -> float:
    """Analytical Black-Scholes price for a European vanilla."""
    if tau <= 0 or sigma <= 0 or spot <= 0 or strike <= 0:
        intrinsic = max(spot - strike, 0.0) if option_type == "call" else max(strike - spot, 0.0)
        return float(intrinsic)
    d1 = (math.log(spot / strike) + (rate - dividend + 0.5 * sigma ** 2) * tau) / (sigma * math.sqrt(tau))
    d2 = d1 - sigma * math.sqrt(tau)
    if option_type == "call":
        return float(spot * math.exp(-dividend * tau) * norm.cdf(d1) - strike * math.exp(-rate * tau) * norm.cdf(d2))
    return float(strike * math.exp(-rate * tau) * norm.cdf(-d2) - spot * math.exp(-dividend * tau) * norm.cdf(-d1))


def all_greeks(
    spot: float, strike: float, tau: float, rate: float,
    sigma: float, dividend: float = 0.0, option_type: str = "call",
) -> dict[str, float]:
    """Delta, gamma, theta (/365), vega (/0.01 sigma), rho (/0.01 rate)."""
    if tau <= 0 or sigma <= 0 or spot <= 0 or strike <= 0:
        return {k: float("nan") for k in ["delta", "gamma", "theta", "vega", "rho", "spot"]}
    d1 = (math.log(spot / strike) + (rate - dividend + 0.5 * sigma ** 2) * tau) / (sigma * math.sqrt(tau))
    d2 = d1 - sigma * math.sqrt(tau)
    pdf_d1 = norm.pdf(d1)
    disc_r = math.exp(-rate * tau)
    disc_q = math.exp(-dividend * tau)
    gamma = disc_q * pdf_d1 / (spot * sigma * math.sqrt(tau))
    vega = spot * disc_q * pdf_d1 * math.sqrt(tau) / 100.0
    if option_type == "call":
        delta = disc_q * norm.cdf(d1)
        theta = (-spot * disc_q * pdf_d1 * sigma / (2 * math.sqrt(tau))
                 - rate * strike * disc_r * norm.cdf(d2) + dividend * spot * disc_q * norm.cdf(d1)) / 365.0
        rho = strike * tau * disc_r * norm.cdf(d2) / 100.0
    else:
        delta = -disc_q * norm.cdf(-d1)
        theta = (-spot * disc_q * pdf_d1 * sigma / (2 * math.sqrt(tau))
                 + rate * strike * disc_r * norm.cdf(-d2) - dividend * spot * disc_q * norm.cdf(-d1)) / 365.0
        rho = -strike * tau * disc_r * norm.cdf(-d2) / 100.0
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho, "spot": spot}


def implied_vol(
    market_price: float, spot: float, strike: float, tau: float,
    rate: float, dividend: float, option_type: str, solver_cfg: dict[str, Any],
) -> float:
    """Extract implied vol from a market price via Brent's method."""
    if market_price <= 0 or tau <= 0 or spot <= 0 or strike <= 0:
        return float("nan")
    lo, hi = float(solver_cfg["sigma_min"]), float(solver_cfg["sigma_max"])

    def objective(s: float) -> float:
        return black_scholes(spot, strike, tau, rate, s, dividend, option_type) - market_price

    try:
        f_lo = objective(lo)
        f_hi = objective(hi)
        if f_lo * f_hi > 0:
            return float("nan")
        return float(brentq(objective, lo, hi, xtol=float(solver_cfg["tol"]), maxiter=int(solver_cfg["max_iter"])))
    except (ValueError, RuntimeError):
        return float("nan")


def build_iv_surface(chain: pd.DataFrame, spot: float, rate: float, dividend: float, solver_cfg: dict) -> pd.DataFrame:
    """Attach an ``iv`` column to a chain DataFrame for surface rendering."""
    if chain is None or chain.empty:
        return pd.DataFrame()
    out = chain.copy()
    ivs: list[float] = []
    for _, row in out.iterrows():
        mid = 0.5 * (row.get("bid", float("nan")) + row.get("ask", float("nan")))
        if np.isnan(mid) or mid <= 0:
            mid = float(row.get("last", float("nan")))
        tau = float(row.get("tau", float("nan")))
        strike = float(row.get("strike", float("nan")))
        opt_type = str(row.get("type", "call"))
        ivs.append(implied_vol(mid, spot, strike, tau, rate, dividend, opt_type, solver_cfg))
    out["iv"] = ivs
    return out
