"""Bloomberg density primitives.

Project specific helpers that go BEYOND the canonical style_inject.py.
The canonical helpers (styled_kpi, styled_card) are still used for
content cards; these helpers exist for the data dense surfaces a
research terminal needs:

- ``ticker_tape``: single line horizontal strip of LABEL value (delta)
  cells, monospace, colored by sign. Used by the global header and
  the market indices strip.
- ``dense_kpi_row``: CSS grid that packs 8 to 12 KPI cells per row at
  minimal spacing. Used wherever a page needs to show many metrics at
  once without burning vertical space.
- ``signed_color``: TOKEN selector for any directional number. Returns
  green for positive, red for negative, muted grey for NaN or zero.
- ``mono_inline``: inline span helper that wraps a value in monospace
  with optional color. Use for any number rendered inline in markdown
  or captions.

All helpers respect the canonical TOKENS so swapping the project accent
re skins everything automatically.
"""

from __future__ import annotations

import math
from typing import Any

from style_inject import TOKENS


def signed_color(value: Any) -> str:
    """Return the TOKEN color appropriate for a directional number."""
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
    """Inline monospace span. Use for any number rendered in markdown / captions."""
    color_css = color or TOKENS["text_primary"]
    return (
        f'<span style="font-family:{TOKENS["font_mono"]};'
        f'color:{color_css};font-weight:{weight};font-size:0.78rem;'
        f'letter-spacing:0;">{text}</span>'
    )


def ticker_tape(items: list[dict[str, Any]]) -> str:
    """Single line horizontal ticker strip.

    Each item is a dict with keys ``label``, ``value``, and optional
    ``delta``, ``delta_color``. Cells are separated by a thin vertical
    rule and rendered in monospace. Returns a single line HTML string.
    """
    cells: list[str] = []
    for item in items:
        label = item.get("label", "")
        value = item.get("value", "n/a")
        delta = item.get("delta", "")
        delta_color = item.get("delta_color") or TOKENS["text_muted"]
        delta_html = (
            f'<span style="color:{delta_color};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.7rem;font-weight:500;margin-left:0.35rem;">{delta}</span>'
            if delta else ""
        )
        cells.append(
            f'<span style="display:inline-flex;align-items:baseline;'
            f'gap:0.3rem;padding:0 0.7rem;border-right:1px solid {TOKENS["border_subtle"]};">'
            f'<span style="color:{TOKENS["text_muted"]};font-family:{TOKENS["font_body"]};'
            f'font-size:0.6rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">{label}</span>'
            f'<span style="color:{TOKENS["text_primary"]};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.78rem;font-weight:600;">{value}</span>'
            f'{delta_html}</span>'
        )
    inner = "".join(cells)
    return (
        f'<div style="background:{TOKENS["bg_surface"]};'
        f'border:1px solid {TOKENS["border_default"]};'
        f'border-radius:{TOKENS["radius_sm"]};'
        f'padding:0.4rem 0.2rem;'
        f'overflow-x:auto;white-space:nowrap;">{inner}</div>'
    )


def dense_kpi_row(items: list[dict[str, Any]], min_cell_px: int = 110) -> str:
    """Dense grid of KPI cells. Packs as many cells as fit per row.

    Each item: ``label`` (str), ``value`` (str), optional ``delta``
    (str), optional ``delta_color`` (str). Layout uses CSS grid
    ``repeat(auto-fit, minmax(min_cell_px, 1fr))`` so wider screens
    get more cells per row automatically. 110px default fits ~12 cells
    on a 1400px container.
    """
    cells: list[str] = []
    for item in items:
        label = item.get("label", "")
        value = item.get("value", "n/a")
        delta = item.get("delta", "")
        delta_color = item.get("delta_color") or TOKENS["text_muted"]
        delta_html = (
            f'<div style="color:{delta_color};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.65rem;font-weight:500;margin-top:0.05rem;">{delta}</div>'
            if delta else ""
        )
        cells.append(
            f'<div style="background:{TOKENS["bg_surface"]};'
            f'border:1px solid {TOKENS["border_subtle"]};'
            f'border-left:2px solid {TOKENS["accent_primary"]};'
            f'border-radius:{TOKENS["radius_sm"]};'
            f'padding:0.35rem 0.5rem;min-width:0;">'
            f'<div style="color:{TOKENS["text_muted"]};font-family:{TOKENS["font_body"]};'
            f'font-size:0.55rem;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:0.06em;line-height:1.1;margin-bottom:0.15rem;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{label}</div>'
            f'<div style="color:{TOKENS["text_primary"]};font-family:{TOKENS["font_mono"]};'
            f'font-size:0.95rem;font-weight:600;line-height:1.1;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{value}</div>'
            f'{delta_html}</div>'
        )
    inner = "".join(cells)
    return (
        f'<div style="display:grid;'
        f'grid-template-columns:repeat(auto-fit,minmax({min_cell_px}px,1fr));'
        f'gap:0.3rem;margin-bottom:0.5rem;">{inner}</div>'
    )
