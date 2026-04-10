"""Error boundary helpers for the UI.

The terminal must never crash on data failure. These helpers return
HTML strings (single-line, per the styled_kpi rule) that pages render
via ``st.markdown(..., unsafe_allow_html=True)``. They use ``TOKENS``
from the canonical design system so colors stay consistent.

Status pills follow the DESIGN.md hard rules: sharp corners, muted
palette, no glow, no gradient.
"""

from __future__ import annotations

from typing import Any

from style_inject import TOKENS


def _pill(label: str, color: str) -> str:
    return (
        f'<span style="display:inline-block;'
        f'padding:0.2rem 0.55rem;'
        f'background:{TOKENS["bg_elevated"]};'
        f'color:{color};'
        f'border:1px solid {color};'
        f'border-radius:{TOKENS["radius_sm"]};'
        f'font-family:{TOKENS["font_body"]};'
        f'font-size:0.65rem;'
        f'font-weight:600;'
        f'letter-spacing:0.08em;'
        f'text-transform:uppercase;">{label}</span>'
    )


def _card(label: str, color: str, what: str, reason: str) -> str:
    return (
        f'<div style="background:{TOKENS["bg_surface"]};'
        f'border:1px solid {TOKENS["border_default"]};'
        f'border-left:3px solid {color};'
        f'border-radius:{TOKENS["radius_md"]};'
        f'padding:0.75rem 1rem;'
        f'box-shadow:{TOKENS["shadow_sm"]};'
        f'margin-bottom:0.75rem;">'
        f'{_pill(label, color)}'
        f'<div style="margin-top:0.4rem;color:{TOKENS["text_muted"]};'
        f'font-size:{TOKENS["text_xs"]};font-family:{TOKENS["font_body"]};">{what}</div>'
        f'<div style="margin-top:0.2rem;color:{TOKENS["text_secondary"]};'
        f'font-size:{TOKENS["text_sm"]};font-family:{TOKENS["font_body"]};">{reason}</div>'
        f'</div>'
    )


def degraded_card(reason: str, provider: str = "n/a") -> str:
    return _card("DEGRADED", TOKENS["accent_warning"], f"Provider: {provider}", reason)


def unavailable_card(what: str, reason: str) -> str:
    return _card("DATA UNAVAILABLE", TOKENS["accent_danger"], what, reason)


def dev_mode_banner() -> str:
    return _card(
        "DEV MODE",
        TOKENS["accent_info"],
        "Serving development data (yfinance).",
        "Not for production use. Set APP_MODE=production for live data.",
    )


def status_pill(label: str, status: str) -> str:
    """Inline status pill for engine cards. ``status`` chooses the color."""
    color = {
        "success": TOKENS["accent_success"],
        "failed": TOKENS["accent_danger"],
        "missing": TOKENS["text_muted"],
    }.get(status, TOKENS["accent_warning"])
    return _pill(f"{label}: {status.upper()}", color)


def is_error(obj: Any) -> bool:
    """True if ``obj`` is a ProviderError returned from the data manager."""
    return hasattr(obj, "reason") and hasattr(obj, "provider") and hasattr(obj, "data_type")
