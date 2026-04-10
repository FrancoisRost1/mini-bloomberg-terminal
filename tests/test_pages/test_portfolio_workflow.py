"""Integration test: Portfolio BUILD / DECOMPOSE / VALIDATE workflow.

Covered by the spec (Section 12). Runs the three-phase workflow on
synthetic returns and asserts that each phase produces its contract.
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from terminal.adapters.optimizer_adapter import run_optimizer
from terminal.adapters.robustness_adapter import run_robustness
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


def test_phase3_validate_returns_verdict(config, synthetic_portfolio_returns):
    weights = run_optimizer(synthetic_portfolio_returns, config["portfolio"])["weights"]["hrp"]
    w = pd.Series(weights).reindex(synthetic_portfolio_returns.columns).fillna(0.0)
    portfolio_returns = synthetic_portfolio_returns.dot(w)
    rng = np.random.default_rng(7)
    n_trials = 15
    trials = pd.DataFrame(
        rng.normal(0.0004, 0.011, (len(synthetic_portfolio_returns), n_trials)),
        index=synthetic_portfolio_returns.index,
        columns=[f"t{i}" for i in range(n_trials)],
    )
    metrics = pd.Series(rng.normal(1.0, 0.1, n_trials), index=trials.columns)
    report = run_robustness(trials, metrics, portfolio_returns, config["portfolio"]["robustness"])
    assert report["status"] == "success"
    verdicts = set(config["portfolio"]["robustness"]["verdicts"].values())
    assert report["verdict"] in verdicts


def test_full_workflow_is_reproducible(config, synthetic_portfolio_returns):
    first = run_optimizer(synthetic_portfolio_returns, config["portfolio"])["weights"]
    second = run_optimizer(synthetic_portfolio_returns, config["portfolio"])["weights"]
    for method in first:
        for asset in first[method]:
            assert abs(first[method][asset] - second[method][asset]) < 1e-10
