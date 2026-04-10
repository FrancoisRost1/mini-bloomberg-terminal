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


def _fake_fundamentals(margin: float = 0.2, revenue: float = 1.0e9):
    """Builds a Fundamentals stand-in with a real income_statement DataFrame."""
    income = pd.DataFrame(
        {"totalRevenue": [revenue * 0.9, revenue]},
        index=pd.to_datetime(["2022-12-31", "2023-12-31"]),
    )

    class Fake:
        key_ratios = {"ebitda_margin": margin}
        market_cap = 1e10
        income_statement = income

    return Fake()


def test_build_sub_scores_returns_four_keys():
    pe = {"status": "success", "pe_score": 70, "red_flags": []}
    factor = {"status": "success", "factor_scores": {"quality": 0.6, "momentum": 0.7, "low_vol": 0.5}, "confidence": 0.8}
    tsmom = {"status": "success", "signal": 1}
    lbo = {"status": "success", "irr": 0.18}
    ratios = {"ev_ebitda": 10, "ebitda_margin": 0.25, "fcf_conversion": 0.7, "roe": 0.2, "interest_coverage": 8}
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
        income_statement = pd.DataFrame()

    assert lbo_assumptions_from_fundamentals(Fake(), config) is None


def test_lbo_assumptions_uses_revenue_not_market_cap(config):
    """Bug 4 regression: EBITDA must be revenue * margin, NOT market_cap * margin."""
    fake = _fake_fundamentals(margin=0.2, revenue=2.0e9)
    result = lbo_assumptions_from_fundamentals(fake, config)
    assert result is not None
    assert result["entry_ebitda"] == 0.2 * 2.0e9
    # Market cap is 1e10; the old buggy code would have produced 0.2 * 1e10 = 2e9.
    # The correct code produces 0.2 * 2e9 = 4e8. Verify it is NOT the buggy value.
    assert result["entry_ebitda"] != 0.2 * 1e10


def test_lbo_assumptions_none_when_no_income_statement(config):
    class Fake:
        key_ratios = {"ebitda_margin": 0.2}
        market_cap = 1e10
        income_statement = pd.DataFrame()

    assert lbo_assumptions_from_fundamentals(Fake(), config) is None


def test_fifty_two_week_position_bounds():
    assert 0 <= fifty_two_week_position(_prices()) <= 100
    assert fifty_two_week_position(pd.Series(dtype=float)) != fifty_two_week_position(pd.Series(dtype=float))
