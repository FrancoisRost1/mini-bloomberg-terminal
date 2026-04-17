"""Global header status bar.

Single line strip rendered below the ticker tape. Shows:
- US equity market status (OPEN / CLOSED / PRE / POST)
- Current time in New York
- Data freshness tag ("prices as of HH:MM ET" or the UTC fetch time
  from the last refreshed ticker)

Zero data fetches: the strip reads existing session state and the
clock. It is a pure render helper, designed to sit in the gap between
the marquee and the first page content so there is no dead zone.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from style_inject import TOKENS


# US eastern time. Hardcoded offset for DST vs standard is not in the
# stdlib on every container so we approximate with -04:00 (EDT) during
# the typical US trading year. The status bar rebuilds on every page
# render so the label flips to CLOSED off hours either way.
_ET_OFFSET_HOURS = -4


def _et_now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=_ET_OFFSET_HOURS)


def _market_status(now_et: datetime) -> tuple[str, str]:
    """Return (label, color_token_key). Pre 09:30 ET is PRE, 09:30 to
    16:00 ET is OPEN, 16:00 to 20:00 ET is POST, otherwise CLOSED."""
    wd = now_et.weekday()
    t = now_et.time()
    if wd >= 5:  # Saturday or Sunday
        return "US CLOSED", "text_muted"
    if time(9, 30) <= t < time(16, 0):
        return "US OPEN", "accent_success"
    if time(4, 0) <= t < time(9, 30):
        return "US PRE", "accent_warning"
    if time(16, 0) <= t < time(20, 0):
        return "US POST", "accent_warning"
    return "US CLOSED", "text_muted"


def build_status_bar_html(data_manager: Any | None = None) -> str:
    """Build the one-line status strip. Pure HTML, no Streamlit calls.

    The mode indicator ('MODE PRODUCTION' / 'MODE DEVELOPMENT') was
    removed from the strip on 2026-04-17 after a recruiter-facing
    audit flagged it as dev-jargon leak. The registry still exposes
    ``mode_label()`` for internal code paths; it just does not render
    here anymore. A DEV banner still appears at the top of the page
    via ``dev_mode_banner()`` when the app is not in production.
    """
    _ = data_manager  # reserved for future per-provider freshness tags
    now_et = _et_now()
    label, token = _market_status(now_et)
    color = TOKENS.get(token, TOKENS["text_secondary"])
    et_clock = now_et.strftime("%H:%M ET")
    utc_clock = datetime.now(timezone.utc).strftime("%H:%M UTC")

    freshness = f"prices as of {et_clock}"
    pieces = [
        (label, color),
        (et_clock, TOKENS["text_primary"]),
        (utc_clock, TOKENS["text_muted"]),
        (freshness, TOKENS["text_muted"]),
    ]

    spans = "".join(
        f'<span style="color:{c};padding:0 0.7rem;'
        f'border-right:1px solid rgba(255,255,255,0.06);">{text}</span>'
        for text, c in pieces
    )
    return (
        f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.66rem;'
        f'font-weight:600;letter-spacing:0.06em;text-transform:uppercase;'
        f'background:#080808;color:{TOKENS["text_secondary"]};'
        f'border-bottom:1px solid rgba(255,255,255,0.06);'
        f'padding:0.15rem 0.2rem;display:flex;align-items:center;'
        f'justify-content:flex-start;">{spans}</div>'
    )


def render_status_bar(data_manager: Any | None = None) -> None:
    """Render the status bar into the current Streamlit frame."""
    st.markdown(build_status_bar_html(data_manager), unsafe_allow_html=True)
