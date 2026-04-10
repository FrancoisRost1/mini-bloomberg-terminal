"""Bloomberg density primitives.

Project specific helpers beyond the canonical style_inject. Exposes
ticker_tape, dense_kpi_row, section_bar, period_returns_tape,
signed_color, mono_inline. Pandas Styler helpers for directional
coloring live in dataframe_styling.py and are re exported here.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from style_inject import TOKENS

from .dataframe_styling import colored_dataframe  # noqa: F401  re export


def signed_color(value: Any) -> str:
    if value is None:
        return TOKENS["text_muted"]
    try:
        v = float(value)
    except (TypeError, ValueError):
        return TOKENS["text_muted"]
    if math.isnan(v) or v == 0:
        return TOKENS["text_muted"]
    return TOKENS["accent_success"] if v > 0 else TOKENS["accent_danger"]


def mono_inline(text: str, color: str | None = None, weight: int = 500) -> str:
    color_css = color or TOKENS["text_primary"]
    return (
        f'<span style="font-family:{TOKENS["font_mono"]};color:{color_css};'
        f'font-weight:{weight};font-size:0.72rem;letter-spacing:0;">{text}</span>'
    )


def ticker_tape(items: list[dict[str, Any]]) -> str:
    cells: list[str] = []
    for item in items:
        label = item.get("label", "")
        value = item.get("value", "n/a")
        delta = item.get("delta", "")
        delta_color = item.get("delta_color") or TOKENS["text_muted"]
        delta_html = (
            f'<span style="color:{delta_color};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.65rem;font-weight:500;margin-left:0.3rem;">{delta}</span>'
            if delta else ""
        )
        cells.append(
            f'<span style="display:inline-flex;align-items:baseline;gap:0.25rem;'
            f'padding:0 0.55rem;border-right:1px solid {TOKENS["border_subtle"]};">'
            f'<span style="color:{TOKENS["text_muted"]};font-family:{TOKENS["font_body"]};'
            f'font-size:0.55rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">{label}</span>'
            f'<span style="color:{TOKENS["text_primary"]};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.72rem;font-weight:600;">{value}</span>{delta_html}</span>'
        )
    return (
        f'<div style="background:{TOKENS["bg_surface"]};'
        f'border:1px solid {TOKENS["border_default"]};border-radius:{TOKENS["radius_sm"]};'
        f'padding:0.3rem 0.15rem;overflow-x:auto;white-space:nowrap;">{"".join(cells)}</div>'
    )


def dense_kpi_row(items: list[dict[str, Any]], min_cell_px: int = 100) -> str:
    """Dense grid of KPI cells. Tighter than v1: 0.78rem values, 0.2rem padding."""
    cells: list[str] = []
    for item in items:
        label = item.get("label", "")
        value = item.get("value", "n/a")
        delta = item.get("delta", "")
        delta_color = item.get("delta_color") or TOKENS["text_muted"]
        value_color = item.get("value_color") or TOKENS["text_primary"]
        delta_html = (
            f'<div style="color:{delta_color};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.6rem;font-weight:500;line-height:1;margin-top:0.05rem;">{delta}</div>'
            if delta else ""
        )
        cells.append(
            f'<div style="background:{TOKENS["bg_surface"]};'
            f'border:1px solid {TOKENS["border_subtle"]};'
            f'border-left:2px solid {TOKENS["accent_primary"]};'
            f'border-radius:{TOKENS["radius_sm"]};padding:0.2rem 0.4rem;min-width:0;">'
            f'<div style="color:{TOKENS["text_muted"]};font-family:{TOKENS["font_body"]};'
            f'font-size:0.5rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;'
            f'line-height:1;margin-bottom:0.1rem;overflow:hidden;text-overflow:ellipsis;'
            f'white-space:nowrap;">{label}</div>'
            f'<div style="color:{value_color};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.78rem;font-weight:600;line-height:1.05;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{value}</div>'
            f'{delta_html}</div>'
        )
    return (
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax({min_cell_px}px,1fr));'
        f'gap:0.2rem;margin-bottom:0.35rem;">{"".join(cells)}</div>'
    )


def section_bar(label: str, tape: str = "") -> str:
    """Loud section header. Orange uppercase mono with a thin underline.

    Optional ``tape`` is rendered inline on the right (use
    ``period_returns_tape`` to build it).
    """
    accent = TOKENS["accent_primary"]
    tape_html = (
        f'<span style="float:right;font-family:{TOKENS["font_mono"]};'
        f'font-size:0.65rem;font-weight:500;color:{TOKENS["text_muted"]};">{tape}</span>'
        if tape else ""
    )
    return (
        f'<div style="color:{accent};font-family:{TOKENS["font_mono"]};'
        f'font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.14em;'
        f'border-bottom:1px solid {accent};padding:0.25rem 0 0.15rem 0;'
        f'margin:0.4rem 0 0.3rem 0;">{label}{tape_html}</div>'
    )


def period_returns_tape(prices: pd.Series) -> str:
    """Inline mono tape: 5d / 21d / 63d / 252d returns, sign colored."""
    if prices is None or prices.empty:
        return ""
    last = float(prices.iloc[-1])
    periods = [("5D", 5), ("21D", 21), ("63D", 63), ("252D", 252)]
    cells: list[str] = []
    for label, n in periods:
        if len(prices) <= n:
            continue
        prior = float(prices.iloc[-n - 1])
        if prior == 0:
            continue
        ret = last / prior - 1.0
        color = signed_color(ret)
        cells.append(
            f'<span style="color:{TOKENS["text_muted"]};">{label}</span> '
            f'<span style="color:{color};font-weight:600;">{ret * 100:+.2f}%</span>'
        )
    return " | ".join(cells)
