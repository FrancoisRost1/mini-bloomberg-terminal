"""Unit tests for the research adapter (P10 wrapper).

The adapter is tested via its sub-score helpers here. Full end-to-end
pipeline coverage lives in ``tests/test_pages/test_research_pipeline.py``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from terminal.adapters._research_sub_scores import (
    build_sub_scores,
    engine_confidences,
    fifty_two_week_position,
    lbo_assumptions_from_fundamentals,
)


def _prices() -> pd.Series:
    idx = pd.date_range("2023-01-01", periods=300, freq="B")
    return pd.Series(np.linspace(100, 150, 300), index=idx, name="close")


def test_build_sub_scores_returns_four_keys():
    pe = {"status": "success", "pe_score": 70, "red_flags": []}
    factor = {"status": "success", "factor_scores": {"quality": 0.6, "momentum": 0.7, "low_vol": 0.5}, "confidence": 0.8}
    tsmom = {"status": "success", "signal": 1}
    lbo = {"status": "success", "irr": 0.18}
    ratios = {"ev_ebitda": 10, "ebitda_margin": 0.25, "fcf_conversion": 0.7, "roic": 0.2, "interest_coverage": 8}
    scores = build_sub_scores(pe, factor, tsmom, lbo, ratios, _prices())
    assert set(scores.keys()) == {"valuation", "quality", "momentum", "risk"}
    for key, val in scores.items():
        assert 0 <= val <= 100, f"{key} out of bounds: {val}"


def test_engine_confidences_zero_on_failed_engine():
    pe = {"status": "failed"}
    factor = {"status": "success", "confidence": 0.9}
    tsmom = {"status": "failed"}
    lbo = {"status": "success"}
    conf = engine_confidences(pe, factor, tsmom, lbo)
    assert conf["pe"] == 0.0
    assert conf["factor"] == 0.9
    assert conf["tsmom"] == 0.0
    assert conf["lbo"] == 0.7


def test_lbo_assumptions_none_when_margin_nan(config):
    class Fake:
        key_ratios = {"ebitda_margin": float("nan")}
        market_cap = 1e9

    assert lbo_assumptions_from_fundamentals(Fake(), config) is None


def test_lbo_assumptions_populated_from_fundamentals(config):
    class Fake:
        key_ratios = {"ebitda_margin": 0.2}
        market_cap = 1e10

    result = lbo_assumptions_from_fundamentals(Fake(), config)
    assert result is not None
    assert result["entry_ebitda"] == 0.2 * 1e10
    assert "entry_multiple" in result  # defaults passed through


def test_fifty_two_week_position_bounds():
    assert 0 <= fifty_two_week_position(_prices()) <= 100
    assert fifty_two_week_position(pd.Series(dtype=float)) != fifty_two_week_position(pd.Series(dtype=float))
