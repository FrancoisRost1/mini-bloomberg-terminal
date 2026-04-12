"""OWNERSHIP section for the Research page.

Top 5 institutional holders and last 5 insider transactions in dense
Bloomberg-style HTML tables. Degrades to OFF pill when unavailable.
"""

from __future__ import annotations

import streamlit as st

from style_inject import TOKENS
from terminal.utils.density import section_bar
from terminal.utils.error_handling import inline_status_line
from terminal.utils.formatting import fmt_money

_MONO = TOKENS["font_mono"]
_MUTED = TOKENS["text_muted"]
_PRIMARY = TOKENS["text_primary"]
_SECONDARY = TOKENS["text_secondary"]
_BORDER = TOKENS["border_subtle"]
_BG = TOKENS["bg_surface"]

_TH = (
    f'font-family:{_MONO};font-size:0.58rem;color:{_MUTED};'
    f'text-transform:uppercase;letter-spacing:0.06em;font-weight:700;'
    f'padding:0.2rem 0.4rem;border-bottom:1px solid {_BORDER};text-align:left;'
)
_TD = (
    f'font-family:{_MONO};font-size:0.62rem;color:{_PRIMARY};'
    f'padding:0.15rem 0.4rem;border-bottom:1px solid {_BORDER};'
)


def _fmt_shares(val) -> str:
    if val is None:
        return "n/a"
    v = float(val)
    if v >= 1e9:
        return f"{v / 1e9:.1f}B"
    if v >= 1e6:
        return f"{v / 1e6:.1f}M"
    if v >= 1e3:
        return f"{v / 1e3:.0f}K"
    return f"{v:,.0f}"


def _fmt_pct_held(val) -> str:
    if val is None:
        return "n/a"
    return f"{float(val) * 100:.2f}%"


def _institutions_table(institutions: list[dict]) -> str:
    rows = ""
    for inst in institutions:
        rows += (
            f'<tr><td style="{_TD}">{inst["holder"]}</td>'
            f'<td style="{_TD}text-align:right;">{_fmt_shares(inst["shares"])}</td>'
            f'<td style="{_TD}text-align:right;">{_fmt_pct_held(inst["pct_held"])}</td></tr>'
        )
    cap = (
        f'<caption style="font-family:{_MONO};font-size:0.58rem;color:{_MUTED};'
        f'text-transform:uppercase;letter-spacing:0.06em;font-weight:700;'
        f'text-align:left;caption-side:top;padding:0.2rem 0 0.5rem 0;">Top Institutional Holders</caption>'
    )
    return (
        f'<table style="width:100%;border-collapse:collapse;background:{_BG};margin-top:0.3rem;">'
        f'{cap}'
        f'<tr><th style="{_TH}">Holder</th>'
        f'<th style="{_TH}text-align:right;">Shares</th>'
        f'<th style="{_TH}text-align:right;">% Out</th></tr>'
        f'{rows}</table>'
    )


def _insiders_table(insiders: list[dict]) -> str:
    rows = ""
    for txn in insiders:
        val = fmt_money(txn["value"]) if txn["value"] is not None else "n/a"
        label = txn["transaction"]
        if len(label) > 30:
            label = label[:30] + "..."
        rows += (
            f'<tr><td style="{_TD}">{txn["date"]}</td>'
            f'<td style="{_TD}">{txn["insider"]}</td>'
            f'<td style="{_TD}">{label}</td>'
            f'<td style="{_TD}text-align:right;">{_fmt_shares(txn["shares"])}</td>'
            f'<td style="{_TD}text-align:right;">{val}</td></tr>'
        )
    cap = (
        f'<caption style="font-family:{_MONO};font-size:0.58rem;color:{_MUTED};'
        f'text-transform:uppercase;letter-spacing:0.06em;font-weight:700;'
        f'text-align:left;caption-side:top;padding:0.2rem 0 0.5rem 0;">Recent Insider Transactions</caption>'
    )
    return (
        f'<table style="width:100%;border-collapse:collapse;background:{_BG};margin-top:0.3rem;">'
        f'{cap}'
        f'<tr><th style="{_TH}">Date</th><th style="{_TH}">Insider</th>'
        f'<th style="{_TH}">Transaction</th>'
        f'<th style="{_TH}text-align:right;">Shares</th>'
        f'<th style="{_TH}text-align:right;">Value</th></tr>'
        f'{rows}</table>'
    )


def render_ownership(ownership: dict) -> None:
    """Render the OWNERSHIP section on the Research page."""
    st.markdown(section_bar("OWNERSHIP", source="yfinance"), unsafe_allow_html=True)
    institutions = ownership.get("institutions", [])
    insiders = ownership.get("insiders", [])
    if not institutions and not insiders:
        st.markdown(inline_status_line("OFF", source="yfinance"), unsafe_allow_html=True)
        return
    if institutions:
        st.markdown(_institutions_table(institutions), unsafe_allow_html=True)
    if insiders:
        st.markdown(_insiders_table(insiders), unsafe_allow_html=True)
