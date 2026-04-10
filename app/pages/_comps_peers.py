"""Comps page peer fundamentals table.

Pulled out of comps_relative_value.py so the page module stays under
the line budget. Builds a side-by-side fundamentals comparison for
the active ticker plus four sector peers, highlighting the active
row in the dataframe.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from style_inject import TOKENS

from terminal.utils.density import section_bar
from terminal.utils.error_handling import inline_status_line, is_error
from terminal.utils.formatting import format_metric
from terminal.utils.sector_peers import peers_for


METRIC_COLS: list[tuple[str, str, str]] = [
    # (display label, ratio key, format)
    ("EV/EBITDA",      "ev_ebitda",       "ratio"),
    ("P/E",            "pe_ratio",        "ratio"),
    ("EBITDA Margin",  "ebitda_margin",   "pct"),
    ("Rev Growth",     "revenue_growth",  "pct"),
    ("ROE",            "roe",             "pct"),
    ("ND/EBITDA",      "net_debt_ebitda", "ratio"),
    ("FCF Conv",       "fcf_conversion",  "pct"),
]


def render_peer_fundamentals(data_manager, ticker: str, sector: str | None) -> None:
    """Fetch the active ticker plus four sector peers and render a
    fundamentals comparison table. The active row is highlighted with
    the project accent color.
    """
    st.markdown(section_bar("PEER FUNDAMENTALS (5)", source="FMP"), unsafe_allow_html=True)
    peers = peers_for(sector, ticker, limit=5)
    rows: list[dict] = []
    missing: list[str] = []
    for tkr in peers:
        f = data_manager.get_fundamentals(tkr)
        if is_error(f):
            missing.append(tkr)
            continue
        ratios = f.key_ratios or {}
        row = {"Ticker": tkr}
        for label, key, fmt in METRIC_COLS:
            row[label] = format_metric(ratios.get(key), fmt)
        rows.append(row)
    if not rows:
        st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
        return
    df = pd.DataFrame(rows)
    accent = TOKENS["accent_primary"]
    bg = TOKENS["bg_active"]

    def _highlight_active(row):
        if row["Ticker"].upper() == ticker.upper():
            return [f"background-color: {bg}; color: {accent}; font-weight: 700;"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(_highlight_active, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)
    if missing:
        st.caption(f"Missing peer data: {', '.join(missing)}")
