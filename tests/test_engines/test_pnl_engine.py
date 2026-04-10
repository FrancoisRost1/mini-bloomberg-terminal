"""Unit tests for the P&L interpretation layer."""

from __future__ import annotations

import numpy as np

from terminal.engines.pnl_engine import (
    compute_lbo_equity_bridge,
    compute_option_payoff,
    compute_option_scenario,
    compute_scenario_payoffs,
)


def test_option_payoff_call_itm_increases():
    df = compute_option_payoff(spot=100, strike=100, premium=5, option_type="call", points=50)
    assert df["pnl"].iloc[-1] > df["pnl"].iloc[0]
    # At strike the intrinsic is 0 so pnl equals -premium
    mid = df.iloc[len(df) // 2]
    assert mid["intrinsic"] >= 0


def test_option_payoff_put_otm_decreases():
    df = compute_option_payoff(spot=100, strike=100, premium=5, option_type="put", points=50)
    assert df["pnl"].iloc[0] > df["pnl"].iloc[-1]


def test_option_scenario_linear_in_delta():
    greeks = {"spot": 100, "delta": 0.5, "gamma": 0, "vega": 0, "theta": 0}
    grid = np.array([90, 100, 110])
    df = compute_option_scenario(greeks, grid)
    assert np.isclose(df["pnl"].iloc[0], 0.5 * (90 - 100))
    assert np.isclose(df["pnl"].iloc[-1], 0.5 * (110 - 100))


def test_lbo_equity_bridge_sums_correctly():
    snap = {
        "entry_ebitda": 100, "exit_ebitda": 120,
        "entry_multiple": 8, "exit_multiple": 9,
        "entry_debt": 300, "exit_debt": 200,
        "fees": 20,
    }
    bridge = compute_lbo_equity_bridge(snap)
    # ebitda_growth = (120-100)*8 = 160
    # multiple_change = 120*(9-8) = 120
    # debt_paydown = 100
    # fees_drag = -20
    assert np.isclose(bridge["ebitda_growth"], 160)
    assert np.isclose(bridge["multiple_expansion"], 120)
    assert np.isclose(bridge["debt_paydown"], 100)
    assert np.isclose(bridge["fees_drag"], -20)
    assert np.isclose(bridge["total_value_creation"], 360)


def test_scenario_payoffs_match_config_shape(config):
    scenarios = config["pnl"]["scenarios"]
    payoffs = compute_scenario_payoffs({"spot": 100, "shares": 10}, scenarios)
    assert len(payoffs) == len(scenarios)
    labels = {p["scenario"] for p in payoffs}
    assert labels == set(scenarios.keys())
