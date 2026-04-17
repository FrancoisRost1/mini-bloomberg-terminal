"""Deterministic recommendation engine (from P10).

Turns per-engine sub-scores into a composite score, applies data gates
and hard override rules, and returns a BUY / HOLD / SELL / INSUFFICIENT
verdict plus a confidence grade. The LLM memo, if enabled downstream,
receives this verdict as an immutable constraint -- it may narrate but
may never override.
"""

from __future__ import annotations

from typing import Any


def compute_composite(sub_scores: dict[str, float], weights: dict[str, float]) -> float:
    """Weighted mean of sub-scores in 0..100 space, skipping NaNs."""
    total_weight = 0.0
    total = 0.0
    for key, weight in weights.items():
        value = sub_scores.get(key)
        if value is None:
            continue
        try:
            val = float(value)
        except (TypeError, ValueError):
            continue
        if val != val:  # NaN
            continue
        total += weight * val
        total_weight += weight
    if total_weight == 0:
        return float("nan")
    return total / total_weight


def grade_confidence(confidence: float, grade_thresholds: dict[str, float]) -> str:
    ordered = sorted(grade_thresholds.items(), key=lambda kv: -kv[1])
    for grade, threshold in ordered:
        if confidence >= threshold:
            return grade
    return "F"


def classify(composite: float, thresholds: dict[str, float]) -> str:
    if composite != composite:  # NaN
        return "INSUFFICIENT_DATA"
    if composite >= thresholds["buy_threshold"]:
        return "BUY"
    if composite <= thresholds["sell_threshold"]:
        return "SELL"
    return "HOLD"


def apply_overrides(
    rating: str,
    sub_scores: dict[str, float],
    flags: dict[str, Any],
    overrides_cfg: dict[str, Any],
) -> tuple[str, str | None]:
    """Apply hard override rules. Returns (new_rating, override_reason)."""
    reason: str | None = None
    if overrides_cfg.get("negative_ebitda_downgrade") and flags.get("negative_ebitda"):
        if rating == "BUY":
            rating = "HOLD"
            reason = "negative_ebitda_downgrade"
    return rating, reason


def run_recommendation(
    sub_scores: dict[str, float],
    engine_confidences: dict[str, float],
    flags: dict[str, Any],
    research_cfg: dict[str, Any],
) -> dict[str, Any]:
    """End-to-end recommendation with composite, overrides, and confidence.

    Returned dict carries an immutable ``rating`` plus a ``rule_trace``
    list documenting every decision, which the LLM memo consumes verbatim.
    """
    composite = compute_composite(sub_scores, research_cfg["composite_weights"])
    thresholds = research_cfg["recommendation"]
    valid_engines = sum(1 for v in sub_scores.values() if v == v)
    overall_confidence = (
        sum(engine_confidences.values()) / len(engine_confidences)
        if engine_confidences else 0.0
    )
    rule_trace: list[str] = [f"composite={composite:.2f}", f"valid_engines={valid_engines}"]
    if valid_engines < thresholds["min_valid_engines"]:
        return _insufficient(composite, overall_confidence, rule_trace, research_cfg, "too few valid engines")
    if overall_confidence < thresholds["min_confidence"]:
        return _insufficient(composite, overall_confidence, rule_trace, research_cfg, "low confidence")
    rating = classify(composite, thresholds)
    rating, override_reason = apply_overrides(rating, sub_scores, flags, research_cfg["overrides"])
    if override_reason:
        rule_trace.append(f"override:{override_reason}")
    grade = grade_confidence(overall_confidence, research_cfg["confidence_grades"])
    return {
        "rating": rating,
        "composite_score": composite,
        "sub_scores": sub_scores,
        "confidence": overall_confidence,
        "confidence_grade": grade,
        "override_reason": override_reason,
        "rule_trace": rule_trace,
    }


def _insufficient(
    composite: float,  # noqa: ARG001 - kept for trace-only consumers
    confidence: float,
    trace: list[str],
    cfg: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    """Insufficient-data result. The composite MUST be NaN here.

    The 2026-04-17 audit caught a contradiction where the decision
    banner rendered ``INSUFFICIENT_DATA`` next to ``100.0 / 100 GRADE D``
    because partial sub-scores had still averaged to a real number
    before the data gate short-circuited the classification. A ticker
    that failed the gate does not have a legitimate composite score,
    so we return NaN unconditionally and let the UI format it as n/a.
    """
    trace.append(f"insufficient:{reason}")
    return {
        "rating": "INSUFFICIENT_DATA",
        "composite_score": float("nan"),
        "sub_scores": {},
        "confidence": confidence,
        "confidence_grade": grade_confidence(confidence, cfg["confidence_grades"]),
        "override_reason": None,
        "rule_trace": trace,
    }
