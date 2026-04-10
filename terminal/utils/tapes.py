"""Ticker tape primitives for the global header and section headings.

Three helpers, all single line HTML strings designed to be passed to
``st.markdown(..., unsafe_allow_html=True)``:

- ``ticker_tape``      legacy LABEL value (delta) cells, used by section bars
- ``bloomberg_tape``   Bloomberg style strip with arrows and colored % change
- ``period_returns_tape`` inline 5d / 21d / 63d / 252d return cells

Split from density.py so that file stays under the per module budget.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from style_inject import TOKENS


def _signed_color(value: Any) -> str:
    """Local copy of density.signed_color to avoid a circular import."""
    if value is None:
        return TOKENS["text_muted"]
    try:
        v = float(value)
    except (TypeError, ValueError):
        return TOKENS["text_muted"]
    if math.isnan(v) or v == 0:
        return TOKENS["text_muted"]
    return TOKENS["accent_success"] if v > 0 else TOKENS["accent_danger"]


signed_color = _signed_color


def ticker_tape(items: list[dict[str, Any]]) -> str:
    """Single line LABEL value (delta) strip. Compact monospace."""
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


def bloomberg_tape(items: list[dict[str, Any]]) -> str:
    """Bloomberg trading desk style ticker tape.

    Each item: ``label`` (str), ``price`` (str), optional ``change_pct``
    (signed float). Renders as ``LABEL price ▲1.23%`` with the arrow
    and percent both colored by sign. Very dense single line strip with
    horizontal scroll if it overflows.
    """
    cells: list[str] = []
    for item in items:
        label = item.get("label", "")
        price = item.get("price", "n/a")
        change = item.get("change_pct")
        if change is None or change != change:
            arrow = "·"
            change_str = ""
            color = TOKENS["text_muted"]
        else:
            arrow = "\u25B2" if change > 0 else ("\u25BC" if change < 0 else "\u00B7")
            color = signed_color(change)
            change_str = f"{abs(change) * 100:.2f}%"
        cells.append(
            f'<span style="display:inline-flex;align-items:baseline;gap:0.35rem;'
            f'padding:0 0.7rem;border-right:1px solid {TOKENS["border_subtle"]};">'
            f'<span style="color:{TOKENS["text_secondary"]};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.7rem;font-weight:700;letter-spacing:0.04em;">{label}</span>'
            f'<span style="color:{TOKENS["text_primary"]};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.7rem;font-weight:600;">{price}</span>'
            f'<span style="color:{color};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.7rem;font-weight:700;">{arrow}{change_str}</span></span>'
        )
    return (
        f'<div style="background:{TOKENS["bg_surface"]};'
        f'border:1px solid {TOKENS["border_default"]};border-radius:{TOKENS["radius_sm"]};'
        f'padding:0.4rem 0.2rem;overflow-x:auto;white-space:nowrap;">{"".join(cells)}</div>'
    )


def period_returns_tape(prices: pd.Series) -> str:
    """Inline 5d / 21d / 63d / 252d returns, colored by sign."""
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
            f'<span style="color:{color};font-weight:700;">{ret * 100:+.2f}%</span>'
        )
    return " | ".join(cells)
