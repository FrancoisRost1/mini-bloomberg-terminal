"""NEWS section for the Research page.

Renders the 8 most recent ticker-specific articles in a dense
Bloomberg-style list: timestamp | publisher | title (linked).
Primary source is Finnhub; falls back to yfinance when key is absent.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from style_inject import TOKENS
from terminal.utils.density import section_bar
from terminal.utils.error_handling import inline_status_line

_NEWS_SOURCE = "FINNHUB" if os.environ.get("FINNHUB_API_KEY") else "yfinance"


def _fmt_time(iso: str) -> str:
    """Convert an ISO-8601 timestamp to compact 'Apr 12 14:30' format."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d %H:%M")
    except Exception:
        return iso[:16]


def _news_row(article: dict) -> str:
    """Single article as a compact HTML row."""
    ts = _fmt_time(article.get("published", ""))
    pub = article.get("publisher", "") or ""
    title = article.get("title", "") or "Untitled"
    link = article.get("link", "")
    mono = TOKENS["font_mono"]
    muted = TOKENS["text_muted"]
    secondary = TOKENS["text_secondary"]
    primary = TOKENS["text_primary"]
    accent = TOKENS["accent_primary"]
    # Title is a clickable link when a URL is available.
    if link:
        title_html = (
            f'<a href="{link}" target="_blank" rel="noopener" '
            f'style="color:{primary};text-decoration:none;">{title}</a>'
        )
    else:
        title_html = f'<span style="color:{primary};">{title}</span>'
    return (
        f'<div style="display:flex;gap:0.5rem;align-items:baseline;'
        f'padding:0.18rem 0;border-bottom:1px solid {TOKENS["border_subtle"]};">'
        f'<span style="font-family:{mono};font-size:0.62rem;color:{muted};'
        f'white-space:nowrap;min-width:5.5rem;">{ts}</span>'
        f'<span style="font-family:{mono};font-size:0.62rem;color:{secondary};'
        f'white-space:nowrap;min-width:5rem;max-width:8rem;overflow:hidden;'
        f'text-overflow:ellipsis;">{pub}</span>'
        f'<span style="font-family:{mono};font-size:0.62rem;flex:1;'
        f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
        f'{title_html}</span></div>'
    )


def render_news(ticker: str, data_manager: Any) -> None:
    """Render the NEWS section on the Research page."""
    st.markdown(section_bar("NEWS", source=_NEWS_SOURCE), unsafe_allow_html=True)
    articles = data_manager.get_news(ticker, count=8)
    if not articles:
        st.markdown(
            inline_status_line("OFF", source=_NEWS_SOURCE),
            unsafe_allow_html=True,
        )
        return
    rows = "".join(_news_row(a) for a in articles)
    st.markdown(
        f'<div style="background:{TOKENS["bg_surface"]};'
        f'border:1px solid {TOKENS["border_default"]};'
        f'border-radius:3px;padding:0.3rem 0.5rem;">{rows}</div>',
        unsafe_allow_html=True,
    )
