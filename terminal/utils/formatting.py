"""Number formatting helpers.

KPI / header / divider / card components live in the canonical
``style_inject.py`` at the project root (``styled_kpi``, ``styled_header``,
``styled_section_label``, ``styled_divider``, ``styled_card``). This
module only carries pure number formatters used everywhere.

The previous version of this file declared its own ``styled_kpi`` and
``badge``; both were removed because they bypassed the design system
TOKENS and used a different visual signature than the other 10 finance
projects. Do NOT reintroduce them. Use the canonical helpers from
``style_inject.py`` instead.
"""

from __future__ import annotations

import math
from typing import Any


def fmt_pct(value: float, decimals: int = 2) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value * 100:.{decimals}f}%"


def fmt_money(value: float, decimals: int = 2) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    abs_v = abs(value)
    if abs_v >= 1e12:
        return f"${value / 1e12:.{decimals}f}T"
    if abs_v >= 1e9:
        return f"${value / 1e9:.{decimals}f}B"
    if abs_v >= 1e6:
        return f"${value / 1e6:.{decimals}f}M"
    if abs_v >= 1e3:
        return f"${value / 1e3:.{decimals}f}K"
    return f"${value:.{decimals}f}"


def fmt_ratio(value: float, decimals: int = 2, suffix: str = "x") -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value:.{decimals}f}{suffix}"


def fmt_bps(value: float) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value * 10000:.0f}bps"


def fmt_signed_pct(value: float, decimals: int = 2) -> str:
    """Signed percent for delta strings used by ``styled_kpi(delta=...)``."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value * 100:+.{decimals}f}%"


def format_metric(value: Any, fmt: str) -> str:
    if fmt == "pct":
        return fmt_pct(value)
    if fmt == "money":
        return fmt_money(value)
    if fmt == "bps":
        return fmt_bps(value)
    return fmt_ratio(value)


def fmt_ratio_with_note(value: Any, notes: dict[str, str] | None, key: str,
                        decimals: int = 2, suffix: str = "x") -> str:
    """Ratio formatter that honors a companion ``_notes`` dict.

    If the value is nan AND the notes dict has an explanatory entry for
    ``key`` (e.g. ``"N/R"``), render that phrase verbatim instead of
    the generic ``n/a`` placeholder. Notes are assumed to be already
    short and display-ready (no implicit uppercasing here, because
    callers like the Research KPI strip use narrow cells that clip
    anything longer than ~4 characters).
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        if notes and key in notes:
            return str(notes[key])
        return "n/a"
    return f"{value:.{decimals}f}{suffix}"
