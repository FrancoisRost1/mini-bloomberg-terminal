"""Robustness adapter (wraps P7 Strategy Robustness Lab).

Computes PBO (Probability of Backtest Overfitting via CSCV), deflated
Sharpe, and parameter plateau fraction given a trial matrix. Consumes
the matrix shape ``(T observations x N trials)`` with daily returns.
"""

from __future__ import annotations

import math
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm


SOURCE_PROJECT = "P7: Strategy Robustness Lab"
SIMPLIFICATIONS = ["Runs on provided trial matrix", "No trial generation", "Fewer combinations for speed"]


def compute_pbo(trial_matrix: pd.DataFrame, n_blocks: int = 16, max_combinations: int = 500) -> float:
    """Probability of Backtest Overfitting via Combinatorially Symmetric Cross Validation."""
    if trial_matrix is None or trial_matrix.empty or trial_matrix.shape[0] < n_blocks * 2:
        return float("nan")
    if n_blocks % 2 != 0:
        n_blocks += 1
    T = trial_matrix.shape[0]
    block_size = T // n_blocks
    blocks = [trial_matrix.iloc[i * block_size:(i + 1) * block_size] for i in range(n_blocks)]
    half = n_blocks // 2
    block_indices = list(range(n_blocks))
    combos = list(combinations(block_indices, half))
    if len(combos) > max_combinations:
        step = len(combos) // max_combinations
        combos = combos[::max(1, step)]
    n_trials = trial_matrix.shape[1]
    logits: list[float] = []
    for is_blocks in combos:
        oos_blocks = [i for i in block_indices if i not in is_blocks]
        is_data = pd.concat([blocks[i] for i in is_blocks])
        oos_data = pd.concat([blocks[i] for i in oos_blocks])
        is_sharpe = _sharpe(is_data)
        oos_sharpe = _sharpe(oos_data)
        is_best = int(np.argmax(is_sharpe))
        oos_rank = (oos_sharpe < oos_sharpe.iloc[is_best]).sum() / max(1, n_trials - 1)
        rel = max(1e-6, min(1 - 1e-6, oos_rank))
        logits.append(math.log(rel / (1 - rel)))
    return float(np.mean([1.0 if x > 0 else 0.0 for x in logits]))


def deflated_sharpe(returns: pd.Series, n_trials: int) -> float:
    """Bailey & Lopez de Prado Deflated Sharpe probability."""
    if returns is None or returns.empty or n_trials <= 1:
        return float("nan")
    sr = _sharpe_single(returns)
    if np.isnan(sr):
        return float("nan")
    skew = float(returns.skew())
    kurt = float(returns.kurtosis()) + 3.0
    t = len(returns)
    var_sr = (1 + 0.5 * sr ** 2 - skew * sr + ((kurt - 3) / 4) * sr ** 2) / max(1, t - 1)
    gamma = 0.5772
    sr0 = math.sqrt(max(var_sr, 0)) * ((1 - gamma) * norm.ppf(1 - 1 / n_trials) + gamma * norm.ppf(1 - 1 / (n_trials * math.e)))
    denom = math.sqrt(max(var_sr, 1e-12))
    return float(norm.cdf((sr - sr0) / denom))


def plateau_fraction(metrics: pd.Series, tolerance: float) -> float:
    """Fraction of parameter cells within ``tolerance`` of the best value."""
    if metrics is None or metrics.empty:
        return float("nan")
    best = metrics.max()
    if np.isnan(best) or best <= 0:
        return float("nan")
    threshold = best * (1 - tolerance)
    return float((metrics >= threshold).mean())


def classify_verdict(pbo: float, dsr: float, plateau: float, robustness_cfg: dict[str, Any]) -> str:
    verdicts = robustness_cfg["verdicts"]
    if np.isnan(pbo):
        return verdicts["borderline"]
    if pbo < robustness_cfg["pbo_threshold_robust"]:
        if not np.isnan(dsr) and dsr >= robustness_cfg["dsr_threshold"] and not np.isnan(plateau) and plateau >= robustness_cfg["plateau_stable"]:
            return verdicts["robust"]
        return verdicts["likely_robust"]
    if pbo > robustness_cfg["pbo_threshold_overfit"]:
        if (not np.isnan(dsr) and dsr < robustness_cfg["dsr_threshold"]
                and not np.isnan(plateau) and plateau < robustness_cfg["plateau_fragile"]):
            return verdicts["overfit"]
        return verdicts["likely_overfit"]
    return verdicts["borderline"]


def run_robustness(
    trial_matrix: pd.DataFrame,
    trial_metrics: pd.Series,
    selected_returns: pd.Series,
    robustness_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Entry point used by the Portfolio workspace Phase 3."""
    pbo = compute_pbo(trial_matrix, int(robustness_cfg["cscv_blocks"]))
    dsr = deflated_sharpe(selected_returns, n_trials=max(1, trial_matrix.shape[1]))
    plateau = plateau_fraction(trial_metrics, float(robustness_cfg["plateau_tolerance"]))
    verdict = classify_verdict(pbo, dsr, plateau, robustness_cfg)
    return {
        "status": "success",
        "source_project": SOURCE_PROJECT,
        "pbo": pbo,
        "deflated_sharpe": dsr,
        "plateau_fraction": plateau,
        "verdict": verdict,
    }


def _sharpe(df: pd.DataFrame) -> pd.Series:
    mu = df.mean()
    sd = df.std().replace(0, np.nan)
    return (mu / sd) * math.sqrt(252)


def _sharpe_single(series: pd.Series) -> float:
    sd = series.std()
    if sd == 0 or np.isnan(sd):
        return float("nan")
    return float((series.mean() / sd) * math.sqrt(252))
