"""Sidebar active ticker block.

Renders, in the sidebar, the active ticker name with a 5 day inline
SVG sparkline and a signed % change. Updates whenever the active
ticker changes (via st.session_state). Pure data fetch + render; the
data manager handles caching so this is cheap to call on every page.
"""

from __future__ import annotations

import streamlit as st

from style_inject import TOKENS

from terminal.managers.data_manager import SharedDataManager
from terminal.utils.density import signed_color
from terminal.utils.error_handling import is_error
from terminal.utils.sparkline import build_sparkline_svg


def render(data_manager: SharedDataManager) -> dict[str, float | None]:
    """Render the sidebar block AND return a small dict the header can
    reuse for its 1D change badge: ``{"last": float, "chg": float}``.
    """
    ticker = (st.session_state.get("active_ticker") or "AAPL").upper()
    data = data_manager.get_any_prices(ticker, period="1mo")
    if is_error(data) or data.is_empty():
        st.sidebar.markdown(
            f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.72rem;'
            f'color:{TOKENS["text_secondary"]};margin:0.2rem 0;">'
            f'<b style="color:{TOKENS["accent_primary"]}">{ticker}</b>'
            f'<span style="color:{TOKENS["text_muted"]};margin-left:0.4rem;">no data</span></div>',
            unsafe_allow_html=True,
        )
        return {"last": None, "chg": None}

    closes = data.prices["close"].tail(6)
    if len(closes) < 2:
        return {"last": None, "chg": None}
    last = float(closes.iloc[-1])
    prev = float(closes.iloc[-2])
    chg = (last - prev) / prev if prev else 0.0
    spark = build_sparkline_svg(closes.tolist(), width=64, height=16)
    color = signed_color(chg)
    arrow = "\u25B2" if chg > 0 else ("\u25BC" if chg < 0 else "\u00B7")
    block = (
        f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.72rem;'
        f'color:{TOKENS["text_primary"]};display:flex;align-items:center;gap:0.35rem;'
        f'margin:0.2rem 0;">'
        f'<b style="color:{TOKENS["accent_primary"]};letter-spacing:0.04em;">{ticker}</b>'
        f'<span>{last:,.2f}</span>'
        f'<span style="color:{color};font-weight:700;">{arrow}{abs(chg) * 100:.2f}%</span>'
        f'{spark}'
        f'</div>'
        f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.55rem;'
        f'color:{TOKENS["text_muted"]};letter-spacing:0.08em;text-transform:uppercase;">'
        f'5D SPARK | LAST CLOSE</div>'
    )
    st.sidebar.markdown(block, unsafe_allow_html=True)
    return {"last": last, "chg": chg}
