"""PE scoring adapter (wraps P2 PE Target Screener).

Single-ticker scoring: converts the key ratios from a Fundamentals object
into a 0..100 percentile-style score with red flag detection. Used by
the Research pipeline and the Comps workspace.

The scoring bands live in ``config.yaml`` under ``comps.pe_scoring_bands``.
Each entry has ``ideal``, ``penalty``, and ``higher_better``. Bands are
NOT hardcoded -- mutating config.yaml changes the scores, and a config
truthfulness test (``test_pe_scoring_adapter.test_bands_driven_by_config``)
guarantees that.
"""

from __future__ import annotations

from typing import Any


SOURCE_PROJECT = "P2: PE Target Screener"
SIMPLIFICATIONS = ["Single-ticker scoring", "No universe screen", "No Monte Carlo"]


def score_band(value: float, band: dict[str, float]) -> float:
    """Linear-interpolate ``value`` between ``ideal`` (100) and ``penalty`` (0)."""
    if value is None or value != value:
        return float("nan")
    ideal = float(band["ideal"])
    penalty = float(band["penalty"])
    higher_better = bool(band["higher_better"])
    if higher_better:
        if value >= ideal:
            return 100.0
        if value <= penalty:
            return 0.0
        return float(100.0 * (value - penalty) / (ideal - penalty))
    if value <= ideal:
        return 100.0
    if value >= penalty:
        return 0.0
    return float(100.0 * (penalty - value) / (penalty - ideal))


def score_single_ticker(ratios: dict[str, float], bands: dict[str, dict[str, float]]) -> dict[str, Any]:
    """Score a single ticker against the configured bands.

    ``bands`` MUST come from config (``cfg["comps"]["pe_scoring_bands"]``);
    this function takes them as a parameter so the config flows in
    explicitly and config truthfulness tests stay meaningful.
    """
    per_metric: dict[str, float] = {}
    for metric, band in bands.items():
        per_metric[metric] = score_band(ratios.get(metric, float("nan")), band)
    valid = [v for v in per_metric.values() if v == v]
    pe_score = float(sum(valid) / len(valid)) if valid else float("nan")
    red_flags = _detect_red_flags(ratios)
    return {
        "status": "success",
        "source_project": SOURCE_PROJECT,
        "pe_score": pe_score,
        "per_metric_scores": per_metric,
        "red_flags": red_flags,
        "valid_metric_count": len(valid),
    }


def _detect_red_flags(ratios: dict[str, float]) -> list[str]:
    """Hard sanity checks. These are independent of band scoring -- they
    fire on values that signal financial distress regardless of percentile.
    """
    flags: list[str] = []
    ebitda_margin = ratios.get("ebitda_margin")
    if ebitda_margin is not None and ebitda_margin == ebitda_margin and ebitda_margin < 0:
        flags.append("negative_ebitda")
    nd = ratios.get("net_debt_ebitda")
    if nd is not None and nd == nd and nd > 6.0:
        flags.append("extreme_leverage")
    ic = ratios.get("interest_coverage")
    if ic is not None and ic == ic and ic < 1.5:
        flags.append("weak_interest_coverage")
    fcf = ratios.get("fcf_conversion")
    if fcf is not None and fcf == fcf and fcf < 0:
        flags.append("negative_fcf_conversion")
    return flags
