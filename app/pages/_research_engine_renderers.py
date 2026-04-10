"""Per engine renderers for the Research page tabs.

Each function takes a single engine result dict and renders the
detailed dense KPI grid for that engine. Pure rendering, no data
fetching. Split from _research_page_helpers.py to keep both modules
under the per module line budget.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from terminal.utils.density import dense_kpi_row, signed_color


def render_pe_engine(e: dict[str, Any]) -> None:
    items = [
        {"label": "PE SCORE", "value": f"{e['pe_score']:.1f}",
         "value_color": signed_color(e["pe_score"] - 50)},
        {"label": "RED FLAGS", "value": str(len(e.get("red_flags", [])))},
        {"label": "VALID", "value": str(e.get("valid_metric_count", 0))},
    ]
    for k, v in e.get("per_metric_scores", {}).items():
        items.append({
            "label": k.upper().replace("_", " "),
            "value": f"{v:.0f}" if v == v else "n/a",
            "value_color": signed_color(v - 50) if v == v else None,
        })
    st.markdown(dense_kpi_row(items, min_cell_px=90), unsafe_allow_html=True)
    if e.get("red_flags"):
        st.caption("Flags: " + ", ".join(e["red_flags"]))


def render_factor_engine(e: dict[str, Any]) -> None:
    items = [
        {"label": "COMPOSITE", "value": f"{e['composite']:.2f}",
         "value_color": signed_color(e["composite"] - 0.5)},
        {"label": "CONF", "value": f"{e['confidence']:.2f}"},
    ]
    for k, v in e.get("factor_scores", {}).items():
        items.append({
            "label": k.upper().replace("_", " "),
            "value": f"{v:.2f}" if v == v else "n/a",
            "value_color": signed_color(v - 0.5) if v == v else None,
        })
    st.markdown(dense_kpi_row(items, min_cell_px=90), unsafe_allow_html=True)


def render_tsmom_engine(e: dict[str, Any]) -> None:
    items = [
        {"label": "SIGNAL", "value": f"{e['signal']:+d}", "value_color": signed_color(e["signal"])},
        {"label": "12-1 RET", "value": f"{e['twelve_one_return'] * 100:+.1f}%",
         "value_color": signed_color(e["twelve_one_return"])},
        {"label": "REAL VOL", "value": f"{e['realized_vol'] * 100:.1f}%"
         if e["realized_vol"] == e["realized_vol"] else "n/a"},
        {"label": "TGT VOL", "value": f"{e['target_vol'] * 100:.1f}%"},
        {"label": "POSITION", "value": f"{e['position']:+.2f}",
         "value_color": signed_color(e["position"])},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=95), unsafe_allow_html=True)


def render_lbo_engine(e: dict[str, Any]) -> None:
    items = [
        {"label": "IRR", "value": f"{e['irr'] * 100:+.1f}%", "value_color": signed_color(e["irr"])},
        {"label": "MOIC", "value": f"{e['moic']:.2f}x", "value_color": signed_color(e["moic"] - 1.0)},
        {"label": "ENTRY EV", "value": f"${e['entry_ev'] / 1e9:.1f}B"},
        {"label": "EXIT EV", "value": f"${e['exit_ev'] / 1e9:.1f}B"},
        {"label": "SPONSOR EQ", "value": f"${e['sponsor_equity'] / 1e9:.1f}B"},
        {"label": "EQUITY EXIT", "value": f"${e['equity_at_exit'] / 1e9:.1f}B"},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=90), unsafe_allow_html=True)
