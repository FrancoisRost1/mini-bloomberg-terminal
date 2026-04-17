"""Unit tests for the deterministic recommendation engine."""

from __future__ import annotations

import math

from terminal.engines.recommendation_engine import (
    apply_overrides,
    classify,
    compute_composite,
    grade_confidence,
    run_recommendation,
)


def test_compute_composite_weighted_mean():
    scores = {"valuation": 80.0, "quality": 60.0, "momentum": 50.0, "risk": 70.0}
    weights = {"valuation": 0.35, "quality": 0.25, "momentum": 0.20, "risk": 0.20}
    expected = 80 * 0.35 + 60 * 0.25 + 50 * 0.20 + 70 * 0.20
    assert math.isclose(compute_composite(scores, weights), expected, rel_tol=1e-6)


def test_compute_composite_skips_nan():
    scores = {"valuation": 80.0, "quality": float("nan"), "momentum": 50.0, "risk": 70.0}
    weights = {"valuation": 0.35, "quality": 0.25, "momentum": 0.20, "risk": 0.20}
    result = compute_composite(scores, weights)
    assert not math.isnan(result)
    total_weight = 0.35 + 0.20 + 0.20
    assert math.isclose(result, (80 * 0.35 + 50 * 0.20 + 70 * 0.20) / total_weight, rel_tol=1e-6)


def test_classify_thresholds():
    thresholds = {"buy_threshold": 65, "sell_threshold": 35, "min_valid_engines": 2, "min_confidence": 0.4}
    assert classify(70, thresholds) == "BUY"
    assert classify(30, thresholds) == "SELL"
    assert classify(50, thresholds) == "HOLD"
    assert classify(float("nan"), thresholds) == "INSUFFICIENT_DATA"


def test_grade_confidence_ordering(config):
    grades = config["research"]["confidence_grades"]
    assert grade_confidence(0.9, grades) == "A"
    assert grade_confidence(0.65, grades) == "B"
    assert grade_confidence(0.45, grades) == "C"
    assert grade_confidence(0.25, grades) == "D"
    assert grade_confidence(0.1, grades) == "F"


def test_negative_ebitda_override():
    overrides = {"negative_ebitda_downgrade": True}
    rating, reason = apply_overrides("BUY", {}, {"negative_ebitda": True}, overrides)
    assert rating == "HOLD"
    assert reason == "negative_ebitda_downgrade"


def test_run_recommendation_insufficient_data(config):
    result = run_recommendation(
        sub_scores={"valuation": float("nan"), "quality": float("nan"),
                    "momentum": float("nan"), "risk": float("nan")},
        engine_confidences={"pe": 0.9},
        flags={},
        research_cfg=config["research"],
    )
    assert result["rating"] == "INSUFFICIENT_DATA"


def test_insufficient_data_score_is_nan_not_100(config):
    """Regression for the 2026-04-17 audit.

    Before the fix, a partial sub-score set (one engine returning a
    real number, others NaN) flowed into compute_composite and produced
    a non-NaN composite like 100.0. Because the gate short-circuits to
    INSUFFICIENT_DATA before classify(), the UI banner showed
    'INSUFFICIENT_DATA 100.0 / 100 GRADE D', which is a contradiction.
    The gate now returns NaN regardless of partial-score arithmetic.
    """
    result = run_recommendation(
        sub_scores={"valuation": 100.0, "quality": float("nan"),
                    "momentum": float("nan"), "risk": float("nan")},
        engine_confidences={"pe": 0.1},  # below min_confidence to force the gate
        flags={},
        research_cfg=config["research"],
    )
    assert result["rating"] == "INSUFFICIENT_DATA"
    assert math.isnan(result["composite_score"]), (
        f"INSUFFICIENT_DATA must not carry a real composite score; got {result['composite_score']}"
    )


def test_config_mutation_changes_classification(config):
    scores = {"valuation": 66, "quality": 66, "momentum": 66, "risk": 66}
    confidences = {"pe": 0.9, "factor": 0.9, "tsmom": 0.9, "lbo": 0.9}
    flags = {}
    baseline = run_recommendation(scores, confidences, flags, config["research"])
    tweaked = {k: v for k, v in config["research"].items()}
    tweaked["recommendation"] = dict(config["research"]["recommendation"])
    tweaked["recommendation"]["buy_threshold"] = 80
    result = run_recommendation(scores, confidences, flags, tweaked)
    assert baseline["rating"] == "BUY"
    assert result["rating"] == "HOLD"
