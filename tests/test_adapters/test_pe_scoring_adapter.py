"""Unit tests for the PE scoring adapter (P2 wrapper)."""

from __future__ import annotations

import copy

from terminal.adapters.pe_scoring_adapter import score_single_ticker


def _bands(config):
    return config["comps"]["pe_scoring_bands"]


def test_ideal_ratios_score_high(config):
    ratios = {
        "ebitda_margin": 0.35,
        "fcf_conversion": 0.95,
        "roe": 0.30,
        "revenue_growth": 0.18,
        "ev_ebitda": 7.0,
        "pe_ratio": 14.0,
        "net_debt_ebitda": 1.0,
    }
    result = score_single_ticker(ratios, _bands(config))
    assert result["pe_score"] == 100.0
    assert result["red_flags"] == []


def test_penalty_ratios_score_low(config):
    ratios = {
        "ebitda_margin": 0.02,
        "fcf_conversion": 0.1,
        "roe": 0.02,
        "revenue_growth": -0.10,
        "ev_ebitda": 22.0,
        "pe_ratio": 45.0,
        "net_debt_ebitda": 7.0,
    }
    result = score_single_ticker(ratios, _bands(config))
    assert result["pe_score"] < 20.0


def test_red_flag_negative_ebitda(config):
    ratios = {"ebitda_margin": -0.05, "ev_ebitda": 10, "pe_ratio": 20, "roe": 0.1,
              "revenue_growth": 0.05, "fcf_conversion": 0.5, "net_debt_ebitda": 2.0}
    result = score_single_ticker(ratios, _bands(config))
    assert "negative_ebitda" in result["red_flags"]


def test_red_flag_weak_interest_coverage(config):
    """Bug 18 regression: interest_coverage red flag must fire when coverage < 1.5."""
    ratios = {"ebitda_margin": 0.2, "fcf_conversion": 0.5, "roe": 0.1,
              "ev_ebitda": 10, "pe_ratio": 20, "net_debt_ebitda": 2.0,
              "interest_coverage": 1.0}
    result = score_single_ticker(ratios, _bands(config))
    assert "weak_interest_coverage" in result["red_flags"]


def test_nan_skipped(config):
    ratios = {"ebitda_margin": 0.25, "fcf_conversion": 0.8, "roe": 0.2,
              "revenue_growth": float("nan"), "ev_ebitda": 10, "pe_ratio": 20, "net_debt_ebitda": 2.0}
    result = score_single_ticker(ratios, _bands(config))
    assert result["pe_score"] == result["pe_score"]
    assert result["valid_metric_count"] == 6


def test_bands_driven_by_config(config):
    """Bug 16 regression: scoring must follow config bands, not hardcoded constants.

    Mutating the ``ebitda_margin`` ideal value MUST change the score for
    a borderline input. If this test ever fails, the BANDS dict has been
    re-introduced into code somewhere.
    """
    ratios = {"ebitda_margin": 0.20, "fcf_conversion": 0.95, "roe": 0.25,
              "revenue_growth": 0.15, "ev_ebitda": 8.0, "pe_ratio": 15.0,
              "net_debt_ebitda": 1.5}
    baseline = score_single_ticker(ratios, _bands(config))
    tweaked_bands = copy.deepcopy(_bands(config))
    tweaked_bands["ebitda_margin"]["ideal"] = 0.20  # input now hits ideal exactly
    tweaked = score_single_ticker(ratios, tweaked_bands)
    assert tweaked["pe_score"] > baseline["pe_score"]
