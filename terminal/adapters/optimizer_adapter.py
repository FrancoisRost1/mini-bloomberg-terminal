"""Portfolio optimizer adapter (wraps P8 Portfolio Optimization Engine).

Implements Mean-Variance (long-only with cap) and Hierarchical Risk
Parity. Ledoit-Wolf covariance shrinkage is used by default. Risk Parity
and Black-Litterman are documented future upgrades.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.optimize import minimize
from scipy.spatial.distance import squareform


SOURCE_PROJECT = "P8: Portfolio Optimization Engine"
SIMPLIFICATIONS = ["MV + HRP only (no BL, no Risk Parity)", "Long-only", "Ledoit-Wolf by default"]


def ledoit_wolf(returns: pd.DataFrame) -> np.ndarray:
    """Shrinkage covariance with an identity-scaled target.

    Kept inline so the adapter is self-contained and does not pull in
    sklearn just for the one estimator.
    """
    x = returns.dropna().values
    n, p = x.shape
    if n < 2:
        return np.eye(p)
    mean = x.mean(axis=0)
    centered = x - mean
    sample = np.dot(centered.T, centered) / (n - 1)
    mu = np.trace(sample) / p
    target = mu * np.eye(p)
    frob_diff = np.linalg.norm(sample - target, "fro") ** 2
    if frob_diff == 0:
        return sample
    phi = 0.0
    for i in range(n):
        row = centered[i:i + 1]
        phi += np.linalg.norm(row.T @ row - sample, "fro") ** 2
    phi /= n
    shrinkage = max(0.0, min(1.0, phi / frob_diff))
    return shrinkage * target + (1 - shrinkage) * sample


def mean_variance(
    mu: np.ndarray, sigma: np.ndarray, risk_aversion: float, weight_cap: float,
) -> np.ndarray:
    """Long-only MV with box constraints and a full-investment budget."""
    n = len(mu)
    x0 = np.ones(n) / n

    def neg_utility(w: np.ndarray) -> float:
        return -(float(w @ mu) - 0.5 * risk_aversion * float(w @ sigma @ w))

    bounds = [(0.0, weight_cap) for _ in range(n)]
    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    result = minimize(neg_utility, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    if not result.success:
        return x0
    return result.x


def hrp(returns: pd.DataFrame) -> np.ndarray:
    """Hierarchical Risk Parity weights via recursive bisection."""
    if returns.empty or returns.shape[1] < 2:
        return np.ones(returns.shape[1]) / max(1, returns.shape[1])
    corr = returns.corr().fillna(0.0).values
    dist = np.sqrt(np.clip((1 - corr) / 2.0, 0, 1))
    link = linkage(squareform(dist, checks=False), method="single")
    order = _quasi_diag(link, len(corr))
    cov = returns.cov().values
    weights = np.ones(len(corr))
    _hrp_recurse(weights, cov, order)
    return weights


def _quasi_diag(link: np.ndarray, n: int) -> list[int]:
    clusters = fcluster(link, t=n, criterion="maxclust")
    return list(np.argsort(clusters))


def _hrp_recurse(weights: np.ndarray, cov: np.ndarray, items: list[int]) -> None:
    if len(items) <= 1:
        return
    half = len(items) // 2
    left, right = items[:half], items[half:]
    var_left = _cluster_var(cov, left)
    var_right = _cluster_var(cov, right)
    alpha = 1 - var_left / (var_left + var_right)
    for idx in left:
        weights[idx] *= alpha
    for idx in right:
        weights[idx] *= (1 - alpha)
    _hrp_recurse(weights, cov, left)
    _hrp_recurse(weights, cov, right)


def _cluster_var(cov: np.ndarray, items: list[int]) -> float:
    sub = cov[np.ix_(items, items)]
    inv_diag = 1.0 / np.diag(sub)
    w = inv_diag / inv_diag.sum()
    return float(w @ sub @ w)


def run_optimizer(returns: pd.DataFrame, portfolio_cfg: dict[str, Any]) -> dict[str, Any]:
    """Produce weights for every configured optimizer method."""
    methods = portfolio_cfg["optimizer"]["methods"]
    cap = float(portfolio_cfg["optimizer"]["weight_cap"])
    gamma = float(portfolio_cfg["optimizer"]["risk_aversion"])
    sigma = ledoit_wolf(returns)
    mu = returns.mean().values * 252
    weights: dict[str, dict[str, float]] = {}
    if "mean_variance" in methods:
        w = mean_variance(mu, sigma, gamma, cap)
        weights["mean_variance"] = dict(zip(returns.columns, w))
    if "hrp" in methods:
        w = hrp(returns)
        weights["hrp"] = dict(zip(returns.columns, w))
    return {"status": "success", "source_project": SOURCE_PROJECT, "weights": weights, "cov": sigma}
