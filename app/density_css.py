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

/* Defensive: never render a stPageLink (nav link button) in the main
   content area. Some Streamlit versions auto-emit these for the first
   page in st.navigation if the user's current page has no title hook;
   we only want navigation in the sidebar. */
section[data-testid="stMain"] [data-testid="stPageLink"],
section[data-testid="stMain"] a[data-testid="stPageLink-NavLink"] {{
    display: none !important;
}}

/* Page container: minimum padding, full viewport width.
   Streamlit defaults to a ~1200px max-width even with layout="wide";
   override every known wrapper so the main content stretches edge
   to edge on 2560px monitors. No empty side gutters. */
.stMainBlockContainer,
.block-container,
[data-testid="stAppViewBlockContainer"],
[data-testid="stMainBlockContainer"] {{
    max-width: 100% !important;
    width: 100% !important;
    padding-top: 0.15rem !important;
    padding-bottom: 0.15rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    background-color: #080808 !important;
}}
[data-testid="stMain"] {{ max-width: 100% !important; width: 100% !important; }}
.stApp {{ background-color: #080808 !important; }}

/* Vertical block stacking: collapse Streamlit's generous default gaps,
   but leave ~3px between siblings so section headers never look like
   they are touching the content immediately below. */
[data-testid="stVerticalBlock"] {{ gap: 0.22rem !important; }}
[data-testid="stHorizontalBlock"] {{ gap: 0.2rem !important; }}

/* Element containers keep a tiny trailing margin so KPI strips and
   section bars have room to breathe below. */
[data-testid="element-container"] {{ margin-bottom: 0.08rem !important; }}

/* Plotly / dataframe / expander containers stay tight (they already
   carry their own padding) so the grid is dense without forcing
   orange section headers to touch. */
div[data-testid="element-container"]:has(.stPlotlyChart),
div[data-testid="element-container"]:has(.stDataFrame),
div[data-testid="element-container"]:has([data-testid="stExpander"]) {{
    margin-top: 0 !important; margin-bottom: 0.08rem !important;
}}

/* Section dividers */
hr {{ margin: 0.18rem 0 !important; border-color: {TOKENS["border_subtle"]} !important; }}

/* Compact metric cards */
div[data-testid="stMetric"] {{ padding: 0.3rem 0.5rem !important; }}

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
    padding: 0.04rem 0.32rem !important;
    line-height: 1.05 !important;
}}
.stDataFrame [role="row"] {{ min-height: 1.2rem !important; }}
.stDataFrame {{ margin-bottom: 0.1rem !important; }}

/* Plotly chart container: minimal padding, no gap below */
.stPlotlyChart {{ padding: 0.15rem !important; margin-bottom: 0.08rem !important; }}

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
h3 {{ margin-top: 0.1rem !important; margin-bottom: 0.05rem !important; }}

/* Form inputs: tighter */
.stTextInput > div > div input,
.stNumberInput > div > div input,
.stSelectbox > div > div {{ padding: 0.2rem 0.45rem !important; font-size: 0.75rem !important; }}
.stTextInput label, .stNumberInput label, .stSelectbox label, .stSlider label {{
    font-size: 0.6rem !important; margin-bottom: 0 !important;
}}

/* Sidebar: 190px, flat, always visible. Wider than 160 so section
   group headers (MARKET, RESEARCH, ANALYTICS, PORTFOLIO) stop
   clipping into "RESEA..." / "ANALY..." / "PORTF..." and there is
   room for both the label and the expand indicator without
   crowding. */
section[data-testid="stSidebar"] {{
    width: 190px !important; min-width: 190px !important; max-width: 190px !important;
    background-color: #080808 !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
    transform: none !important;
    visibility: visible !important;
}}
section[data-testid="stSidebar"] > div {{ padding-top: 0.3rem !important; background-color: #080808 !important; }}
section[data-testid="stSidebar"] .block-container {{ padding: 0.25rem 0.3rem !important; }}

/* Streamlit 1.50 injects a Material icon ("expand_more") via a
   DynamicIcon > MaterialFontIcon chain inside a StyledChevronContainer
   next to each sidebar nav section header. The chevron container is
   a plain div with an emotion class (no data-testid). We hide the
   icon at every layer: the testid span, any material class span,
   and the chevron container itself (targeted as the last child div
   of the section header wrapper). */
section[data-testid="stSidebarNav"] [data-testid="stIconMaterial"],
section[data-testid="stSidebarNav"] span.material-icons,
section[data-testid="stSidebarNav"] span.material-symbols-outlined {{
    font-size: 0 !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
    display: none !important;
    visibility: hidden !important;
}}
/* Hide the chevron container (StyledChevronContainer). It wraps the
   icon span and is the last child div inside the clickable section
   header. Without a data-testid we target it structurally. */
section[data-testid="stSidebarNav"] div > div:last-child:has([data-testid="stIconMaterial"]) {{
    display: none !important;
    width: 0 !important;
    overflow: hidden !important;
}}
/* Sidebar scope: any stray icon-like descendant that managed to
   evade the above (different Streamlit build, SSR, etc.). */
section[data-testid="stSidebar"] [data-testid="stIconMaterial"] {{
    font-size: 0 !important;
    display: none !important;
    visibility: hidden !important;
}}

/* Expander chevron: Streamlit renders keyboard_arrow_right/down via
   Material Icons DynamicIcon. Without the font loaded the raw icon
   name leaks as text ("_arrow..."). Hide the icon span and use a
   pure CSS triangle as the disclosure indicator instead. */
.stExpander [data-testid="stIconMaterial"] {{
    font-size: 0 !important;
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
}}
.stExpander summary::before {{
    content: "\\25B8";
    font-size: 0.7rem;
    color: {TOKENS["text_muted"]};
    margin-right: 0.35rem;
}}
.stExpander[open] summary::before {{
    content: "\\25BE";
}}

/* Kill the sidebar collapse / expand toggles. The sidebar is a
   fixed terminal style rail; the user never needs to hide it. */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
button[kind="header"][data-testid="baseButton-header"] {{
    display: none !important;
}}
section[data-testid="stSidebar"] .stMarkdown p {{ font-size: 0.65rem !important; line-height: 1.2 !important; margin: 0.05rem 0 !important; }}
section[data-testid="stSidebar"] .stMarkdown h3 {{
    font-size: 0.6rem !important; letter-spacing: 0.12em;
    margin: 0.45rem 0 0.15rem 0 !important;
    color: #FF8A2A !important;
    text-transform: uppercase;
    font-weight: 700 !important;
}}
/* Flatten the navigation entry. No rounded pill, no fill. Thin left border on active. */
section[data-testid="stSidebarNav"] ul {{ padding: 0 !important; margin: 0 !important; }}
section[data-testid="stSidebarNav"] li {{ list-style: none !important; margin: 0 !important; }}
section[data-testid="stSidebarNav"] a {{
    border-radius: 0 !important;
    padding: 0.22rem 0.5rem !important;
    font-family: {TOKENS["font_mono"]} !important;
    font-size: 0.66rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-left: 2px solid transparent !important;
    background-color: transparent !important;
}}
section[data-testid="stSidebarNav"] a:hover {{
    background-color: transparent !important;
    color: #E8E8EC !important;
}}
section[data-testid="stSidebarNav"] a[aria-current="page"] {{
    background-color: transparent !important;
    border-left: 2px solid #FF8A2A !important;
    color: #FF8A2A !important;
}}
/* Section header label rendered by st.navigation groups */
section[data-testid="stSidebarNav"] [data-testid="stSidebarNavSeparator"],
section[data-testid="stSidebarNav"] div[role="heading"],
section[data-testid="stSidebarNav"] span[class*="StyledNavSection"] {{
    font-family: {TOKENS["font_mono"]} !important;
    font-size: 0.6rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: #FF8A2A !important;
    margin: 0.5rem 0 0.1rem 0 !important;
    padding: 0 0.5rem !important;
}}

/* Buttons: smaller */
.stButton > button {{ padding: 0.18rem 0.55rem !important; font-size: 0.66rem !important; }}

/* Page title h1: max 0.5rem from first content. Zero top margin. */
h1 {{ margin-top: 0 !important; margin-bottom: 0.2rem !important; font-size: 1.1rem !important; line-height: 1.15 !important; }}
/* Custom styled_header wrapper margin (designs use a 1.25rem margin-bottom inline). */
.stMarkdown div[style*="margin-bottom: 1.25rem"] {{ margin-bottom: 0.3rem !important; }}
.stMarkdown div[style*="margin-bottom: 0.4rem"] {{ margin-bottom: 0.15rem !important; }}

/* Markdown body line height tighter */
.stMarkdown p {{ margin: 0.08rem 0 !important; line-height: 1.25 !important; }}

/* Cap any vertical gap and collapse spacing between stacked column rows */
[data-testid="stVerticalBlock"] > div {{ margin-top: 0 !important; margin-bottom: 0 !important; }}
[data-testid="stHorizontalBlock"] {{ margin-top: 0 !important; margin-bottom: 0 !important; }}
.stRadio > label {{ margin-bottom: 0 !important; }}
.stRadio div[role="radiogroup"] {{ gap: 0.3rem !important; }}

/* Numbers in any markdown body get monospace via the .num class */
.num {{ font-family: {TOKENS["font_mono"]} !important; font-weight: 500; }}

/* Loading skeleton pulse keyframes (used by terminal/utils/skeletons.py) */
@keyframes skel-pulse {{
    0%   {{ background-position: 200% 0; opacity: 0.6; }}
    50%  {{ background-position: -200% 0; opacity: 1.0; }}
    100% {{ background-position: 200% 0; opacity: 0.6; }}
}}

/* Row hover highlight on every dataframe. The glide grid puts rows in
   role=row; the hover background uses bg_hover so the cursor lands
   land on a slightly lighter band. Cells inherit the row hover. */
.stDataFrame [role="row"] {{ transition: background-color 0.08s linear; }}
.stDataFrame [role="row"]:hover {{ background-color: {TOKENS["bg_hover"]} !important; }}
.stDataFrame [role="row"]:hover [role="cell"] {{ background-color: transparent !important; }}

/* Freshness footer band sits at the bottom of every page. Tight,
   monospace, neutral. The string is rendered by render_freshness_footer
   in app/footer.py so the timestamp is always live. */
.freshness-footer {{
    border-top: 1px solid {TOKENS["border_subtle"]};
    margin-top: 0.2rem;
    padding: 0.15rem 0.4rem;
    font-family: {TOKENS["font_mono"]};
    font-size: 0.6rem;
    color: {TOKENS["text_muted"]};
    letter-spacing: 0.06em;
    text-transform: uppercase;
    display: flex;
    justify-content: space-between;
}}
</style>
"""


def inject_density() -> None:
    """Inject density overrides. No external font dependency -- the
    sidebar icon elements are hidden purely via CSS selectors above."""
    st.markdown(DENSITY_CSS, unsafe_allow_html=True)
