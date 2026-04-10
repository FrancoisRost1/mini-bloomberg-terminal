"""Unit tests for the options adapter (P9 wrapper)."""

from __future__ import annotations

import math

from terminal.adapters.options_adapter import all_greeks, black_scholes, implied_vol


def test_bs_call_put_parity():
    spot, strike, tau, rate, sigma = 100.0, 100.0, 0.5, 0.04, 0.25
    call = black_scholes(spot, strike, tau, rate, sigma, option_type="call")
    put = black_scholes(spot, strike, tau, rate, sigma, option_type="put")
    lhs = call - put
    rhs = spot - strike * math.exp(-rate * tau)
    assert math.isclose(lhs, rhs, rel_tol=1e-6)


def test_call_delta_bounds():
    greeks = all_greeks(100, 100, 0.5, 0.04, 0.25, option_type="call")
    assert 0 < greeks["delta"] < 1
    assert greeks["gamma"] > 0
    assert greeks["vega"] > 0


def test_put_delta_negative():
    greeks = all_greeks(100, 100, 0.5, 0.04, 0.25, option_type="put")
    assert -1 < greeks["delta"] < 0


def test_iv_extraction_round_trip(config):
    true_sigma = 0.35
    price = black_scholes(100, 105, 0.25, 0.05, true_sigma, option_type="call")
    iv = implied_vol(price, 100, 105, 0.25, 0.05, 0.0, "call", config["options_lab"]["iv_solver"])
    assert math.isclose(iv, true_sigma, abs_tol=1e-4)


def test_degenerate_inputs_return_nan():
    greeks = all_greeks(100, 100, 0.0, 0.04, 0.25, option_type="call")
    assert all(v != v for v in greeks.values())
