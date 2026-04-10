"""Error boundary helpers for the UI.

Bloomberg style: data status is a sharp inline mono pill, never a
boxed alarm. User facing strings are short and clean. Long technical
detail (stack messages, provider error reasons) only render when
APP_MODE=development via ``dev_detail_caption``.
"""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from style_inject import TOKENS


def _is_dev() -> bool:
    return os.environ.get("APP_MODE", "production").lower() != "production"


def data_status(status: str, source: str = "") -> str:
    """Inline mono status pill rendered in section_bar tape position.

    Use as ``section_bar(label, source=...)``; this function exists for
    pages that build their own status line outside section_bar.
    """
    color = TOKENS["text_secondary"]
    src = f' | SRC {source.upper()}' if source else ""
    return (
        f'<span style="font-family:{TOKENS["font_mono"]};font-size:0.62rem;'
        f'font-weight:700;letter-spacing:0.08em;color:{color};">'
        f'DATA {status.upper()}{src}</span>'
    )


def inline_status_line(status: str, source: str = "") -> str:
    """Single line mono status used in body when a section degrades."""
    color = TOKENS["text_secondary"]
    src = f' | SRC {source.upper()}' if source else ""
    return (
        f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.66rem;'
        f'font-weight:600;color:{color};padding:0.2rem 0;letter-spacing:0.06em;">'
        f'DATA {status.upper()}{src}</div>'
    )


def degraded_card(reason: str, provider: str = "") -> str:
    """Compatibility wrapper. Renders a sharp PARTIAL status line."""
    return inline_status_line("PARTIAL", source=provider)


def unavailable_card(what: str, reason: str = "") -> str:
    """Compatibility wrapper. Renders a sharp OFF status line."""
    return inline_status_line("OFF")


def dev_mode_banner() -> str:
    return (
        f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.62rem;'
        f'color:{TOKENS["accent_info"]};border-bottom:1px solid {TOKENS["accent_info"]};'
        f'padding:0.15rem 0.4rem;letter-spacing:0.06em;">'
        f'DEV MODE | yfinance fallback active | not for production</div>'
    )


def status_pill(label: str, status: str) -> str:
    """Sharp inline mono pill for engine cards."""
    color = {
        "success": TOKENS["accent_success"],
        "failed": TOKENS["accent_danger"],
        "missing": TOKENS["text_muted"],
    }.get(status, TOKENS["accent_warning"])
    return (
        f'<span style="font-family:{TOKENS["font_mono"]};font-size:0.62rem;'
        f'font-weight:700;color:{color};letter-spacing:0.08em;">'
        f'{label} {status.upper()}</span>'
    )


def dev_detail_caption(detail: str) -> None:
    """Render a long technical detail line ONLY when APP_MODE=development.

    Use this for stack traces, provider error reasons, raw URLs, etc.
    The user facing surface stays clean; developers can flip the env
    var to see the underlying mechanics.
    """
    if not _is_dev():
        return
    if not detail:
        return
    st.caption(f"dev: {detail}")


def is_error(obj: Any) -> bool:
    return hasattr(obj, "reason") and hasattr(obj, "provider") and hasattr(obj, "data_type")


def safe_render(callable_, *, label: str, source: str = "") -> Any:
    """Run a render callable, swallow any exception, return None on failure
    while showing an inline status line. Used to prevent raw tracebacks
    from leaking into the production UI.
    """
    try:
        return callable_()
    except Exception as exc:
        st.markdown(inline_status_line(f"PARTIAL", source=source), unsafe_allow_html=True)
        dev_detail_caption(f"{label} failed: {type(exc).__name__}: {exc}")
        return None
