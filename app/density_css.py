"""Project level density override.

Bloomberg terminal density. Applied AFTER the canonical inject_styles()
so it cascades on top of the design system. The streamlit native top
bar is hidden; the global header (rendered by app/header.py) sits at
the absolute top of the viewport. Every spacing rule below is set to
the smallest value that still keeps content legible.
"""

from __future__ import annotations

import streamlit as st

from style_inject import TOKENS


DENSITY_CSS = f"""
<style>
/* Hide the native streamlit top bar so our header sits at viewport top */
[data-testid="stHeader"] {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}

/* Page container: minimum padding, full width */
.block-container {{
    padding-top: 0.4rem !important;
    padding-bottom: 0.4rem !important;
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
    max-width: 1700px !important;
}}

/* Vertical block stacking: collapse all default gaps */
[data-testid="stVerticalBlock"] {{ gap: 0.25rem !important; }}
[data-testid="stHorizontalBlock"] {{ gap: 0.4rem !important; }}
[data-testid="element-container"] {{ margin-bottom: 0 !important; }}

/* Section dividers */
hr {{ margin: 0.3rem 0 !important; border-color: {TOKENS["border_subtle"]} !important; }}

/* Compact metric cards */
div[data-testid="stMetric"] {{ padding: 0.35rem 0.55rem !important; }}

/* Force monospace on every data bearing element */
.stDataFrame, .stDataFrame *, .stTable, .stTable *,
[data-testid="stDataFrameResizable"], [data-testid="stDataFrameResizable"] *,
code, pre, kbd, samp {{ font-family: {TOKENS["font_mono"]} !important; }}

/* Captions: monospace and tighter */
.stCaption, [data-testid="stCaptionContainer"], .stMarkdown small {{
    font-family: {TOKENS["font_mono"]} !important;
    font-size: 0.66rem !important;
    color: {TOKENS["text_muted"]} !important;
    line-height: 1.2 !important;
    margin: 0.1rem 0 !important;
}}

/* Compact dataframe rows. Bloomberg target: ~10-11px, near zero padding. */
.stDataFrame [role="cell"], .stDataFrame [role="columnheader"] {{
    font-size: 0.66rem !important;
    padding: 0.06rem 0.32rem !important;
    line-height: 1.1 !important;
}}
.stDataFrame [role="row"] {{ min-height: 1.3rem !important; }}
.stDataFrame {{ margin-bottom: 0.25rem !important; }}

/* Plotly chart container: minimal padding, no gap below */
.stPlotlyChart {{ padding: 0.2rem !important; margin-bottom: 0.15rem !important; }}

/* Tabs: dense Bloomberg style. Mono caps, tight padding, orange underline. */
.stTabs [data-baseweb="tab-list"] {{ gap: 0 !important; padding: 0 !important; }}
.stTabs [data-baseweb="tab"] {{
    padding: 0.25rem 0.65rem !important;
    font-size: 0.6rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-family: {TOKENS["font_mono"]} !important;
    min-height: 1.5rem !important;
}}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: 0.25rem !important; }}

/* Section labels (h3 from canonical) tighter top margin */
h3 {{ margin-top: 0.2rem !important; margin-bottom: 0.1rem !important; }}

/* Form inputs: tighter */
.stTextInput > div > div input,
.stNumberInput > div > div input,
.stSelectbox > div > div {{ padding: 0.2rem 0.45rem !important; font-size: 0.75rem !important; }}
.stTextInput label, .stNumberInput label, .stSelectbox label, .stSlider label {{
    font-size: 0.6rem !important; margin-bottom: 0 !important;
}}

/* Sidebar: narrow, flat, terminal style. No rounded pills, no padding. */
section[data-testid="stSidebar"] {{ width: 200px !important; min-width: 200px !important; }}
section[data-testid="stSidebar"] > div {{ padding-top: 0.4rem !important; }}
section[data-testid="stSidebar"] .block-container {{ padding: 0.4rem 0.5rem !important; }}
section[data-testid="stSidebar"] .stMarkdown p {{ font-size: 0.66rem !important; line-height: 1.2 !important; margin: 0.05rem 0 !important; }}
section[data-testid="stSidebar"] .stMarkdown h3 {{ font-size: 0.6rem !important; letter-spacing: 0.1em; margin: 0.5rem 0 0.2rem 0 !important; color: {TOKENS["accent_primary"]} !important; }}
/* Flatten the navigation entry. No rounded pill, no big padding. Sharp left border on active. */
section[data-testid="stSidebarNav"] ul {{ padding: 0 !important; }}
section[data-testid="stSidebarNav"] li {{ list-style: none !important; }}
section[data-testid="stSidebarNav"] a {{
    border-radius: 0 !important;
    padding: 0.25rem 0.5rem !important;
    font-family: {TOKENS["font_mono"]} !important;
    font-size: 0.66rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-left: 2px solid transparent !important;
}}
section[data-testid="stSidebarNav"] a[aria-current="page"] {{
    background-color: transparent !important;
    border-left: 2px solid {TOKENS["accent_primary"]} !important;
    color: {TOKENS["accent_primary"]} !important;
}}

/* Buttons: smaller */
.stButton > button {{ padding: 0.18rem 0.55rem !important; font-size: 0.66rem !important; }}

/* Page title h1: tighter top margin and zero bottom gap so the first
   data element sits immediately below it. */
h1 {{ margin-top: 0 !important; margin-bottom: 0.05rem !important; font-size: 1.1rem !important; }}

/* Markdown body line height tighter */
.stMarkdown p {{ margin: 0.1rem 0 !important; line-height: 1.3 !important; }}

/* Numbers in any markdown body get monospace via the .num class */
.num {{ font-family: {TOKENS["font_mono"]} !important; font-weight: 500; }}
</style>
"""


def inject_density() -> None:
    st.markdown(DENSITY_CSS, unsafe_allow_html=True)
