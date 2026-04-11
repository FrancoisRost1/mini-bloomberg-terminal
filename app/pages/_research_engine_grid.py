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
        'padding:0.15rem 0.3rem 0.25rem 0.3rem;margin-bottom:0.2rem;'
        'border-left:2px solid rgba(255,255,255,0.06);">'
        '<div style="font-family:\'JetBrains Mono\',monospace;'
        f'font-size:0.62rem;font-weight:700;color:{color};'
        'letter-spacing:0.08em;line-height:1.1;'
        'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
        f'{label} {status.upper()}'
        '</div>'
        '<div style="font-family:\'JetBrains Mono\',monospace;'
        'font-size:0.6rem;color:#8E8E9A;letter-spacing:0.04em;'
        'line-height:1.2;margin-top:0.18rem;'
        'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
        f'{body}'
        '</div></div>'
    )


def _engine_cell_header(label: str, status: str) -> str:
    """Mono status pill wrapped in a single overflow-clipped line."""
    color = _STATUS_COLORS.get(status, "#E8B500")
    return (
        '<div style="overflow:hidden;max-width:100%;min-width:0;'
        'white-space:nowrap;text-overflow:ellipsis;'
        'padding:0.05rem 0 0.1rem 0;">'
        '<span style="font-family:\'JetBrains Mono\',monospace;'
        f'font-size:0.62rem;font-weight:700;color:{color};'
        'letter-spacing:0.08em;">'
        f'{label} {status.upper()}'
        '</span></div>'
    )


def render_engine_grid(packet: dict[str, Any]) -> None:
    """Render the four engine cards in a 2x2 grid with clipped cells."""
    st.markdown(section_bar("ENGINE RESULTS", source="FMP"), unsafe_allow_html=True)
    engines = packet.get("engines") or {}
    layout: list[tuple[str, str, Any]] = [
        ("pe_scoring",      "PE SCORING",     render_pe_engine),
        ("factor_exposure", "FACTOR EXPOSURE", render_factor_engine),
        ("tsmom",           "TSMOM SIGNAL",    render_tsmom_engine),
        ("lbo",             "LBO SNAPSHOT",    render_lbo_engine),
    ]
    row1_l, row1_r = st.columns([1, 1])
    row2_l, row2_r = st.columns([1, 1])
    slots = [row1_l, row1_r, row2_l, row2_r]
    for slot, (key, label, renderer) in zip(slots, layout):
        with slot:
            engine = engines.get(key, {})
            status = engine.get("status", "missing")
            if engine.get("status") != "success":
                st.markdown(_engine_fail_block(label, status, engine.get("reason")),
                            unsafe_allow_html=True)
                continue
            st.markdown(_engine_cell_header(label, status), unsafe_allow_html=True)
            renderer(engine)
