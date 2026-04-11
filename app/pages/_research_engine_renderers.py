"""Per engine renderers for the Research page tabs.

Each function takes a single engine result dict and renders the
detailed dense KPI grid for that engine. Pure rendering, no data
fetching. Split from _research_page_helpers.py to keep both modules
under the per module line budget.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

import os

from app.pages._research_visuals import render_memo_card
from terminal.synthesis.llm_client import generate_memo, is_available as llm_is_available
from terminal.utils.density import dense_kpi_rows, section_bar, signed_color
from terminal.utils.error_handling import inline_status_line, is_error, status_pill


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
    # Lives in a 50% column. 10 items in 3 rows forced the engine
    # grid row-2 to start way below the tallest row-1 cell and
    # created bleed between cells. 2 rows at 140px fits the column
    # without clipping labels, and keeps both engine cells on row 1
    # roughly the same height.
    st.markdown(dense_kpi_rows(items, rows=2, min_cell_px=140), unsafe_allow_html=True)
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
    # 7 cells (composite + conf + 5 factors) inside a 50% column is
    # too cramped on one line. Split into 2 balanced rows so factor
    # labels like "LOW VOL" don't touch the neighbouring cell.
    st.markdown(dense_kpi_rows(items, rows=2, min_cell_px=130), unsafe_allow_html=True)


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
    st.markdown(dense_kpi_rows(items, rows=2, min_cell_px=130), unsafe_allow_html=True)


def render_lbo_engine(e: dict[str, Any]) -> None:
    items = [
        {"label": "IRR", "value": f"{e['irr'] * 100:+.1f}%", "value_color": signed_color(e["irr"])},
        {"label": "MOIC", "value": f"{e['moic']:.2f}x", "value_color": signed_color(e["moic"] - 1.0)},
        {"label": "ENTRY EV", "value": f"${e['entry_ev'] / 1e9:.1f}B"},
        {"label": "EXIT EV", "value": f"${e['exit_ev'] / 1e9:.1f}B"},
        {"label": "SPONSOR EQ", "value": f"${e['sponsor_equity'] / 1e9:.1f}B"},
        {"label": "EQUITY EXIT", "value": f"${e['equity_at_exit'] / 1e9:.1f}B"},
    ]
    # 6 cells split into 2 rows of 3 inside the 50% engine column.
    st.markdown(dense_kpi_rows(items, rows=2, min_cell_px=130), unsafe_allow_html=True)


def render_llm_memo(packet: dict[str, Any], config: dict[str, Any]) -> None:
    """Phase 4. Optional LLM memo synthesis. Never blocks the page.

    Renders a one line TLDR backed by the deterministic rating, a
    generation timestamp, and the full memo body inside a collapsible
    expander. The deterministic rating is locked at the prompt layer,
    so the TLDR is always derived from the recommendation dict, not
    from the LLM output.
    """
    st.markdown(section_bar("LLM MEMO", source="anthropic"), unsafe_allow_html=True)
    llm_cfg = config["llm"]
    enabled = llm_cfg.get("enabled", False)
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not ((enabled == "auto" and has_key) or enabled is True) or not llm_is_available():
        st.markdown(inline_status_line("OFF", source="anthropic"), unsafe_allow_html=True)
        return
    fundamentals = packet.get("fundamentals")
    if packet.get("status") != "success" or not fundamentals or is_error(fundamentals):
        st.markdown(inline_status_line("PARTIAL", source="anthropic"), unsafe_allow_html=True)
        return
    with st.spinner("Synthesizing memo via Claude."):
        result = generate_memo(
            ticker=packet["ticker"], recommendation=packet["recommendation"],
            ratios=fundamentals.key_ratios, scenarios=packet.get("scenarios", []), llm_cfg=llm_cfg,
        )
    if result["status"] != "success":
        st.markdown(inline_status_line("PARTIAL", source="anthropic"), unsafe_allow_html=True)
        return
    if result.get("inconsistency"):
        st.markdown(status_pill("LLM RATING INCONSISTENCY", "failed"), unsafe_allow_html=True)
    rec = packet.get("recommendation") or {}
    render_memo_card(result, rec.get("rating", "INSUFFICIENT_DATA"), rec.get("composite_score", float("nan")))
