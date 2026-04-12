"""Cross-module signal synthesis for the Research page.

Reads all engine outputs from the research packet and generates a
coherent deterministic narrative. No LLM. Pure string construction
from numerical engine results.
"""

from __future__ import annotations

import math
from typing import Any

import streamlit as st

from style_inject import TOKENS, styled_card

from terminal.utils.chart_helpers import interpretation_callout_html
from terminal.utils.density import section_bar


def _safe(val: Any, default: float = float("nan")) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def _pe_sentence(pe: dict[str, Any]) -> str:
    score = _safe(pe.get("pe_score"))
    if math.isnan(score):
        return ""
    metrics = pe.get("per_metric_scores") or {}
    above = [k.replace("_", " ") for k, v in metrics.items() if _safe(v) >= 50]
    below = [k.replace("_", " ") for k, v in metrics.items() if _safe(v) < 50 and not math.isnan(_safe(v))]
    parts = f"PE screening scores {score:.1f}"
    if above:
        parts += f" with {', '.join(above[:3])} strong"
    if below:
        parts += f" but {', '.join(below[:3])} penalized"
    return parts + "."


def _factor_sentence(fac: dict[str, Any]) -> str:
    comp = _safe(fac.get("composite"))
    if math.isnan(comp):
        return ""
    scores = fac.get("factor_scores") or {}
    mom = _safe(scores.get("momentum"))
    mom_str = f" momentum reads {mom:.2f}" if not math.isnan(mom) else ""
    return f"Factor composite {comp:.2f}{mom_str}."


def _tsmom_sentence(ts: dict[str, Any]) -> str:
    sig = ts.get("signal")
    if sig is None:
        return ""
    ret12 = _safe(ts.get("twelve_one_return"))
    ret_str = f" ({ret12 * 100:+.1f}% trailing)" if not math.isnan(ret12) else ""
    direction = "bullish +1" if sig > 0 else ("bearish -1" if sig < 0 else "flat 0")
    return f"TSMOM signal {direction}{ret_str}."


def _lbo_sentence(lbo: dict[str, Any]) -> str:
    irr = _safe(lbo.get("irr"))
    moic = _safe(lbo.get("moic"))
    if math.isnan(irr):
        return ""
    parts = f"LBO returns {irr * 100:.1f}% IRR"
    if not math.isnan(moic):
        parts += f" at {moic:.2f}x MOIC"
    return parts + " on base case assumptions."


def _consensus_sentence(rec: dict[str, Any]) -> str:
    sub = rec.get("sub_scores") or {}
    if not sub:
        return ""
    bullish = sum(1 for v in sub.values() if _safe(v) >= 60)
    bearish = sum(1 for v in sub.values() if _safe(v) < 40)
    neutral = len(sub) - bullish - bearish
    rating = rec.get("rating", "INSUFFICIENT_DATA")
    composite = _safe(rec.get("composite_score"))
    comp_str = f" at {composite:.1f}" if not math.isnan(composite) else ""
    return (
        f"Consensus across engines: {bullish} of {len(sub)} bullish, "
        f"{neutral} neutral, {bearish} bearish. "
        f"The deterministic rating aggregates to {rating}{comp_str}."
    )


def render_synthesis(packet: dict[str, Any]) -> None:
    engines = packet.get("engines") or {}
    rec = packet.get("recommendation") or {}
    pe = engines.get("pe_scoring") or {}
    fac = engines.get("factor_exposure") or {}
    ts = engines.get("tsmom") or {}
    lbo = engines.get("lbo") or {}

    sentences = [s for s in [
        _pe_sentence(pe) if pe.get("status") == "success" else "",
        _factor_sentence(fac) if fac.get("status") == "success" else "",
        _tsmom_sentence(ts) if ts.get("status") == "success" else "",
        _lbo_sentence(lbo) if lbo.get("status") == "success" else "",
    ] if s]

    if not sentences and not rec.get("sub_scores"):
        return

    observation = " ".join(sentences) if sentences else "No engine signals available."
    consensus = _consensus_sentence(rec)
    rating = rec.get("rating", "INSUFFICIENT_DATA")
    color_map = {"BUY": TOKENS["accent_success"], "HOLD": TOKENS["accent_warning"],
                 "SELL": TOKENS["accent_danger"]}
    accent = color_map.get(rating, TOKENS["accent_primary"])

    st.markdown(section_bar("SIGNAL SYNTHESIS", source="local"), unsafe_allow_html=True)
    styled_card(
        interpretation_callout_html(
            observation=observation,
            interpretation=consensus,
            implication="",
        ),
        accent_color=accent,
    )
