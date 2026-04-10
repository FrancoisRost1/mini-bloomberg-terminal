"""Bloomberg dark mode CSS injection.

Streamlit's theme config covers colors but not layout density. We inject
a small CSS override so the terminal feels dense and monospaced rather
than the default generous whitespace. Kept as a single string constant.
"""

from __future__ import annotations

import streamlit as st


BLOOMBERG_CSS = """
<style>
:root {
  --bg: #0E1117;
  --panel: #161A23;
  --border: #262B3A;
  --text: #E6E6E6;
  --muted: #888;
  --accent: #FF8C00;
  --pos: #00C853;
  --neg: #FF3D57;
}
.stApp { background: var(--bg); color: var(--text); font-family: 'JetBrains Mono','Fira Code',monospace; }
section[data-testid="stSidebar"] { background: var(--panel); border-right: 1px solid var(--border); }
h1, h2, h3, h4 { font-family: 'JetBrains Mono',monospace; letter-spacing: 0.5px; }
h1 { color: var(--text); font-size: 22px; }
h2 { color: var(--accent); font-size: 16px; text-transform: uppercase; }
h3 { color: var(--text); font-size: 14px; }
[data-testid="stMetric"] { background: var(--panel); padding: 12px; border-left: 3px solid var(--accent); border-radius: 4px; }
[data-testid="stMetricLabel"] { color: var(--muted); font-size: 11px; text-transform: uppercase; }
[data-testid="stMetricValue"] { color: var(--text); font-size: 20px; font-weight: 600; }
div[data-testid="stMarkdownContainer"] code { background: var(--panel); color: var(--accent); padding: 1px 5px; border-radius: 2px; }
.block-container { padding-top: 1rem; padding-bottom: 2rem; }
div.stButton>button { background: var(--panel); color: var(--text); border: 1px solid var(--border); font-family: 'JetBrains Mono',monospace; }
div.stButton>button:hover { border-color: var(--accent); color: var(--accent); }
</style>
"""


def inject() -> None:
    """Call once at the top of ``app.py`` to apply the terminal theme."""
    st.markdown(BLOOMBERG_CSS, unsafe_allow_html=True)
