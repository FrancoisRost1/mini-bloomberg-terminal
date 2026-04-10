"""Inline SVG sparkline.

Returns a single line SVG string sized to fit a sidebar or header
slot. Renders without any external library so the component can be
dropped into st.markdown(unsafe_allow_html=True). The polyline color
is signed by the start to end change.
"""

from __future__ import annotations

from typing import Sequence

from style_inject import TOKENS


def build_sparkline_svg(
    values: Sequence[float],
    width: int = 60,
    height: int = 18,
    color: str | None = None,
) -> str:
    """Compact polyline sparkline. Empty input returns an empty string."""
    if not values or len(values) < 2:
        return ""
    floats = [float(v) for v in values if v == v]
    if len(floats) < 2:
        return ""
    lo = min(floats)
    hi = max(floats)
    span = (hi - lo) or 1.0
    n = len(floats)
    pts: list[str] = []
    for i, v in enumerate(floats):
        x = (i / (n - 1)) * (width - 2) + 1
        y = height - ((v - lo) / span) * (height - 2) - 1
        pts.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(pts)
    chg = (floats[-1] - floats[0]) / floats[0] if floats[0] else 0.0
    if color is None:
        if chg > 0:
            color = TOKENS["accent_success"]
        elif chg < 0:
            color = TOKENS["accent_danger"]
        else:
            color = TOKENS["text_muted"]
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;">'
        f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.4" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )
