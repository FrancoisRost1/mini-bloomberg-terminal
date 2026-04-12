"""Bloomberg-style command bar. Persistent across all pages.

Accepts ticker symbols, page shortcuts, and combined commands.
Examples: "AAPL", "market", "MSFT options", "lbo", "GOOGL research".
"""

from __future__ import annotations

import streamlit as st

from style_inject import TOKENS
from terminal.utils.ticker_lookup import suggest_ticker

# Page shortcut -> url_path mapping (matches st.Page url_path in app.py).
_PAGE_MAP: dict[str, str] = {
    "market": "pages/market_overview.py",
    "research": "pages/ticker_deep_dive.py",
    "options": "pages/options_lab.py",
    "lbo": "pages/lbo_quick_calc.py",
    "comps": "pages/comps_relative_value.py",
    "portfolio": "pages/portfolio_builder.py",
}

_CMD_CSS = f"""
<style>
div[data-testid="stTextInput"]:has(input#command_bar) input {{
    font-family: {TOKENS["font_mono"]} !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    background-color: #0A0A0A !important;
    border: 1px solid {TOKENS["accent_primary"]} !important;
    border-radius: 2px !important;
    color: {TOKENS["text_primary"]} !important;
    padding: 0.3rem 0.6rem !important;
    caret-color: {TOKENS["accent_primary"]} !important;
}}
div[data-testid="stTextInput"]:has(input#command_bar) input::placeholder {{
    color: {TOKENS["text_muted"]} !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}}
</style>
"""


def _parse_command(raw: str) -> tuple[str | None, str | None]:
    """Parse command into (ticker_or_None, page_or_None)."""
    parts = raw.strip().upper().split()
    if not parts:
        return None, None
    # Single token: page shortcut or ticker.
    if len(parts) == 1:
        token = parts[0].lower()
        if token in _PAGE_MAP:
            return None, token
        return parts[0], "research"
    # Two tokens: try both orderings (AAPL options / options AAPL).
    a, b = parts[0], parts[1]
    if a.lower() in _PAGE_MAP:
        return b, a.lower()
    if b.lower() in _PAGE_MAP:
        return a, b.lower()
    # Default: first token is ticker, go to research.
    return a, "research"


def render_command_bar() -> None:
    """Render the command bar and handle navigation."""
    st.markdown(_CMD_CSS, unsafe_allow_html=True)
    cmd = st.text_input(
        "Command",
        value="",
        key="command_bar",
        label_visibility="collapsed",
        placeholder="TICKER or COMMAND (e.g. AAPL, MSFT OPTIONS, MARKET, LBO)",
    )
    if not cmd or not cmd.strip():
        return
    ticker, page = _parse_command(cmd)
    if ticker:
        suggestions = suggest_ticker(ticker)
        resolved = suggestions[0] if suggestions else ticker
        st.session_state["active_ticker"] = resolved
        if suggestions and resolved != ticker:
            st.caption(f"Resolved: {resolved}")
    target = _PAGE_MAP.get(page or "research")
    if target:
        try:
            st.switch_page(target)
        except Exception:
            st.rerun()
