"""Unit tests for the optimizer adapter (P8 wrapper)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from terminal.adapters.optimizer_adapter import hrp, ledoit_wolf, mean_variance, run_optimizer


def test_ledoit_wolf_positive_definite(synthetic_returns_matrix):
    cov = ledoit_wolf(synthetic_returns_matrix)
    eigvals = np.linalg.eigvalsh(cov)
    assert np.all(eigvals > -1e-8)


def test_mean_variance_respects_cap(synthetic_returns_matrix):
    sigma = ledoit_wolf(synthetic_returns_matrix)
    mu = synthetic_returns_matrix.mean().values * 252
    weights = mean_variance(mu, sigma, risk_aversion=2.5, weight_cap=0.3)
    assert np.isclose(weights.sum(), 1.0, atol=1e-4)
    assert (weights <= 0.3 + 1e-6).all()
    assert (weights >= -1e-6).all()


def test_hrp_sums_to_one(synthetic_returns_matrix):
    weights = hrp(synthetic_returns_matrix)
    assert np.isclose(weights.sum(), 1.0, atol=1e-6)
    assert (weights >= 0).all()


def test_run_optimizer_returns_all_methods(synthetic_returns_matrix, config):
    result = run_optimizer(synthetic_returns_matrix, config["portfolio"])
    assert "mean_variance" in result["weights"]
    assert "hrp" in result["weights"]
    for method_weights in result["weights"].values():
        assert abs(sum(method_weights.values()) - 1.0) < 1e-4
