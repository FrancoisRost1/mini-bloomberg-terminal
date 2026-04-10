"""Project level density override.

Bloomberg terminal density. Applied AFTER the canonical inject_styles()
so it cascades on top of the design system. Tightens block container
padding, reduces hr margins, and forces monospace on every data
bearing element (tables, captions, code, dataframes) so the page
reads like a research terminal rather than a marketing page.

This CSS does not redefine any TOKEN values. It only overrides
spacing and font family rules at the project level. The canonical
design system stays the source of truth for colors and tokens.
"""

from __future__ import annotations

import streamlit as st

from style_inject import TOKENS


DENSITY_CSS = f"""
<style>
/* Tighten the page container */
.block-container {{
    padding-top: 0.5rem !important;
    padding-bottom: 0.75rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 1600px !important;
}}

/* Tighter section spacing */
hr {{ margin: 0.5rem 0 !important; }}

/* Compact metric cards (canonical helper, just less padding) */
div[data-testid="stMetric"] {{ padding: 0.4rem 0.6rem !important; }}

/* Force monospace on every data bearing element */
.stDataFrame, .stDataFrame *, .stTable, .stTable *,
[data-testid="stDataFrameResizable"], [data-testid="stDataFrameResizable"] *,
code, pre, kbd, samp {{
    font-family: {TOKENS["font_mono"]} !important;
}}

/* Captions: monospace and tighter */
.stCaption, [data-testid="stCaptionContainer"], .stMarkdown small {{
    font-family: {TOKENS["font_mono"]} !important;
    font-size: 0.7rem !important;
    color: {TOKENS["text_muted"]} !important;
    line-height: 1.25 !important;
}}

/* Compact dataframe rows. Bloomberg target: ~10-11px, near-zero padding. */
.stDataFrame [role="cell"], .stDataFrame [role="columnheader"] {{
    font-size: 0.68rem !important;
    padding: 0.08rem 0.35rem !important;
    line-height: 1.15 !important;
}}
.stDataFrame [role="row"] {{ min-height: 1.4rem !important; }}

/* Plotly chart container: minimal padding */
.stPlotlyChart {{ padding: 0.25rem !important; margin-bottom: 0.3rem !important; }}

/* Section labels (h3 from canonical) tighter top margin */
h3 {{ margin-top: 0.4rem !important; margin-bottom: 0.2rem !important; }}

/* Form inputs: tighter */
.stTextInput > div > div input,
.stNumberInput > div > div input,
.stSelectbox > div > div {{ padding: 0.25rem 0.5rem !important; font-size: 0.8rem !important; }}
.stTextInput label, .stNumberInput label, .stSelectbox label, .stSlider label {{
    font-size: 0.65rem !important; margin-bottom: 0.05rem !important;
}}

/* Sidebar tightening */
section[data-testid="stSidebar"] .block-container {{ padding-top: 0.75rem !important; }}
section[data-testid="stSidebar"] .stMarkdown p {{ font-size: 0.7rem !important; line-height: 1.3 !important; }}

/* Buttons: smaller */
.stButton > button {{ padding: 0.2rem 0.6rem !important; font-size: 0.7rem !important; }}

/* Numbers in any markdown body get monospace via the .num class */
.num {{ font-family: {TOKENS["font_mono"]} !important; font-weight: 500; }}
</style>
"""


def inject_density() -> None:
    """Apply the project density override after inject_styles() runs."""
    st.markdown(DENSITY_CSS, unsafe_allow_html=True)
