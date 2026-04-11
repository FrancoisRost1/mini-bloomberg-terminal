"""Global header sidebar show / hide toggle.

Stateful Streamlit button that flips ``st.session_state['sidebar_visible']``
and triggers a rerun. The sidebar is hidden by ``_inject_sidebar_visibility``
in app.py when the flag is False. Styling is injected inline so the
button reads as a Bloomberg F-key rather than a rounded web button.
"""

from __future__ import annotations

import streamlit as st


_TOGGLE_CSS = """
<style>
div[data-testid="stVerticalBlock"] button[data-testid*="sidebar_toggle"] {
    background: #0E0E0E !important;
    color: #FF8A2A !important;
    border: 1px solid #FF8A2A !important;
    border-radius: 2px !important;
    font-family: "JetBrains Mono", monospace !important;
    font-size: 0.62rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    padding: 0.38rem 0.2rem !important;
    width: 100% !important;
    box-shadow: 0 0 0 1px rgba(255,138,42,0.15) inset !important;
}
div[data-testid="stVerticalBlock"] button[data-testid*="sidebar_toggle"]:hover {
    background: rgba(255,138,42,0.12) !important;
    border-color: #FFB055 !important;
    color: #FFB055 !important;
}
</style>
"""


def render_sidebar_toggle(col) -> None:
    """Render the toggle button inside the given Streamlit column."""
    with col:
        st.markdown(_TOGGLE_CSS, unsafe_allow_html=True)
        visible = st.session_state.get("sidebar_visible", True)
        label = "< NAV" if visible else "MENU >"
        if st.button(label, key="sidebar_toggle", use_container_width=True):
            st.session_state["sidebar_visible"] = not visible
            st.rerun()
