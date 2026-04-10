"""PE scoring adapter (wraps P2 PE Target Screener).

Single-ticker scoring: converts the key ratios from a Fundamentals object
into a 0..100 percentile-style score with red flag detection. Used by
the Research pipeline and the Comps workspace.
"""

from __future__ import annotations

from typing import Any

SOURCE_PROJECT = "P2: PE Target Screener"
SIMPLIFICATIONS = ["Single-ticker scoring", "No universe screen", "No Monte Carlo"]


# Per-metric ideal bands. Values inside the ideal range score 100, values
# at the penalty edge score 0. Bands mirror the P2 scoring bible.
BANDS: dict[str, dict[str, float]] = {
    "ebitda_margin":   {"ideal": 0.30, "penalty": 0.05, "higher_better": True},
    "fcf_conversion":  {"ideal": 0.90, "penalty": 0.30, "higher_better": True},
    "roic":            {"ideal": 0.25, "penalty": 0.05, "higher_better": True},
    "revenue_growth":  {"ideal": 0.15, "penalty": -0.05, "higher_better": True},
    "ev_ebitda":       {"ideal": 8.0,  "penalty": 18.0,  "higher_better": False},
    "pe_ratio":        {"ideal": 15.0, "penalty": 35.0,  "higher_better": False},
    "net_debt_ebitda": {"ideal": 1.5,  "penalty": 5.0,   "higher_better": False},
}


def _band_score(value: float, band: dict[str, float]) -> float:
    if value is None or value != value:  # NaN
        return float("nan")
    ideal = band["ideal"]
    penalty = band["penalty"]
    if band["higher_better"]:
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


def score_single_ticker(ratios: dict[str, float]) -> dict[str, Any]:
    """Score a single ticker's ratios and return a summary dict.

    Returns both per-metric scores and a simple average aggregate. Red
    flags are triggered by individual metric failures and surfaced so
    the recommendation engine's override rules can consume them.
    """
    per_metric: dict[str, float] = {}
    for metric, band in BANDS.items():
        per_metric[metric] = _band_score(ratios.get(metric, float("nan")), band)
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
