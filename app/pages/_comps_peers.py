"""Comps page peer fundamentals table.

Pulled out of comps_relative_value.py so the page module stays under
the line budget. Builds a side-by-side fundamentals comparison for
the active ticker plus four sector peers, highlighting the active
row and appending a sector median row so the delta vs peers reads
off the page.
"""

from __future__ import annotations

import math

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


def _median_ignoring_nan(values: list[float]) -> float:
    clean = [v for v in values if v is not None and isinstance(v, (int, float)) and not math.isnan(v)]
    if not clean:
        return float("nan")
    clean.sort()
    n = len(clean)
    mid = n // 2
    if n % 2 == 1:
        return float(clean[mid])
    return float((clean[mid - 1] + clean[mid]) / 2.0)


def render_peer_fundamentals(data_manager, ticker: str, sector: str | None) -> None:
    """Fetch the active ticker plus four sector peers and render a
    fundamentals comparison table. The active row is highlighted with
    the project accent color and a sector median row is appended so
    the user can read the delta against peers at a glance.
    """
    st.markdown(section_bar("PEER FUNDAMENTALS + SECTOR MEDIAN", source="FMP"), unsafe_allow_html=True)
    peers = peers_for(sector, ticker, limit=5)
    rows: list[dict] = []
    raw_values: dict[str, list[float]] = {label: [] for label, _, _ in METRIC_COLS}
    missing: list[str] = []
    for tkr in peers:
        f = data_manager.get_fundamentals(tkr)
        if is_error(f):
            missing.append(tkr)
            continue
        ratios = f.key_ratios or {}
        row = {"Ticker": tkr}
        for label, key, fmt in METRIC_COLS:
            val = ratios.get(key)
            raw_values[label].append(float(val) if val is not None and isinstance(val, (int, float)) else float("nan"))
            row[label] = format_metric(val, fmt)
        rows.append(row)
    if not rows:
        st.markdown(inline_status_line("OFF", source="FMP"), unsafe_allow_html=True)
        return
    # Sector median (computed across the peers we DID fetch).
    median_row = {"Ticker": "Sector median"}
    for label, _key, fmt in METRIC_COLS:
        median_row[label] = format_metric(_median_ignoring_nan(raw_values[label]), fmt)
    rows.append(median_row)
    df = pd.DataFrame(rows)
    accent = TOKENS["accent_primary"]
    # Vivid orange tint so the target row stands out at a glance.
    active_bg = "rgba(224,112,32,0.22)"
    median_bg = TOKENS["bg_elevated"]
    muted = TOKENS["text_muted"]

    def _highlight(row):
        label = str(row["Ticker"]).upper()
        if label == ticker.upper():
            return [
                f"background-color: {active_bg}; color: {accent}; "
                "font-weight: 800; border-top: 1px solid rgba(224,112,32,0.55); "
                "border-bottom: 1px solid rgba(224,112,32,0.55);"
            ] * len(row)
        if label == "SECTOR MEDIAN":
            return [
                f"background-color: {median_bg}; color: {muted}; "
                "font-style: italic; font-weight: 600; "
                "border-top: 1px solid rgba(255,255,255,0.14);"
            ] * len(row)
        return [""] * len(row)

    styled = df.style.apply(_highlight, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)
    if missing:
        st.caption(f"Missing peer data: {', '.join(missing)}")
