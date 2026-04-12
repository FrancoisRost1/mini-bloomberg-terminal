"""EARNINGS section for the Research page.

Next earnings date as a prominent KPI, plus last 4 quarters in a
compact table with color-coded surprise percentages. Degrades to
an OFF pill when data is unavailable.
"""

from __future__ import annotations

import streamlit as st

from style_inject import TOKENS
from terminal.utils.density import dense_kpi_rows, section_bar
from terminal.utils.error_handling import inline_status_line

_MONO = TOKENS["font_mono"]
_MUTED = TOKENS["text_muted"]
_PRIMARY = TOKENS["text_primary"]
_BORDER = TOKENS["border_subtle"]
_BG = TOKENS["bg_surface"]
_GREEN = "#00C853"
_RED = "#FF1744"

_TH = (
    f'font-family:{_MONO};font-size:0.58rem;color:{_MUTED};'
    f'text-transform:uppercase;letter-spacing:0.06em;font-weight:700;'
    f'padding:0.2rem 0.4rem;border-bottom:1px solid {_BORDER};text-align:left;'
)
_TD = (
    f'font-family:{_MONO};font-size:0.62rem;color:{_PRIMARY};'
    f'padding:0.15rem 0.4rem;border-bottom:1px solid {_BORDER};'
)


def _fmt_eps(val) -> str:
    if val is None:
        return "n/a"
    return f"{val:.2f}"


def _surprise_cell(pct) -> str:
    """Surprise % with green (beat) or red (miss) coloring."""
    if pct is None:
        return f'<td style="{_TD}text-align:right;">n/a</td>'
    display = f"{pct * 100:+.1f}%"
    color = _GREEN if pct >= 0 else _RED
    return f'<td style="{_TD}text-align:right;color:{color};font-weight:700;">{display}</td>'


def _history_table(history: list[dict]) -> str:
    rows = ""
    for q in history:
        rows += (
            f'<tr><td style="{_TD}">{q["quarter"]}</td>'
            f'<td style="{_TD}text-align:right;">{_fmt_eps(q["eps_estimate"])}</td>'
            f'<td style="{_TD}text-align:right;">{_fmt_eps(q["eps_actual"])}</td>'
            f'{_surprise_cell(q["surprise_pct"])}</tr>'
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;background:{_BG};">'
        f'<tr><th style="{_TH}">Quarter</th>'
        f'<th style="{_TH}text-align:right;">EPS Est</th>'
        f'<th style="{_TH}text-align:right;">EPS Actual</th>'
        f'<th style="{_TH}text-align:right;">Surprise</th></tr>'
        f'{rows}</table>'
    )


def render_earnings(earnings: dict) -> None:
    """Render the EARNINGS section on the Research page."""
    st.markdown(section_bar("EARNINGS", source="yfinance"), unsafe_allow_html=True)
    next_date = earnings.get("next_date")
    eps_est = earnings.get("eps_estimate")
    history = earnings.get("history", [])
    if not next_date and not history:
        st.markdown(inline_status_line("OFF", source="yfinance"), unsafe_allow_html=True)
        return

    items = [
        {"label": "NEXT EARNINGS", "value": next_date or "n/a"},
        {"label": "EPS ESTIMATE", "value": _fmt_eps(eps_est)},
    ]
    st.markdown(dense_kpi_rows(items, rows=1, min_cell_px=140), unsafe_allow_html=True)

    if history:
        st.markdown(_history_table(history), unsafe_allow_html=True)
