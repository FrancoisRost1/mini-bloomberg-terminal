"""Unit tests for the robustness adapter (P7 wrapper)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from terminal.adapters.robustness_adapter import (
    classify_verdict,
    compute_pbo,
    deflated_sharpe,
    plateau_fraction,
    run_robustness,
)


def _trial_matrix(n_obs=400, n_trials=10, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    data = rng.normal(0.0005, 0.01, (n_obs, n_trials))
    idx = pd.date_range("2022-01-01", periods=n_obs, freq="B")
    return pd.DataFrame(data, index=idx, columns=[f"trial_{i}" for i in range(n_trials)])


def test_pbo_in_unit_interval():
    pbo = compute_pbo(_trial_matrix(), n_blocks=8)
    assert pbo != pbo or 0 <= pbo <= 1  # NaN or in [0, 1]


def test_pbo_nan_on_insufficient_data():
    small = _trial_matrix(n_obs=20, n_trials=5)
    assert compute_pbo(small, n_blocks=16) != compute_pbo(small, n_blocks=16)  # NaN


def test_deflated_sharpe_handles_single_trial():
    rng = np.random.default_rng(1)
    returns = pd.Series(rng.normal(0.001, 0.01, 300))
    # n_trials = 1 is an edge case; with no trials to deflate against,
    # the adapter returns NaN rather than inflating a single-test SR.
    result = deflated_sharpe(returns, n_trials=1)
    assert result != result  # NaN


def test_plateau_fraction_full_equal_matrix():
    metrics = pd.Series([1.0, 1.0, 1.0, 1.0])
    assert plateau_fraction(metrics, tolerance=0.1) == 1.0


def test_plateau_fraction_fragile_when_one_peak():
    metrics = pd.Series([0.1, 0.1, 0.1, 1.0])
    frac = plateau_fraction(metrics, tolerance=0.1)
    assert 0 <= frac <= 1
    assert frac < 0.5


def test_classify_verdict_uses_config_labels(config):
    cfg = config["portfolio"]["robustness"]
    verdict = classify_verdict(pbo=0.1, dsr=0.98, plateau=0.5, robustness_cfg=cfg)
    assert verdict == cfg["verdicts"]["robust"]
    verdict = classify_verdict(pbo=0.6, dsr=0.5, plateau=0.05, robustness_cfg=cfg)
    assert verdict == cfg["verdicts"]["overfit"]
    verdict = classify_verdict(pbo=0.4, dsr=0.8, plateau=0.2, robustness_cfg=cfg)
    assert verdict == cfg["verdicts"]["borderline"]


def test_run_robustness_full_pipeline(config):
    matrix = _trial_matrix()
    metrics = pd.Series(np.random.default_rng(2).normal(1.0, 0.05, matrix.shape[1]), index=matrix.columns)
    report = run_robustness(
        trial_matrix=matrix,
        trial_metrics=metrics,
        selected_returns=matrix.iloc[:, 0],
        robustness_cfg=config["portfolio"]["robustness"],
    )
    assert report["status"] == "success"
    assert "pbo" in report
    assert "deflated_sharpe" in report
    assert "plateau_fraction" in report
    assert "verdict" in report
