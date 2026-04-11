"""Compact economic calendar strip for the Market Overview.

Renders a single-line Bloomberg style tape listing upcoming central
bank meetings and macro releases. Static for v1; a live connector
(Trading Economics or FRED calendar endpoint) lands in v2.

Split out of _market_regime.py to keep that module under the per
module line budget.
"""

from __future__ import annotations

import streamlit as st

from style_inject import TOKENS


_EVENTS: list[tuple[str, str]] = [
    ("FOMC",   "Jun 17"),
    ("CPI",    "May 13"),
    ("NFP",    "May 02"),
    ("ECB",    "Jun 05"),
    ("BOE",    "Jun 19"),
    ("GDP Q1", "May 29"),
    ("PCE",    "May 30"),
]


def render_event_calendar_strip() -> None:
    """One-line calendar rail with accent orange left border."""
    mono = TOKENS["font_mono"]
    muted = TOKENS["text_muted"]
    accent = "#FF8A2A"
    border = TOKENS["border_subtle"]
    cells = "".join(
        f'<span style="color:{muted};margin-right:0.35rem;">{lbl}</span>'
        f'<span style="color:{TOKENS["text_primary"]};margin-right:0.9rem;">{date}</span>'
        for lbl, date in _EVENTS
    )
    st.markdown(
        f'<div style="font-family:{mono};font-size:0.64rem;font-weight:600;'
        f'letter-spacing:0.06em;color:{TOKENS["text_secondary"]};line-height:1.6;'
        f'background:#080808;border:1px solid {border};border-left:2px solid {accent};'
        f'padding:0.35rem 0.55rem;margin:0.3rem 0 0.15rem 0;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
        f'<span style="color:{accent};font-weight:800;text-transform:uppercase;'
        f'letter-spacing:0.1em;margin-right:0.7rem;">CALENDAR</span>'
        f'{cells}</div>',
        unsafe_allow_html=True,
    )
