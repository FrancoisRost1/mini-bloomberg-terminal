"""Decision summary banner. First element on the Research page.

Answers 'so what?' in a single full-width card with three columns:
  Left   -- rating, composite score, confidence grade
  Middle -- one-line deterministic thesis from sub-score rankings
  Right  -- key risk derived from the weakest sub-score category
"""

from __future__ import annotations

import math
from typing import Any

import streamlit as st

from style_inject import TOKENS


_RATING_COLORS: dict[str, str] = {
    "BUY": TOKENS["accent_success"],
    "HOLD": TOKENS["accent_warning"],
    "SELL": TOKENS["accent_danger"],
    "INSUFFICIENT_DATA": TOKENS["text_muted"],
}

_CATEGORY_LABELS: dict[str, str] = {
    "valuation": "valuation",
    "quality": "quality",
    "momentum": "momentum",
    "risk": "risk",
}


def _ranked_scores(sub: dict[str, float]) -> list[tuple[str, float]]:
    """Return sub-scores sorted best to worst, skipping NaN."""
    pairs = []
    for k, v in sub.items():
        if k.startswith("_") or v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if math.isnan(fv):
            continue
        pairs.append((k, fv))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs


def _momentum_direction(sub: dict[str, float]) -> str:
    mom = sub.get("momentum")
    if mom is None or (isinstance(mom, float) and math.isnan(mom)):
        return "Neutral"
    return "Positive" if float(mom) >= 50 else "Negative"


def _build_thesis(rating: str, ranked: list[tuple[str, float]]) -> str:
    if not ranked:
        return "Insufficient data for a deterministic thesis."
    strongest = _CATEGORY_LABELS.get(ranked[0][0], ranked[0][0])
    weakest = _CATEGORY_LABELS.get(ranked[-1][0], ranked[-1][0])
    mom_dir = _momentum_direction(dict(ranked))
    if rating == "BUY":
        return (f"Strong {strongest} offset by {weakest}. "
                f"{mom_dir} momentum supports entry.")
    if rating == "SELL":
        return (f"{weakest.capitalize()} dominates. "
                f"{strongest.capitalize()} insufficient to offset downside risk.")
    if rating == "HOLD":
        return (f"Mixed signals. {strongest.capitalize()} positive "
                f"but {weakest} flags caution. Wait for catalyst.")
    return "Insufficient data for a deterministic thesis."


def _build_positioning(rating: str, ranked: list[tuple[str, float]]) -> str:
    """One-line trade recommendation from rating + sub-score context."""
    if rating == "HOLD":
        return "No new positioning. Monitor catalyst triggers."
    if rating == "SELL":
        risk_val = dict(ranked).get("risk", 50) if ranked else 50
        if risk_val < 30:
            return "Put spread or reduce exposure."
        return "Underweight or exit. Risk outweighs reward."
    if rating == "BUY":
        scores = dict(ranked)
        risk_val = scores.get("risk", 50)
        val_val = scores.get("valuation", 50)
        if risk_val < 35:
            return "Long equity but reduce size due to macro regime."
        if val_val < 30:
            return "Call spread preferred given stretched valuation."
        return "Long equity, 3-6 month horizon."
    return ""


def _build_key_risk(ranked: list[tuple[str, float]]) -> tuple[str, str]:
    """Return (risk label, color). Weakest sub-score drives the risk."""
    if not ranked:
        return "No data", TOKENS["text_muted"]
    name, val = ranked[-1]
    label = _CATEGORY_LABELS.get(name, name).upper()
    color = TOKENS["accent_danger"] if val < 40 else TOKENS["accent_warning"]
    return f"{label} ({val:.0f}/100)", color


def render_decision_banner(packet: dict[str, Any]) -> None:
    rec = packet.get("recommendation") or {}
    rating = rec.get("rating", "INSUFFICIENT_DATA")
    composite = rec.get("composite_score", float("nan"))
    grade = rec.get("confidence_grade", "F")
    sub = rec.get("sub_scores") or {}
    ranked = _ranked_scores(sub)
    accent = _RATING_COLORS.get(rating, TOKENS["text_muted"])
    thesis = _build_thesis(rating, ranked)
    positioning = _build_positioning(rating, ranked)
    risk_label, risk_color = _build_key_risk(ranked)
    comp_str = f"{composite:.1f}" if composite == composite else "n/a"
    mono = TOKENS["font_mono"]
    bg = TOKENS["bg_surface"]
    border = TOKENS["border_default"]
    muted = TOKENS["text_muted"]
    primary = TOKENS["text_primary"]
    html = (
        f'<div style="background:{bg};border:1px solid {border};'
        f'border-left:4px solid {accent};border-radius:2px;'
        f'padding:0.7rem 1rem;margin:0.3rem 0 0.6rem 0;'
        f'display:grid;grid-template-columns:28% 44% 28%;'
        f'align-items:center;gap:0.8rem;">'
        # Left column: rating + composite + grade
        f'<div style="text-align:left;">'
        f'<div style="font-family:{mono};font-size:1.5rem;font-weight:900;'
        f'color:{accent};letter-spacing:0.08em;line-height:1.2;">{rating}</div>'
        f'<div style="font-family:{mono};font-size:0.82rem;font-weight:600;'
        f'color:{primary};margin-top:0.15rem;">{comp_str} / 100</div>'
        f'<div style="font-family:{mono};font-size:0.62rem;font-weight:600;'
        f'color:{muted};letter-spacing:0.1em;margin-top:0.1rem;">GRADE {grade}</div>'
        f'</div>'
        # Middle column: thesis + positioning
        f'<div style="padding:0 0.3rem;">'
        f'<div style="font-family:{mono};font-size:0.72rem;font-weight:500;'
        f'color:{primary};line-height:1.55;">{thesis}</div>'
        f'<div style="font-family:{mono};font-size:0.6rem;font-weight:500;'
        f'color:{muted};line-height:1.4;margin-top:0.25rem;">{positioning}</div>'
        f'</div>'
        # Right column: key risk
        f'<div style="text-align:right;">'
        f'<div style="font-family:{mono};font-size:0.56rem;font-weight:700;'
        f'color:{muted};letter-spacing:0.12em;margin-bottom:0.15rem;">KEY RISK</div>'
        f'<div style="font-family:{mono};font-size:0.78rem;font-weight:700;'
        f'color:{risk_color};line-height:1.3;">{risk_label}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
