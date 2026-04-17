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


def test_option_scenario_long_call_loss_bounded_on_down_move():
    """A long call crashing 20% into deep OTM territory cannot profit.

    This is the P0 regression from the 2026-04-17 terminal audit: the
    delta-gamma Taylor expansion was showing a +6497% P&L when spot
    fell 20% on an ATM call. BS repricing keeps P&L inside the true
    payoff surface. The loss is bounded below by -premium.
    """
    spot, strike = 263.40, 262.50
    tau, rate, sigma = 30 / 365.0, 0.04, 0.25
    grid = np.array([spot * 0.8, spot, spot * 1.2])
    df = compute_option_scenario(
        spot0=spot, strike=strike, tau=tau, rate=rate, sigma=sigma,
        spot_range=grid, option_type="call",
        vol_shift=0.0, time_decay_days=7,
    )
    entry_price = df["value"].iloc[1] - df["pnl"].iloc[1]
    assert df["pnl"].iloc[0] < 0, "long call must lose on -20% spot"
    assert df["pnl"].iloc[0] >= -entry_price - 1e-6, "loss cannot exceed premium"
    assert df["pnl"].iloc[-1] > df["pnl"].iloc[0], "P&L must be monotonic in spot"
    assert df["pnl"].iloc[-1] > 0, "long call must gain on +20% spot"


def test_option_scenario_long_put_gains_on_down_move():
    """Dual: long put must profit on spot crash and lose on spot rally."""
    spot, strike = 100.0, 100.0
    tau, rate, sigma = 30 / 365.0, 0.04, 0.25
    grid = np.array([80.0, 100.0, 120.0])
    df = compute_option_scenario(
        spot0=spot, strike=strike, tau=tau, rate=rate, sigma=sigma,
        spot_range=grid, option_type="put",
        vol_shift=0.0, time_decay_days=7,
    )
    assert df["pnl"].iloc[0] > 0, "long put must gain on -20% spot"
    assert df["pnl"].iloc[-1] < 0, "long put must lose on +20% spot"


def test_option_scenario_returns_value_column():
    """Contract: scenario frame must include both the repriced value and P&L."""
    grid = np.array([95.0, 100.0, 105.0])
    df = compute_option_scenario(
        spot0=100.0, strike=100.0, tau=30 / 365.0, rate=0.04, sigma=0.20,
        spot_range=grid, option_type="call",
    )
    assert {"value", "pnl"}.issubset(df.columns)
    assert (df["value"] >= 0).all(), "BS price is non-negative"


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
