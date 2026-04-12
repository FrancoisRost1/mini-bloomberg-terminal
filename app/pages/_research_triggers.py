"""Downgrade / Upgrade / Catalyst triggers for the Research page.

Generates 3-4 deterministic bullet points showing what would change
the current rating. Thresholds from config; current values from engines.
"""

from __future__ import annotations

import math
from typing import Any

import streamlit as st

from style_inject import TOKENS

from terminal.utils.density import section_bar


def _safe(val: Any) -> float:
    if val is None:
        return float("nan")
    try:
        return float(val)
    except (TypeError, ValueError):
        return float("nan")


def _tcolor(current: float, threshold: float, breach_above: bool = False) -> str:
    if math.isnan(current):
        return TOKENS["text_muted"]
    if breach_above:
        if current >= threshold:
            return TOKENS["accent_danger"]
        return TOKENS["accent_warning"] if current >= threshold * 0.8 else TOKENS["accent_success"]
    if current <= threshold:
        return TOKENS["accent_danger"]
    return TOKENS["accent_warning"] if current <= threshold * 1.2 else TOKENS["accent_success"]


def _fmt(val: float, pct: bool = False) -> str:
    if math.isnan(val):
        return "n/a"
    return f"{val * 100:+.1f}%" if pct else f"{val:.1f}"


def _t(text: str, current: float, threshold: float, pct: bool = False, breach_above: bool = False) -> dict:
    return {"text": f"{text} (current: {_fmt(current, pct)})", "color": _tcolor(current, threshold, breach_above)}


def _buy_triggers(engines: dict, rec: dict, config: dict) -> list[dict]:
    pe = (engines.get("pe_scoring") or {}).get("per_metric_scores") or {}
    ts = engines.get("tsmom") or {}
    sub = rec.get("sub_scores") or {}
    return [
        _t("EV/EBITDA score drops below 20", _safe(pe.get("ev_ebitda")), 20),
        _t("Momentum reversal: 12-1M return turns negative", _safe(ts.get("twelve_one_return")), 0, pct=True),
        _t("Risk sub-score drops below 35", _safe(sub.get("risk")), 35),
        _t("FCF conversion score collapses below 20", _safe(pe.get("fcf_conversion")), 20),
    ]


def _sell_triggers(engines: dict, rec: dict, config: dict) -> list[dict]:
    ts = engines.get("tsmom") or {}
    sub = rec.get("sub_scores") or {}
    return [
        _t("Valuation sub-score rises above 50", _safe(sub.get("valuation")), 50),
        _t("Momentum turns positive: 12-1M return > 0", _safe(ts.get("twelve_one_return")), 0, pct=True),
        _t("Quality sub-score rises above 50", _safe(sub.get("quality")), 50),
        _t("Risk sub-score rises above 50", _safe(sub.get("risk")), 50),
    ]


def _hold_triggers(engines: dict, rec: dict, config: dict) -> list[dict]:
    sub = rec.get("sub_scores") or {}
    ts = engines.get("tsmom") or {}
    buy_thresh = config.get("research", {}).get("recommendation", {}).get("buy_threshold", 65)
    sig = ts.get("signal", 0)
    return [
        _t(f"Composite crosses {buy_thresh} for upgrade", _safe(rec.get("composite_score")), buy_thresh),
        {"text": f"TSMOM signal confirms direction (current: {sig:+d})",
         "color": TOKENS["accent_success"] if sig > 0 else TOKENS["accent_warning"]},
        _t("Momentum sub-score breaks above 60", _safe(sub.get("momentum")), 60),
        _t("Risk sub-score stabilizes above 50", _safe(sub.get("risk")), 50),
    ]


_TITLE_MAP = {"BUY": "DOWNGRADE TRIGGERS", "SELL": "UPGRADE TRIGGERS",
              "HOLD": "CATALYST WATCH", "INSUFFICIENT_DATA": "CATALYST WATCH"}
_BUILDER_MAP = {"BUY": _buy_triggers, "SELL": _sell_triggers,
                "HOLD": _hold_triggers, "INSUFFICIENT_DATA": _hold_triggers}


def render_triggers(packet: dict[str, Any], config: dict[str, Any]) -> None:
    rec = packet.get("recommendation") or {}
    rating = rec.get("rating", "INSUFFICIENT_DATA")
    engines = packet.get("engines") or {}
    title = _TITLE_MAP.get(rating, "CATALYST WATCH")
    triggers = _BUILDER_MAP.get(rating, _hold_triggers)(engines, rec, config)
    if not triggers:
        return
    st.markdown(section_bar(title, source="local"), unsafe_allow_html=True)
    mono = TOKENS["font_mono"]
    items_html = "".join(
        f'<div style="font-family:{mono};font-size:0.68rem;color:{t["color"]};'
        f'line-height:1.6;padding:0.2rem 0 0.2rem 0.6rem;'
        f'border-left:2px solid {t["color"]};">{t["text"]}</div>'
        for t in triggers
    )
    st.markdown(
        f'<div style="background:{TOKENS["bg_surface"]};border:1px solid {TOKENS["border_subtle"]};'
        f'border-radius:2px;padding:0.5rem 0.7rem;margin:0.15rem 0 0.4rem 0;">'
        f'{items_html}</div>',
        unsafe_allow_html=True,
    )
