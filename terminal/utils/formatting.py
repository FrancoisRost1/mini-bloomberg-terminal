"""Number formatting helpers and styled KPI builder.

Known bug (P8, P9, P10): Streamlit's Markdown parser treats 4+ space
indentation as a code block, which caused styled HTML KPIs to leak
closing tags onto the page. Mitigation: every HTML string here is
built as a SINGLE-LINE concatenated f-string. Do not refactor back
to multi-line templates.
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


def styled_kpi(label: str, value: str, accent: str = "#FF8C00") -> str:
    """Single-line HTML KPI card. MUST stay on one line (see module docstring)."""
    return f'<div style="padding:10px 14px;background:#161A23;border-left:3px solid {accent};border-radius:4px;font-family:JetBrains Mono,Fira Code,monospace;"><div style="color:#888;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">{label}</div><div style="color:#E6E6E6;font-size:20px;font-weight:600;margin-top:4px;">{value}</div></div>'


def badge(text: str, color: str) -> str:
    """Single-line HTML status badge."""
    return f'<span style="display:inline-block;padding:3px 10px;background:{color}22;color:{color};border:1px solid {color};border-radius:3px;font-family:JetBrains Mono,monospace;font-size:11px;font-weight:600;letter-spacing:0.5px;">{text}</span>'


def format_metric(value: Any, fmt: str) -> str:
    if fmt == "pct":
        return fmt_pct(value)
    if fmt == "money":
        return fmt_money(value)
    if fmt == "bps":
        return fmt_bps(value)
    return fmt_ratio(value)
