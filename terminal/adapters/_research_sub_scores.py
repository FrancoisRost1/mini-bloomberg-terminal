"""Sub-score blending helpers for the research adapter.

Pure functions only -- no adapter calls, no data manager access. Split
out of ``research_adapter.py`` for the line-budget rule.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def build_sub_scores(
    pe: dict[str, Any],
    factor: dict[str, Any],
    tsmom: dict[str, Any],
    lbo: dict[str, Any],
    ratios: dict[str, float],
    prices: pd.Series,
) -> dict[str, float]:
    """Blend per-engine outputs into the four composite sub-scores.

    Weights are held inline intentionally -- they mirror the
    ``research.*_weights`` blocks in config.yaml and the recommendation
    engine re-blends the sub-scores with the top-level composite weights.
    """
    factor_scores = factor.get("factor_scores", {}) if factor.get("status") == "success" else {}
    pe_score = pe.get("pe_score", float("nan"))
    lbo_irr = lbo.get("irr", float("nan")) if lbo.get("status") == "success" else float("nan")
    ev_ebitda = ratios.get("ev_ebitda", float("nan"))
    valuation = _blend({
        "pe": (pe_score, 0.5),
        "lbo": (_scale_irr(lbo_irr), 0.3),
        "ev": (_scale_inverse(ev_ebitda, target=10.0), 0.2),
    })
    quality = _blend({
        "factor_q": (_factor_to_100(factor_scores.get("quality")), 0.4),
        "margin": (_scale_margin(ratios.get("ebitda_margin")), 0.2),
        "fcf": (_scale_margin(ratios.get("fcf_conversion")), 0.2),
        "roe": (_scale_margin(ratios.get("roe")), 0.2),
    })
    tsmom_val = (50 + 50 * tsmom.get("signal", 0)) if tsmom.get("status") == "success" else float("nan")
    momentum = _blend({
        "factor_m": (_factor_to_100(factor_scores.get("momentum")), 0.5),
        "tsmom": (tsmom_val, 0.3),
        "52w": (fifty_two_week_position(prices), 0.2),
    })
    risk = _blend({
        "lowvol": (_factor_to_100(factor_scores.get("low_vol")), 0.4),
        "red_flag": (100 - 25 * len(pe.get("red_flags", [])), 0.3),
        "coverage": (_scale_coverage(ratios.get("interest_coverage")), 0.3),
    })
    return {"valuation": valuation, "quality": quality, "momentum": momentum, "risk": risk}


def engine_confidences(
    pe: dict[str, Any],
    factor: dict[str, Any],
    tsmom: dict[str, Any],
    lbo: dict[str, Any],
) -> dict[str, float]:
    """Per-engine confidence snapshot fed into the recommendation engine."""
    return {
        "pe": 0.8 if pe.get("status") == "success" else 0.0,
        "factor": float(factor.get("confidence", 0.5)) if factor.get("status") == "success" else 0.0,
        "tsmom": 0.7 if tsmom.get("status") == "success" else 0.0,
        "lbo": 0.7 if lbo.get("status") == "success" else 0.0,
    }


def lbo_assumptions_from_fundamentals(fundamentals, config: dict[str, Any]) -> dict[str, Any] | None:
    """Map live fundamentals onto the LBO quick-calc defaults.

    EBITDA is resolved from ``income.ebitda`` -> operating +
    depreciation -> revenue * margin. FMP uses ``revenue``, yfinance
    uses ``totalRevenue``; both are probed. Returns None when no
    path yields a positive EBITDA.
    """
    defaults = dict(config["lbo_quick_calc"]["defaults"])
    income = getattr(fundamentals, "income_statement", None)
    ratios = getattr(fundamentals, "key_ratios", {}) or {}
    if income is None or getattr(income, "empty", True):
        return None
    ebitda = float("nan")
    if "ebitda" in income.columns:
        s = income["ebitda"].dropna()
        if not s.empty and float(s.iloc[-1]) > 0:
            ebitda = float(s.iloc[-1])
    if ebitda != ebitda:
        op = income.get("operatingIncome", pd.Series(dtype=float)).dropna()
        da = income.get("depreciationAndAmortization", pd.Series(dtype=float)).dropna()
        if not op.empty and not da.empty:
            cand = float(op.iloc[-1]) + float(da.iloc[-1])
            if cand > 0:
                ebitda = cand
    if ebitda != ebitda:
        margin = float(ratios.get("ebitda_margin", float("nan")))
        revenue = float("nan")
        for col in ("revenue", "totalRevenue"):
            if col in income.columns:
                rev_series = income[col].dropna()
                if not rev_series.empty:
                    revenue = float(rev_series.iloc[-1])
                    break
        if margin == margin and margin > 0 and revenue == revenue and revenue > 0:
            ebitda = revenue * margin
    if ebitda != ebitda or ebitda <= 0:
        return None
    defaults["entry_ebitda"] = float(ebitda)
    return defaults


def fifty_two_week_position(prices: pd.Series) -> float:
    """Percentile position of the last close in the trailing 52w range."""
    if prices is None or prices.empty:
        return float("nan")
    window = prices.tail(252)
    hi, lo = window.max(), window.min()
    if hi == lo:
        return 50.0
    return float((window.iloc[-1] - lo) / (hi - lo) * 100)


def _blend(items: dict[str, tuple[float, float]]) -> float:
    total_w = 0.0
    total = 0.0
    for _, (val, w) in items.items():
        if val is None or val != val:
            continue
        total += val * w
        total_w += w
    return total / total_w if total_w else float("nan")


def _scale_irr(irr: float) -> float:
    if irr is None or irr != irr:
        return float("nan")
    return float(max(0.0, min(100.0, 50 + 200 * irr)))


def _scale_inverse(value: float, target: float) -> float:
    if value is None or value != value or value <= 0:
        return float("nan")
    return float(max(0.0, min(100.0, 100 * target / value)))


def _scale_margin(value: float) -> float:
    if value is None or value != value:
        return float("nan")
    return float(max(0.0, min(100.0, 200 * value)))


def _scale_coverage(value: float) -> float:
    if value is None or value != value:
        return float("nan")
    return float(max(0.0, min(100.0, value * 10)))


def _factor_to_100(value: float | None) -> float:
    if value is None or value != value:
        return float("nan")
    return float(max(0.0, min(100.0, value * 100)))
