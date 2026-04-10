"""Loading skeleton primitives.

Grey placeholder blocks rendered while a section is fetching. Use as
context managers around the actual render call: the placeholder
appears first, the spinner runs, and st.empty().empty() clears it
when the real content arrives.

Usage:
    ph = chart_skeleton(height=320)
    real_chart = expensive_call()
    ph.empty()
    st.plotly_chart(real_chart)
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import streamlit as st


_BASE_BG = "rgba(255,255,255,0.04)"
_HIGHLIGHT = "rgba(255,255,255,0.08)"


def _block(height_px: int) -> str:
    return (
        f'<div style="height:{height_px}px;width:100%;'
        f'background:linear-gradient(90deg, {_BASE_BG} 0%, {_HIGHLIGHT} 50%, {_BASE_BG} 100%);'
        f'background-size:200% 100%;'
        f'border:1px solid rgba(255,255,255,0.04);border-radius:3px;'
        f'animation: skel-pulse 1.4s ease-in-out infinite;margin:0.15rem 0;"></div>'
    )


def _bars(rows: int) -> str:
    cells = "".join(
        f'<div style="height:1.05rem;background:{_BASE_BG};border-radius:2px;margin:0.18rem 0;'
        f'background:linear-gradient(90deg, {_BASE_BG} 0%, {_HIGHLIGHT} 50%, {_BASE_BG} 100%);'
        f'background-size:200% 100%;animation: skel-pulse 1.4s ease-in-out infinite;width:{w}%;"></div>'
        for w in (96, 88, 92, 84, 90, 86, 78, 82)[:rows]
    )
    return f'<div style="display:flex;flex-direction:column;gap:0.05rem;">{cells}</div>'


def chart_skeleton(height: int = 320):
    """Return a placeholder slot for an upcoming chart."""
    slot = st.empty()
    slot.markdown(_block(height), unsafe_allow_html=True)
    return slot


def kpi_skeleton(rows: int = 1, cells: int = 6):
    """Return a placeholder slot for an upcoming KPI grid."""
    slot = st.empty()
    grid = (
        f'<div style="display:grid;grid-template-columns:repeat({cells},1fr);gap:0.2rem;">'
        + "".join(_block(46) for _ in range(rows * cells))
        + "</div>"
    )
    slot.markdown(grid, unsafe_allow_html=True)
    return slot


def table_skeleton(rows: int = 6):
    slot = st.empty()
    slot.markdown(_bars(rows), unsafe_allow_html=True)
    return slot


@contextmanager
def loading_chart(height: int = 320) -> Iterator:
    """Context manager. Shows a chart skeleton, yields the slot, and
    clears it on exit so the real chart can be rendered after.
    """
    slot = chart_skeleton(height)
    try:
        yield slot
    finally:
        slot.empty()
