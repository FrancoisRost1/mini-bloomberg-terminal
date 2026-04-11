"""Bloomberg density primitives. Project specific helpers beyond
the canonical style_inject. Tape helpers (ticker_tape, bloomberg_tape,
period_returns_tape) live in tapes.py and are re exported here.
Pandas Styler helpers for directional coloring live in
dataframe_styling.py and are re exported here.
"""

from __future__ import annotations

import math
from typing import Any

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


def dense_kpi_row(items: list[dict[str, Any]], min_cell_px: int = 110) -> str:
    """Dense grid of KPI cells. Tighter than v1: 0.78rem values, 0.2rem padding.

    Every grid item is ``min-width: 0`` so it can shrink below its
    intrinsic content width (CSS Grid defaults items to ``min-width:
    auto`` which allows contents to push neighbours aside). The label
    and value elements use ``overflow: hidden`` with ``text-overflow:
    ellipsis`` so clipped text ends in ``...`` instead of bleeding
    into the next cell. Delta strings render their own mono cell and
    are also ellipsised.
    """
    cells: list[str] = []
    for item in items:
        label = str(item.get("label", ""))
        value = str(item.get("value", "n/a"))
        delta = str(item.get("delta", ""))
        delta_color = item.get("delta_color") or TOKENS["text_muted"]
        value_color = item.get("value_color") or TOKENS["text_primary"]
        delta_html = (
            f'<div title="{delta}" style="color:{delta_color};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.6rem;font-weight:500;line-height:1;margin-top:0.08rem;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{delta}</div>'
            if delta else ""
        )
        cells.append(
            f'<div style="background:{TOKENS["bg_surface"]};'
            f'border:1px solid {TOKENS["border_subtle"]};'
            f'border-left:2px solid {TOKENS["accent_primary"]};'
            f'border-radius:{TOKENS["radius_sm"]};padding:0.25rem 0.45rem;'
            f'min-width:0;overflow:hidden;">'
            f'<div title="{label}" style="color:{TOKENS["text_muted"]};font-family:{TOKENS["font_body"]};'
            f'font-size:0.52rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;'
            f'line-height:1;margin-bottom:0.15rem;overflow:hidden;text-overflow:ellipsis;'
            f'white-space:nowrap;">{label}</div>'
            f'<div title="{value}" style="color:{value_color};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.8rem;font-weight:600;line-height:1.05;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{value}</div>'
            f'{delta_html}</div>'
        )
    return (
        f'<div style="display:grid;'
        f'grid-template-columns:repeat(auto-fit,minmax({min_cell_px}px,1fr));'
        f'gap:0.3rem;margin-bottom:0.4rem;align-items:stretch;">{"".join(cells)}</div>'
    )


def dense_kpi_rows(items: list[dict[str, Any]], rows: int = 2, min_cell_px: int = 118) -> str:
    """Split ``items`` across ``rows`` balanced dense KPI rows.

    When a single row would cram too many cells and clip labels, call
    this helper with ``rows=2`` (or 3 for very long lists). The
    function divides items into near-equal chunks in order, renders
    each chunk with ``dense_kpi_row``, and concatenates the HTML. A
    small vertical gap separates the rows so they read as a 2D grid.

    The split is by COUNT not by content type, so callers ordering
    matters: put the most important KPIs first so they always land in
    the first row.
    """
    if not items:
        return ""
    rows = max(1, int(rows))
    per_row = (len(items) + rows - 1) // rows
    html_parts: list[str] = []
    for r in range(rows):
        chunk = items[r * per_row:(r + 1) * per_row]
        if not chunk:
            continue
        html_parts.append(dense_kpi_row(chunk, min_cell_px=min_cell_px))
    return "".join(html_parts)


def section_bar(label: str, tape: str = "", source: str = "") -> str:
    """Loud section header. Bright orange uppercase mono on a 2px
    underline. Higher contrast on the new #080808 background.
    """
    # Brighter orange than the project accent (#E07020) so the headers
    # punch on near-black. Same hue, higher value.
    accent = "#FF8A2A"
    pieces: list[str] = []
    if source:
        pieces.append(
            f'<span style="font-family:{TOKENS["font_mono"]};font-size:0.55rem;'
            f'font-weight:700;color:{TOKENS["text_secondary"]};letter-spacing:0.08em;'
            f'border:1px solid {TOKENS["border_default"]};border-radius:2px;'
            f'padding:0 0.3rem;margin-right:0.4rem;">SRC {source.upper()}</span>'
        )
    if tape:
        pieces.append(
            f'<span style="font-family:{TOKENS["font_mono"]};font-size:0.65rem;'
            f'font-weight:600;color:{TOKENS["text_secondary"]};">{tape}</span>'
        )
    right = (f'<span style="float:right;">{"".join(pieces)}</span>' if pieces else "")
    return (
        f'<div style="color:{accent};font-family:{TOKENS["font_mono"]};'
        f'font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.14em;'
        f'border-bottom:2px solid {accent};padding:0.12rem 0 0.05rem 0;'
        f'margin:0.08rem 0 0.1rem 0;text-shadow:0 0 1px rgba(255,138,42,0.25);">{label}{right}</div>'
    )


# Re export tape helpers so existing call sites continue to import from density.
from .tapes import bloomberg_tape, period_returns_tape, ticker_tape  # noqa: E402,F401
