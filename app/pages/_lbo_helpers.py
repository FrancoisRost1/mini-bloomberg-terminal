"""LBO Quick Calc helpers.

Pulled out of lbo_quick_calc.py so the page module stays under the
~150 line budget. Renders:

- Sources and Uses table at entry (senior + sub debt + sponsor equity)
- Three quick credit metrics at the entry capital structure
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from style_inject import TOKENS
from terminal.utils.density import dense_kpi_row, dense_kpi_rows, section_bar, signed_color
from terminal.utils.formatting import fmt_money, fmt_pct, fmt_ratio


# Senior / sub split applied to the total debt for the S&U table.
# Real deals tier debt by tranche; this gives the S&U the same shape
# without forcing the user to specify a full term sheet.
SENIOR_TRANCHE = 0.70
SUB_TRANCHE = 0.30


def render_assumptions_row(assumptions: dict) -> None:
    """Dense KPI row showing the active LBO scenario inputs."""
    entry_ev = assumptions.get("entry_ebitda", 0) * assumptions.get("entry_multiple", 0)
    items = [
        {"label": "ENTRY EV", "value": fmt_money(entry_ev)},
        {"label": "ENTRY MULT", "value": f"{assumptions.get('entry_multiple', 0):.1f}x"},
        {"label": "EBITDA", "value": fmt_money(assumptions.get("entry_ebitda", 0))},
        {"label": "LEVERAGE", "value": f"{assumptions.get('leverage', 0):.1f}x"},
        {"label": "EXIT MULT", "value": f"{assumptions.get('exit_multiple', 0):.1f}x"},
        {"label": "HOLD", "value": f"{assumptions.get('hold_period', 5)}yr"},
        {"label": "REV GROWTH", "value": fmt_pct(assumptions.get("revenue_growth", 0))},
    ]
    label = (f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.55rem;'
             f'color:{TOKENS["text_muted"]};text-transform:uppercase;'
             f'letter-spacing:0.08em;font-weight:700;margin-bottom:0.2rem;">LBO ASSUMPTIONS</div>')
    st.markdown(label + dense_kpi_rows(items, rows=1, min_cell_px=110), unsafe_allow_html=True)


def render_credit_metrics(result, debt_rate: float = 0.06) -> None:
    """Three quick credit ratios at the entry capital structure."""
    st.markdown(section_bar("CREDIT METRICS (ENTRY)"), unsafe_allow_html=True)
    ebitda = float(result["entry_ebitda"]) or float("nan")
    debt = float(result["entry_debt"])
    interest = debt * float(debt_rate)
    debt_ebitda = (debt / ebitda) if ebitda and ebitda == ebitda and ebitda > 0 else float("nan")
    icov = (ebitda / interest) if interest > 0 else float("nan")
    sponsor = float(result["sponsor_equity"])
    # FCF proxy. EBITDA minus a 45% drag for taxes / capex / NWC at the
    # default model assumptions. Same haircut the LBO engine applies in
    # the first projection year.
    fcf_proxy = ebitda * 0.55
    fcf_yield = (fcf_proxy / sponsor) if sponsor > 0 else float("nan")
    items = [
        {"label": "DEBT / EBITDA", "value": fmt_ratio(debt_ebitda),
         "value_color": signed_color(-(debt_ebitda - 4.0)) if debt_ebitda == debt_ebitda else None},
        {"label": "INT COVERAGE", "value": fmt_ratio(icov, suffix="x"),
         "value_color": signed_color(icov - 2.0) if icov == icov else None},
        {"label": "FCF YIELD (SPONSOR EQ)", "value": fmt_pct(fcf_yield),
         "value_color": signed_color(fcf_yield - 0.05) if fcf_yield == fcf_yield else None},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=140), unsafe_allow_html=True)


def render_sources_and_uses(result) -> None:
    """Sources and Uses table at entry: senior / sub debt + sponsor equity vs entry EV + fees."""
    st.markdown(section_bar("SOURCES AND USES"), unsafe_allow_html=True)
    entry_ev = float(result["entry_ev"])
    fees = float(result["fees"])
    debt = float(result["entry_debt"])
    sponsor = float(result["sponsor_equity"])
    senior = debt * SENIOR_TRANCHE
    sub = debt * SUB_TRANCHE
    total_uses = entry_ev + fees
    total_sources = senior + sub + sponsor

    rows = [
        ("Sources", "Senior Debt (TLB)",        senior,        _safe_pct(senior, total_sources)),
        ("Sources", "Subordinated Debt",        sub,           _safe_pct(sub, total_sources)),
        ("Sources", "Sponsor Equity",           sponsor,       _safe_pct(sponsor, total_sources)),
        ("Sources", "TOTAL SOURCES",            total_sources, 1.0),
        ("Uses",    "Purchase Enterprise Value", entry_ev,     _safe_pct(entry_ev, total_uses)),
        ("Uses",    "Transaction Fees",          fees,         _safe_pct(fees, total_uses)),
        ("Uses",    "TOTAL USES",                total_uses,   1.0),
    ]
    df = pd.DataFrame([
        {"Side": s, "Item": i, "Amount": fmt_money(v), "% Total": f"{p * 100:.1f}%"}
        for s, i, v, p in rows
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
    if abs(total_sources - total_uses) > 1.0:
        st.caption(
            f"S&U MISMATCH | sources {fmt_money(total_sources)} vs uses {fmt_money(total_uses)}"
        )


def _safe_pct(part: float, whole: float) -> float:
    return (part / whole) if whole else 0.0
