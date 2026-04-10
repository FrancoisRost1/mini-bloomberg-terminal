"""
STREAMLIT DESIGN SYSTEM
Institutional finance aesthetic. Dense, sharp, data-first.
Not literal terminal imitation.

Usage:
    from style_inject import inject_styles, TOKENS
    inject_styles()

Accent color is auto-detected from the project folder name.
No manual setup needed. To override manually, set TOKENS["accent_primary"]
before calling inject_styles().
"""

import streamlit as st
import os


# ─────────────────────────────────────────────
# PROJECT ACCENT AUTO-DETECTION
# ─────────────────────────────────────────────
PROJECT_ACCENTS = {
    "lbo-engine":                  "#D4882B",   # Amber
    "pe-target-screener":          "#C8962E",   # Warm amber
    "factor-backtest-engine":      "#4A7FB5",   # Steel blue
    "ma-database":                 "#3D8A7A",   # Muted teal
    "volatility-regime-engine":    "#B86A3A",   # Muted red-amber
    "tsmom-engine":                "#4A7FB5",   # Steel blue
    "strategy-robustness-lab":     "#B8703A",   # Muted amber-red
    "portfolio-optimization-engine": "#5A7A9E", # Cool grey-blue
    "options-pricing-engine":      "#7C6DB0",   # Muted violet
    "ai-research-agent":           "#C89040",   # Neutral amber
    "mini-bloomberg-terminal":     "#E07020",   # Bloomberg orange
}


def _detect_project_accent():
    """Walk up from cwd looking for a matching project folder name."""
    path = os.path.abspath(os.getcwd())
    for _ in range(10):
        folder = os.path.basename(path)
        if folder in PROJECT_ACCENTS:
            return PROJECT_ACCENTS[folder]
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return None


# ─────────────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────────────
TOKENS = {
    # Background layers (charcoal, not navy)
    "bg_base": "#0A0A0F",        # Page background
    "bg_surface": "#121218",     # Cards, containers
    "bg_elevated": "#1A1A22",    # Elevated panels
    "bg_hover": "#22222C",       # Hover states
    "bg_active": "#2A2A36",      # Active/selected states

    # Accent colors (muted, professional)
    # Default is neutral amber. Override accent_primary per project.
    # See DESIGN.md accent guide for project-specific colors.
    "accent_primary": "#D4882B",    # Amber (default, override per project)
    "accent_secondary": "#7A8A9E",  # Steel blue-grey
    "accent_success": "#3D9A50",    # Muted green (up)
    "accent_warning": "#C8962E",    # Muted amber
    "accent_danger": "#C43D3D",     # Muted red (down)
    "accent_info": "#4A7FB5",       # Muted blue

    # Text hierarchy
    "text_primary": "#E8E8EC",      # Main text
    "text_secondary": "#8E8E9A",    # Subdued text
    "text_muted": "#55555F",        # Hints, placeholders
    "text_on_accent": "#FFFFFF",    # Text on accent backgrounds

    # Borders
    "border_subtle": "rgba(255, 255, 255, 0.04)",
    "border_default": "rgba(255, 255, 255, 0.08)",
    "border_strong": "rgba(255, 255, 255, 0.14)",

    # Spacing scale (rem)
    "space_xs": "0.2rem",
    "space_sm": "0.4rem",
    "space_md": "0.75rem",
    "space_lg": "1.1rem",
    "space_xl": "1.5rem",
    "space_2xl": "2rem",

    # Typography
    "font_display": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "font_body": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "font_mono": "'JetBrains Mono', 'SF Mono', 'Consolas', monospace",
    "text_xs": "0.7rem",
    "text_sm": "0.8rem",
    "text_base": "0.875rem",
    "text_lg": "1rem",
    "text_xl": "1.125rem",
    "text_2xl": "1.25rem",
    "text_3xl": "1.5rem",

    # Radius (sharp, but not brutalist)
    "radius_sm": "2px",
    "radius_md": "3px",
    "radius_lg": "4px",

    # Shadows (ultra-subtle, structural only)
    "shadow_sm": "0 1px 2px rgba(0,0,0,0.2)",
    "shadow_md": "0 2px 6px rgba(0,0,0,0.25)",
}


def inject_styles():
    """
    Call at the top of your app (after st.set_page_config).
    Auto-detects project accent from folder name. No setup needed.
    """
    # Auto-detect accent if not manually overridden
    detected = _detect_project_accent()
    if detected and TOKENS["accent_primary"] == "#D4882B":
        TOKENS["accent_primary"] = detected

    css = f"""
    <style>
    /* ── FONTS ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ── BASE ── */
    .stApp {{
        background-color: {TOKENS["bg_base"]};
        font-family: {TOKENS["font_body"]};
        color: {TOKENS["text_primary"]};
    }}

    .block-container {{
        padding-top: 1.25rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 1400px;
    }}

    /* ── TYPOGRAPHY ── */
    h1 {{
        font-family: {TOKENS["font_display"]} !important;
        font-weight: 600 !important;
        color: {TOKENS["text_primary"]} !important;
        font-size: {TOKENS["text_3xl"]} !important;
        letter-spacing: -0.01em !important;
        margin-bottom: 0.15rem !important;
    }}

    h2 {{
        font-family: {TOKENS["font_display"]} !important;
        font-weight: 600 !important;
        color: {TOKENS["text_primary"]} !important;
        font-size: {TOKENS["text_2xl"]} !important;
    }}

    h3 {{
        font-family: {TOKENS["font_display"]} !important;
        font-weight: 600 !important;
        color: {TOKENS["text_secondary"]} !important;
        font-size: {TOKENS["text_sm"]} !important;
        text-transform: uppercase;
        letter-spacing: 0.08em !important;
    }}

    p, span, label, .stMarkdown {{
        font-family: {TOKENS["font_body"]} !important;
        color: {TOKENS["text_secondary"]};
        font-size: {TOKENS["text_base"]} !important;
    }}

    /* ── SIDEBAR ── */
    section[data-testid="stSidebar"] {{
        background-color: {TOKENS["bg_surface"]} !important;
        border-right: 1px solid {TOKENS["border_default"]} !important;
    }}

    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {{
        color: {TOKENS["text_primary"]} !important;
    }}

    /* ── METRIC CARDS ── */
    div[data-testid="stMetric"] {{
        background: {TOKENS["bg_surface"]};
        border: 1px solid {TOKENS["border_default"]};
        border-radius: {TOKENS["radius_md"]};
        padding: 0.75rem 1rem;
        box-shadow: {TOKENS["shadow_sm"]};
    }}

    div[data-testid="stMetric"] label {{
        color: {TOKENS["text_muted"]} !important;
        font-size: {TOKENS["text_xs"]} !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        font-family: {TOKENS["font_mono"]} !important;
        font-weight: 600 !important;
        color: {TOKENS["text_primary"]} !important;
        font-size: {TOKENS["text_2xl"]} !important;
    }}

    div[data-testid="stMetricDelta"] {{
        font-family: {TOKENS["font_mono"]} !important;
        font-weight: 500 !important;
    }}

    /* ── FORMS & INPUTS ── */
    .stTextInput > div > div,
    .stNumberInput > div > div,
    .stTextArea > div > div {{
        background-color: {TOKENS["bg_elevated"]} !important;
        border: 1px solid {TOKENS["border_default"]} !important;
        border-radius: {TOKENS["radius_sm"]} !important;
        color: {TOKENS["text_primary"]} !important;
        font-family: {TOKENS["font_body"]} !important;
    }}

    .stTextInput > div > div:focus-within,
    .stNumberInput > div > div:focus-within,
    .stTextArea > div > div:focus-within {{
        border-color: {TOKENS["accent_primary"]} !important;
        box-shadow: none !important;
    }}

    input, textarea {{
        color: {TOKENS["text_primary"]} !important;
        font-family: {TOKENS["font_body"]} !important;
        caret-color: {TOKENS["accent_primary"]} !important;
    }}

    input::placeholder, textarea::placeholder {{
        color: {TOKENS["text_muted"]} !important;
    }}

    .stSelectbox > div > div,
    .stMultiSelect > div > div {{
        background-color: {TOKENS["bg_elevated"]} !important;
        border: 1px solid {TOKENS["border_default"]} !important;
        border-radius: {TOKENS["radius_sm"]} !important;
        color: {TOKENS["text_primary"]} !important;
    }}

    .stSelectbox > div > div:focus-within,
    .stMultiSelect > div > div:focus-within {{
        border-color: {TOKENS["accent_primary"]} !important;
        box-shadow: none !important;
    }}

    .stSlider > div > div > div {{
        background-color: {TOKENS["bg_hover"]} !important;
    }}

    .stSlider [data-testid="stThumbValue"] {{
        color: {TOKENS["text_primary"]} !important;
        font-family: {TOKENS["font_mono"]} !important;
    }}

    .stDateInput > div > div,
    .stTimeInput > div > div {{
        background-color: {TOKENS["bg_elevated"]} !important;
        border: 1px solid {TOKENS["border_default"]} !important;
        border-radius: {TOKENS["radius_sm"]} !important;
    }}

    .stCheckbox label, .stRadio label {{
        color: {TOKENS["text_secondary"]} !important;
        font-family: {TOKENS["font_body"]} !important;
    }}

    .stTextInput label,
    .stNumberInput label,
    .stTextArea label,
    .stSelectbox label,
    .stMultiSelect label,
    .stSlider label,
    .stDateInput label,
    .stTimeInput label,
    .stRadio label p,
    .stCheckbox label span {{
        color: {TOKENS["text_secondary"]} !important;
        font-weight: 500 !important;
        font-size: {TOKENS["text_sm"]} !important;
        margin-bottom: 0.15rem !important;
    }}

    /* ── BUTTONS ── */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button {{
        background-color: {TOKENS["accent_primary"]} !important;
        color: {TOKENS["text_on_accent"]} !important;
        border: none !important;
        border-radius: {TOKENS["radius_sm"]} !important;
        font-family: {TOKENS["font_body"]} !important;
        font-weight: 600 !important;
        font-size: {TOKENS["text_sm"]} !important;
        padding: 0.45rem 1.1rem !important;
    }}

    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button:hover {{
        opacity: 0.88;
    }}

    .stButton > button[kind="secondary"],
    .stButton > button:not([kind]) {{
        background-color: transparent !important;
        color: {TOKENS["text_secondary"]} !important;
        border: 1px solid {TOKENS["border_default"]} !important;
        border-radius: {TOKENS["radius_sm"]} !important;
        font-family: {TOKENS["font_body"]} !important;
        font-weight: 500 !important;
        font-size: {TOKENS["text_sm"]} !important;
        padding: 0.45rem 1.1rem !important;
    }}

    .stButton > button[kind="secondary"]:hover,
    .stButton > button:not([kind]):hover {{
        background-color: {TOKENS["bg_hover"]} !important;
        border-color: {TOKENS["text_muted"]} !important;
        color: {TOKENS["text_primary"]} !important;
    }}

    /* ── TABLES & DATAFRAMES ── */
    .stDataFrame {{
        border: 1px solid {TOKENS["border_default"]} !important;
        border-radius: {TOKENS["radius_md"]} !important;
        overflow: hidden;
    }}

    .stDataFrame [data-testid="glideDataEditor"] {{
        border-radius: {TOKENS["radius_md"]} !important;
    }}

    /* ── CHARTS ── */
    .stPlotlyChart, .stVegaLiteChart {{
        background: {TOKENS["bg_surface"]} !important;
        border: 1px solid {TOKENS["border_subtle"]} !important;
        border-radius: {TOKENS["radius_md"]} !important;
        padding: 0.5rem !important;
        box-shadow: {TOKENS["shadow_sm"]};
    }}

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        background: transparent;
        border-bottom: 1px solid {TOKENS["border_default"]};
        border-radius: 0;
        padding: 0;
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 0 !important;
        color: {TOKENS["text_muted"]} !important;
        font-family: {TOKENS["font_body"]} !important;
        font-weight: 500 !important;
        font-size: {TOKENS["text_sm"]} !important;
        padding: 0.5rem 1rem !important;
        border-bottom: 2px solid transparent !important;
    }}

    .stTabs [aria-selected="true"] {{
        background-color: transparent !important;
        color: {TOKENS["accent_primary"]} !important;
        border-bottom: 2px solid {TOKENS["accent_primary"]} !important;
    }}

    /* ── EXPANDERS ── */
    .streamlit-expanderHeader {{
        background-color: {TOKENS["bg_surface"]} !important;
        border: 1px solid {TOKENS["border_default"]} !important;
        border-radius: {TOKENS["radius_sm"]} !important;
        color: {TOKENS["text_primary"]} !important;
        font-weight: 500 !important;
    }}

    /* ── ALERTS ── */
    .stAlert {{
        border-radius: {TOKENS["radius_sm"]} !important;
        font-family: {TOKENS["font_body"]} !important;
    }}

    /* ── DIVIDERS ── */
    hr {{
        border-color: {TOKENS["border_subtle"]} !important;
        margin: {TOKENS["space_lg"]} 0 !important;
    }}

    /* ── SCROLLBAR ── */
    ::-webkit-scrollbar {{
        width: 5px;
        height: 5px;
    }}
    ::-webkit-scrollbar-track {{
        background: {TOKENS["bg_base"]};
    }}
    ::-webkit-scrollbar-thumb {{
        background: {TOKENS["text_muted"]};
        border-radius: 2px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {TOKENS["text_secondary"]};
    }}

    /* ── FORM CONTAINER ── */
    [data-testid="stForm"] {{
        background: {TOKENS["bg_surface"]} !important;
        border: 1px solid {TOKENS["border_default"]} !important;
        border-radius: {TOKENS["radius_md"]} !important;
        padding: 1rem !important;
        box-shadow: {TOKENS["shadow_sm"]};
    }}

    /* ── TOOLTIPS ── */
    .stTooltipIcon {{
        color: {TOKENS["text_muted"]} !important;
    }}

    /* ── TOAST ── */
    .stToast {{
        background: {TOKENS["bg_elevated"]} !important;
        border: 1px solid {TOKENS["border_default"]} !important;
        border-radius: {TOKENS["radius_sm"]} !important;
    }}

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPER COMPONENTS
# ─────────────────────────────────────────────

def styled_header(title: str, subtitle: str = ""):
    """
    Page header. Clean, tight.
    Usage: styled_header("LBO Engine", "AAPL | Base Case | 5yr Hold")
    """
    html = f"""
    <div style="margin-bottom: 1.25rem;">
        <h1 style="
            font-family: {TOKENS["font_display"]};
            font-weight: 600;
            font-size: 1.5rem;
            color: {TOKENS["text_primary"]};
            letter-spacing: -0.01em;
            margin: 0;
            line-height: 1.3;
        ">{title}</h1>
        {"<p style='font-size: 0.8rem; color: " + TOKENS["text_muted"] + "; margin-top: 0.2rem; font-family: " + TOKENS["font_body"] + ";'>" + subtitle + "</p>" if subtitle else ""}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def styled_card(content: str, accent_color: str = None):
    """
    Content card. Tight padding, sharp corners, optional left border.
    Usage: styled_card("Strong quality profile, near fair value.", accent_color=TOKENS["accent_primary"])
    """
    accent = f"border-left: 3px solid {accent_color};" if accent_color else ""
    html = f"""
    <div style="
        background: {TOKENS["bg_surface"]};
        border: 1px solid {TOKENS["border_default"]};
        border-radius: {TOKENS["radius_md"]};
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
        box-shadow: {TOKENS["shadow_sm"]};
        {accent}
    ">
        <span style="color: {TOKENS["text_secondary"]}; font-family: {TOKENS["font_body"]}; font-size: 0.85rem; line-height: 1.5;">
            {content}
        </span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def styled_kpi(label: str, value: str, delta: str = "", delta_color: str = ""):
    """
    KPI block. Monospace value, compact layout.
    Usage: styled_kpi("SPOT ($)", "$259", delta="+3.2%", delta_color=TOKENS["accent_success"])
    """
    delta_html = ""
    if delta:
        dc = delta_color or TOKENS["accent_success"]
        delta_html = f'<span style="font-family: {TOKENS["font_mono"]}; font-size: 0.75rem; color: {dc}; font-weight: 500;">{delta}</span>'

    html = f"""
    <div style="
        background: {TOKENS["bg_surface"]};
        border: 1px solid {TOKENS["border_default"]};
        border-radius: {TOKENS["radius_md"]};
        padding: 0.65rem 0.9rem;
        box-shadow: {TOKENS["shadow_sm"]};
    ">
        <div style="
            font-size: 0.65rem;
            color: {TOKENS["text_muted"]};
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 600;
            font-family: {TOKENS["font_body"]};
            margin-bottom: 0.3rem;
        ">{label}</div>
        <div style="display: flex; align-items: baseline; gap: 0.5rem;">
            <span style="
                font-family: {TOKENS["font_mono"]};
                font-size: 1.35rem;
                font-weight: 600;
                color: {TOKENS["text_primary"]};
            ">{value}</span>
            {delta_html}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def styled_divider():
    """Thin horizontal rule."""
    st.markdown(
        f'<hr style="border: none; border-top: 1px solid {TOKENS["border_subtle"]}; margin: 1rem 0;">',
        unsafe_allow_html=True
    )


def styled_section_label(text: str):
    """
    Small uppercase label for sections.
    Usage: styled_section_label("FILTERS")
    """
    html = f"""
    <div style="
        font-size: 0.65rem;
        color: {TOKENS["text_muted"]};
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 600;
        font-family: {TOKENS["font_body"]};
        margin-bottom: 0.5rem;
        margin-top: 0.75rem;
    ">{text}</div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PLOTLY THEME
# ─────────────────────────────────────────────

PLOTLY_THEME = dict(
    template="plotly_dark",
    layout=dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, -apple-system, sans-serif",
            color=TOKENS["text_secondary"],
            size=11,
        ),
        title=dict(
            font=dict(
                family="Inter, -apple-system, sans-serif",
                size=13,
                color=TOKENS["text_primary"],
            ),
            x=0,
            xanchor="left",
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            linecolor="rgba(255,255,255,0.08)",
            zerolinecolor="rgba(255,255,255,0.04)",
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.04)",
            linecolor="rgba(255,255,255,0.08)",
            zerolinecolor="rgba(255,255,255,0.04)",
            tickfont=dict(size=10),
        ),
        margin=dict(l=40, r=16, t=40, b=32),
        colorway=[
            TOKENS["accent_primary"],   # Project accent
            TOKENS["accent_info"],      # Muted blue
            TOKENS["accent_success"],   # Muted green
            TOKENS["accent_secondary"], # Steel grey
            TOKENS["accent_warning"],   # Muted amber
            TOKENS["accent_danger"],    # Muted red
            "#7C6DB0",                  # Dusty purple
            "#4D9A8A",                  # Muted teal
        ],
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TOKENS["text_secondary"], size=10),
        ),
    ),
)


def apply_plotly_theme(fig):
    """
    Apply the institutional theme to any Plotly figure.
    Reads TOKENS at call time, so accent overrides are reflected.

    Usage:
        fig = px.line(df, x="date", y="revenue")
        apply_plotly_theme(fig)
        st.plotly_chart(fig, use_container_width=True)
    """
    # Rebuild colorway from current TOKENS in case accent was overridden
    layout = dict(PLOTLY_THEME["layout"])
    layout["colorway"] = [
        TOKENS["accent_primary"],
        TOKENS["accent_info"],
        TOKENS["accent_success"],
        TOKENS["accent_secondary"],
        TOKENS["accent_warning"],
        TOKENS["accent_danger"],
        "#7C6DB0",
        "#4D9A8A",
    ]
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────
# STREAMLIT THEME CONFIG
# ─────────────────────────────────────────────
TOML_THEME = """
# .streamlit/config.toml
# primaryColor is auto-detected at runtime by style_inject.py
# This value is the fallback default (amber)

[theme]
base = "dark"
primaryColor = "#D4882B"
backgroundColor = "#0A0A0F"
secondaryBackgroundColor = "#121218"
textColor = "#E8E8EC"
font = "sans serif"
"""
