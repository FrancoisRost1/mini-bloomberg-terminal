"""Research page engine results grid.

Renders the 2x2 grid of engine cards (PE, Factor, TSMOM, LBO). Split
out of ``_research_engine_renderers`` so both modules stay under the
per module line budget. Every cell is clipped to the 50% grid column
with ``overflow:hidden`` so failure reasons or long labels can never
bleed into a neighbouring cell.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.pages._research_engine_renderers import (
    render_factor_engine,
    render_lbo_engine,
    render_pe_engine,
    render_tsmom_engine,
)
from terminal.utils.density import section_bar


_STATUS_COLORS = {
    "success": "#3D9A50",
    "failed":  "#C43D3D",
    "missing": "#8E8E9A",
}


def _engine_fail_block(label: str, status: str, reason: str | None) -> str:
    """Self-contained HTML block for a failed or missing engine cell.

    Wraps the status pill and the short failure reason in one
    overflow-clipped container so long text is ellipsised rather than
    bleeding into the neighbouring grid cell.
    """
    color = _STATUS_COLORS.get(status, "#E8B500")
    body = (reason or "engine unavailable").strip()
    if len(body) > 52:
        body = body[:49] + "..."
    body = body.replace("<", "&lt;").replace(">", "&gt;")
    return (
        '<div style="overflow:hidden;max-width:100%;min-width:0;'
        'padding:0.35rem 0.4rem 0.35rem 0.4rem;margin:0.3rem 0 0.4rem 0;'
        'border-left:2px solid rgba(255,255,255,0.06);">'
        '<div style="font-family:\'JetBrains Mono\',monospace;'
        f'font-size:0.64rem;font-weight:800;color:{color};'
        'letter-spacing:0.08em;line-height:1.5;'
        'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
        f'{label} {status.upper()}'
        '</div>'
        '<div style="font-family:\'JetBrains Mono\',monospace;'
        'font-size:0.6rem;color:#8E8E9A;letter-spacing:0.04em;'
        'line-height:1.4;margin-top:0.25rem;'
        'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
        f'{body}'
        '</div></div>'
    )


def _engine_cell_header(label: str, status: str) -> str:
    """Mono status pill wrapped in a single overflow-clipped line.

    Uses explicit line-height 1.6 and generous vertical padding so
    the cap-height has room inside the container even when the
    parent element container clips.
    """
    color = _STATUS_COLORS.get(status, "#E8B500")
    return (
        '<div style="overflow:hidden;max-width:100%;min-width:0;'
        'white-space:nowrap;text-overflow:ellipsis;'
        'padding:0.45rem 0 0.25rem 0;margin-top:0.3rem;'
        'border-bottom:1px solid rgba(255,255,255,0.06);'
        'margin-bottom:0.35rem;">'
        '<span style="font-family:\'JetBrains Mono\',monospace;'
        f'font-size:0.66rem;font-weight:800;color:{color};'
        'letter-spacing:0.1em;line-height:1.6;'
        'display:inline-block;padding:0.05rem 0;">'
        f'{label} {status.upper()}'
        '</span></div>'
    )


_ENGINE_DIVIDER = (
    '<div style="height:0.7rem;margin:0.3rem 0;'
    'border-top:1px solid rgba(255,255,255,0.08);"></div>'
)


def render_engine_grid(packet: dict[str, Any]) -> None:
    """Render the four engine cards as two full-width rows.

    A true 2x2 grid packs four cell headers in tight 50% columns
    which collides with the 3-row PE scoring KPI split on tall
    layouts. Instead we render Row 1 = PE + Factor and Row 2 =
    TSMOM + LBO as two independent st.columns blocks separated by
    an explicit horizontal divider, so the second row always starts
    cleanly below the tallest cell of the first row.
    """
    st.markdown(section_bar("ENGINE RESULTS", source="FMP"), unsafe_allow_html=True)
    engines = packet.get("engines") or {}
    rows: list[list[tuple[str, str, Any]]] = [
        [
            ("pe_scoring",      "PE SCORING",      render_pe_engine),
            ("factor_exposure", "FACTOR EXPOSURE", render_factor_engine),
        ],
        [
            ("tsmom",           "TSMOM SIGNAL",    render_tsmom_engine),
            ("lbo",             "LBO SNAPSHOT",    render_lbo_engine),
        ],
    ]
    for idx, row in enumerate(rows):
        if idx > 0:
            st.markdown(_ENGINE_DIVIDER, unsafe_allow_html=True)
        slot_l, slot_r = st.columns([1, 1])
        for slot, (key, label, renderer) in zip([slot_l, slot_r], row):
            with slot:
                engine = engines.get(key, {})
                status = engine.get("status", "missing")
                if engine.get("status") != "success":
                    st.markdown(_engine_fail_block(label, status, engine.get("reason")),
                                unsafe_allow_html=True)
                    continue
                st.markdown(_engine_cell_header(label, status), unsafe_allow_html=True)
                renderer(engine)
