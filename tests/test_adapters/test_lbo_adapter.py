"""Unit tests for the LBO adapter (P1 wrapper)."""

from __future__ import annotations

from terminal.adapters.lbo_adapter import run_base_case, sensitivity_grid


def _base_assumptions(config):
    defaults = dict(config["lbo_quick_calc"]["defaults"])
    defaults["entry_ebitda"] = 100.0
    return defaults


def test_base_case_positive_irr_on_reasonable_inputs(config):
    result = run_base_case(_base_assumptions(config))
    assert result["status"] == "success"
    assert result["sponsor_equity"] > 0
    assert result["entry_ev"] == 100.0 * config["lbo_quick_calc"]["defaults"]["entry_multiple"]
    assert result["irr"] == result["irr"]  # not NaN


def test_base_case_multiple_expansion_boosts_returns(config):
    base = _base_assumptions(config)
    upside = dict(base)
    upside["exit_multiple"] = base["entry_multiple"] + 2.0
    base_result = run_base_case(base)
    up_result = run_base_case(upside)
    assert up_result["irr"] > base_result["irr"]
    assert up_result["moic"] > base_result["moic"]


def test_base_case_debt_paydown_reduces_exit_debt(config):
    result = run_base_case(_base_assumptions(config))
    assert result["exit_debt"] < result["entry_debt"]


def test_sensitivity_grid_monotonic_in_exit_multiple(config):
    assumptions = _base_assumptions(config)
    exits = [6.0, 8.0, 10.0]
    growth = [0.05]
    grid = sensitivity_grid(assumptions, exits, growth)
    assert len(grid) == 1
    row = grid[0]
    assert row[0] < row[1] < row[2]


def test_config_driven_defaults(config):
    defaults = config["lbo_quick_calc"]["defaults"]
    result = run_base_case(_base_assumptions(config))
    assert result["entry_multiple"] == defaults["entry_multiple"]
    assert result["exit_multiple"] == defaults["exit_multiple"]
