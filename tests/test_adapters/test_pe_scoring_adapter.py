"""Unit tests for the PE scoring adapter (P2 wrapper)."""

from __future__ import annotations

import math

from terminal.adapters.pe_scoring_adapter import score_single_ticker


def test_ideal_ratios_score_high():
    ratios = {
        "ebitda_margin": 0.35,
        "fcf_conversion": 0.95,
        "roic": 0.30,
        "revenue_growth": 0.18,
        "ev_ebitda": 7.0,
        "pe_ratio": 14.0,
        "net_debt_ebitda": 1.0,
    }
    result = score_single_ticker(ratios)
    assert result["pe_score"] == 100.0
    assert result["red_flags"] == []


def test_penalty_ratios_score_low():
    ratios = {
        "ebitda_margin": 0.02,
        "fcf_conversion": 0.1,
        "roic": 0.02,
        "revenue_growth": -0.10,
        "ev_ebitda": 22.0,
        "pe_ratio": 45.0,
        "net_debt_ebitda": 7.0,
    }
    result = score_single_ticker(ratios)
    assert result["pe_score"] < 20.0


def test_red_flag_negative_ebitda():
    ratios = {"ebitda_margin": -0.05, "ev_ebitda": 10, "pe_ratio": 20, "roic": 0.1,
              "revenue_growth": 0.05, "fcf_conversion": 0.5, "net_debt_ebitda": 2.0}
    result = score_single_ticker(ratios)
    assert "negative_ebitda" in result["red_flags"]


def test_nan_skipped():
    ratios = {"ebitda_margin": 0.25, "fcf_conversion": 0.8, "roic": 0.2,
              "revenue_growth": float("nan"), "ev_ebitda": 10, "pe_ratio": 20, "net_debt_ebitda": 2.0}
    result = score_single_ticker(ratios)
    assert result["pe_score"] == result["pe_score"]
    assert result["valid_metric_count"] == 6
