"""Integration test: Portfolio BUILD / DECOMPOSE workflow.

Phase 3 VALIDATE was removed from v1 because the original page-level
implementation generated a fake trial matrix by perturbing weights with
Gaussian noise, which produced theatrical PBO verdicts. The robustness
adapter is still tested standalone in test_robustness_adapter.py and
will be re-integrated into Phase 3 in v2 with a real parameter sweep.
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from terminal.adapters.optimizer_adapter import run_optimizer
from terminal.engines.pnl_engine import compute_portfolio_attribution


@pytest.fixture
def synthetic_portfolio_returns():
    rng = np.random.default_rng(42)
    n, k = 600, 5
    data = rng.normal(0.0004, 0.011, (n, k))
    idx = pd.date_range("2022-01-01", periods=n, freq="B")
    return pd.DataFrame(data, index=idx, columns=["SPY", "QQQ", "TLT", "GLD", "EFA"])


def test_phase1_build_produces_weights(config, synthetic_portfolio_returns):
    result = run_optimizer(synthetic_portfolio_returns, config["portfolio"])
    assert result["status"] == "success"
    assert "mean_variance" in result["weights"]
    assert "hrp" in result["weights"]
    for weights in result["weights"].values():
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-4
        assert all(0 - 1e-6 <= w <= 1 + 1e-6 for w in weights.values())


def test_phase2_decompose_attribution(config, synthetic_portfolio_returns):
    weights = run_optimizer(synthetic_portfolio_returns, config["portfolio"])["weights"]["hrp"]
    attribution = compute_portfolio_attribution(weights, synthetic_portfolio_returns)
    assert "portfolio_return" in attribution
    assert "asset_contribution" in attribution
    assert set(attribution["asset_contribution"].keys()) == set(synthetic_portfolio_returns.columns)


# Phase 3 page integration test removed; the page itself no longer
# renders Phase 3. The robustness adapter is still covered by
# tests/test_adapters/test_robustness_adapter.py.


def test_full_workflow_is_reproducible(config, synthetic_portfolio_returns):
    first = run_optimizer(synthetic_portfolio_returns, config["portfolio"])["weights"]
    second = run_optimizer(synthetic_portfolio_returns, config["portfolio"])["weights"]
    for method in first:
        for asset in first[method]:
            assert abs(first[method][asset] - second[method][asset]) < 1e-10
