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
    spark = build_sparkline_svg(closes.tolist(), width=120, height=18)
    color = signed_color(chg)
    arrow = "\u25B2" if chg > 0 else ("\u25BC" if chg < 0 else "\u00B7")
    mono = TOKENS["font_mono"]
    # Stacked layout so nothing clips at 160px sidebar width.
    # Line 1: ticker symbol in the project accent.
    # Line 2: last close (no decimals if 4+ digits, 2 decimals otherwise)
    #         + arrow + signed percent change.
    # Line 3: full-width sparkline.
    # Line 4: muted caption.
    price_txt = f"{last:,.0f}" if last >= 1000 else f"{last:,.2f}"
    block = (
        f'<div style="font-family:{mono};margin:0.25rem 0 0.1rem 0;'
        f'color:{TOKENS["accent_primary"]};font-size:0.74rem;font-weight:700;'
        f'letter-spacing:0.06em;">{ticker}</div>'
        f'<div style="font-family:{mono};color:{TOKENS["text_primary"]};'
        f'font-size:0.7rem;font-weight:600;margin-bottom:0.15rem;'
        f'white-space:nowrap;">'
        f'<span>{price_txt}</span>'
        f'<span style="color:{color};font-weight:700;margin-left:0.35rem;">'
        f'{arrow}{abs(chg) * 100:.2f}%</span>'
        f'</div>'
        f'<div style="line-height:0;margin-bottom:0.15rem;">{spark}</div>'
        f'<div style="font-family:{mono};font-size:0.52rem;'
        f'color:{TOKENS["text_muted"]};letter-spacing:0.08em;text-transform:uppercase;">'
        f'5D SPARK | LAST CLOSE</div>'
    )
    st.sidebar.markdown(block, unsafe_allow_html=True)
    return {"last": last, "chg": chg}
