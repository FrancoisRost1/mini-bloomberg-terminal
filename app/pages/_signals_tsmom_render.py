"""TSMOM signal table renderer for the Signals page.

Renders the 13-ETF signal table grouped by asset class, with signal
change detection highlighted.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from style_inject import TOKENS, styled_section_label  # noqa: E402

_ACCENT = TOKENS.get("accent_primary", "#FF8C00")
_SIGNAL_COLORS = {"LONG": "#00C853", "SHORT": "#FF1744", "FLAT": _ACCENT, "NO DATA": "#555555"}


def _render_changes(df: pd.DataFrame) -> None:
    changes = df[df["changed"]]
    if len(changes) > 0:
        flips = [f"{r['ticker']} {r['prior_signal']} -> {r['signal']}" for _, r in changes.iterrows()]
        flip_text = " | ".join(flips)
        st.markdown(
            f'<div style="color:{_ACCENT};font-size:12px;margin-bottom:8px;font-family:monospace;">SIGNAL CHANGES: {flip_text}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="color:#666;font-size:12px;margin-bottom:8px;font-family:monospace;">No signal changes since prior close</div>',
            unsafe_allow_html=True,
        )


def _table_header() -> str:
    hdr = '<table style="width:100%;border-collapse:collapse;font-family:monospace;font-size:13px;">'
    hdr += '<tr style="border-bottom:1px solid #333;color:#888;">'
    for col, align in [("TICKER", "left"), ("NAME", "left"), ("SIGNAL", "center"),
                       ("12-1 RET", "right"), ("ANN VOL", "right"), ("CHG", "center")]:
        hdr += f'<th style="text-align:{align};padding:4px 8px;">{col}</th>'
    hdr += '</tr>'
    return hdr


def _table_row(r: pd.Series) -> str:
    sig_color = _SIGNAL_COLORS.get(r["signal"], "#555")
    ret_val = r.get("return_12_1")
    ret_str = f"{ret_val:.1%}" if ret_val is not None else "n/a"
    ret_color = "#00C853" if (ret_val or 0) > 0 else "#FF1744" if (ret_val or 0) < 0 else "#888"
    vol_val = r.get("ann_vol")
    vol_str = f"{vol_val:.1%}" if vol_val is not None else "n/a"
    chg_str = f'<span style="color:{_ACCENT};">FLIP</span>' if r["changed"] else ""

    row = '<tr style="border-bottom:1px solid #1a1a1a;">'
    row += f'<td style="padding:4px 8px;color:#ccc;">{r["ticker"]}</td>'
    row += f'<td style="padding:4px 8px;color:#999;">{r["name"]}</td>'
    row += f'<td style="text-align:center;padding:4px 8px;color:{sig_color};font-weight:bold;">{r["signal"]}</td>'
    row += f'<td style="text-align:right;padding:4px 8px;color:{ret_color};">{ret_str}</td>'
    row += f'<td style="text-align:right;padding:4px 8px;color:#999;">{vol_str}</td>'
    row += f'<td style="text-align:center;padding:4px 8px;">{chg_str}</td></tr>'
    return row


def render_tsmom_table(df: pd.DataFrame) -> None:
    styled_section_label("TSMOM SIGNALS | 13-ETF UNIVERSE")
    _render_changes(df)

    html = _table_header()
    current_class = None
    for _, r in df.iterrows():
        if r["asset_class"] != current_class:
            current_class = r["asset_class"]
            html += (
                f'<tr><td colspan="6" style="padding:6px 8px 2px;color:#888;font-size:11px;'
                f'text-transform:uppercase;border-top:1px solid #222;">{current_class}</td></tr>'
            )
        html += _table_row(r)

    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    longs = len(df[df["signal"] == "LONG"])
    shorts = len(df[df["signal"] == "SHORT"])
    flats = len(df[df["signal"] == "FLAT"])
    valid = len(df[df["signal"] != "NO DATA"])

    if valid > 0:
        long_pct = longs / valid
        if long_pct > 0.65:
            tone = "Broad momentum is positive across asset classes."
        elif long_pct < 0.35:
            tone = "Momentum is predominantly negative. Defensive positioning is indicated."
        else:
            tone = "Mixed momentum signals. No strong directional conviction across assets."
    else:
        tone = "Insufficient data to assess cross-asset momentum."

    callout = f"{longs}L / {shorts}S / {flats}F across {valid} assets. {tone}"
    st.markdown(
        f'<div style="color:#888;font-size:12px;margin-top:8px;padding:8px;border-left:2px solid {_ACCENT};font-family:monospace;">{callout}</div>',
        unsafe_allow_html=True,
    )
