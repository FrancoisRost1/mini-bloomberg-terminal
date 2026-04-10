"""Error boundary helpers for the UI.

Bloomberg style: data status is a small monospace tag in the top right
of each section, not a full width alarm box. ``data_status`` is the
canonical helper. ``degraded_card`` and ``unavailable_card`` exist for
backward compatibility but render as a single inline mono line, not a
boxed alert.

Status values are deliberately minimal:
- LIVE     fresh data from the production provider
- PARTIAL  some series missing or fell back to a shorter lookback
- STALE    served from cache because the live fetch failed
- DELAYED  endpoint is delayed by tier or by upstream policy
- OFF      the active provider does not serve this endpoint at all
"""

from __future__ import annotations

from typing import Any

from style_inject import TOKENS


_STATUS_COLORS = {
    "LIVE": TOKENS["text_muted"],
    "PARTIAL": TOKENS["text_muted"],
    "STALE": TOKENS["text_muted"],
    "DELAYED": TOKENS["text_muted"],
    "OFF": TOKENS["text_muted"],
}


def data_status(status: str, detail: str = "") -> str:
    """Inline mono status tag. Use as the ``tape`` argument to section_bar."""
    color = _STATUS_COLORS.get(status, TOKENS["text_muted"])
    detail_html = f' <span style="color:{TOKENS["text_muted"]};opacity:0.6;">{detail}</span>' if detail else ""
    return (
        f'<span style="font-family:{TOKENS["font_mono"]};font-size:0.6rem;'
        f'font-weight:600;letter-spacing:0.06em;color:{color};">'
        f'DATA: {status}</span>{detail_html}'
    )


def inline_status_line(status: str, reason: str) -> str:
    """Single line mono status used in place of degraded_card / unavailable_card."""
    color = _STATUS_COLORS.get(status, TOKENS["text_muted"])
    return (
        f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.66rem;'
        f'color:{color};padding:0.2rem 0;">DATA: {status} | {reason}</div>'
    )


def degraded_card(reason: str, provider: str = "n/a") -> str:
    return inline_status_line("PARTIAL", f"{provider} | {reason}")


def unavailable_card(what: str, reason: str) -> str:
    return inline_status_line("OFF", f"{what} | {reason}")


def dev_mode_banner() -> str:
    """Single line dev mode strip across the top."""
    return (
        f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.62rem;'
        f'color:{TOKENS["accent_info"]};border-bottom:1px solid {TOKENS["accent_info"]};'
        f'padding:0.15rem 0.4rem;letter-spacing:0.06em;">'
        f'DEV MODE | yfinance fallback | not for production</div>'
    )


def status_pill(label: str, status: str) -> str:
    """Small inline status pill for engine cards. Muted Bloomberg style."""
    color = {
        "success": TOKENS["accent_success"],
        "failed": TOKENS["accent_danger"],
        "missing": TOKENS["text_muted"],
    }.get(status, TOKENS["accent_warning"])
    return (
        f'<span style="font-family:{TOKENS["font_mono"]};font-size:0.6rem;'
        f'font-weight:600;color:{color};letter-spacing:0.06em;">'
        f'{label} {status.upper()}</span>'
    )


def is_error(obj: Any) -> bool:
    return hasattr(obj, "reason") and hasattr(obj, "provider") and hasattr(obj, "data_type")
