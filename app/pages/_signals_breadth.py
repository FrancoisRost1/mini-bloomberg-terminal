"""Breadth signals for the Signals page.

Percentage of sector ETFs trading above their 200-day SMA, per-ETF
status, and an aggregate reading.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import TOKENS, styled_section_label  # noqa: E402
from terminal.data.schemas import PriceData  # noqa: E402


_ACCENT = TOKENS.get("accent_primary", "#FF8C00")


@st.cache_data(ttl=900, show_spinner=False)
def compute_breadth_signals(_config: dict, _data_manager) -> dict:
    """Compute breadth metrics for the sector ETF universe."""
    breadth_cfg = _config.get("market", {}).get("breadth", {})
    universe = breadth_cfg.get("universe", [])
    ma_period = _config.get("signals", {}).get("breadth", {}).get("ma_period", 200)

    results = []
    for ticker in universe:
        prices = None
        try:
            price_data = _data_manager.get_index_prices(ticker, period="2y")
            if isinstance(price_data, PriceData) and not price_data.is_empty():
                prices = price_data.prices
        except Exception:
            prices = None

        if prices is None or len(prices) < ma_period + 5:
            results.append({"ticker": ticker, "above_ma": None, "last": None, "ma_200": None, "pct_from_ma": None})
            continue

        close = prices["close"] if "close" in prices.columns else prices.iloc[:, 0]
        close = close.dropna()
        if len(close) < ma_period + 5:
            results.append({"ticker": ticker, "above_ma": None, "last": None, "ma_200": None, "pct_from_ma": None})
            continue

        last_price = float(close.iloc[-1])
        ma_val = float(close.rolling(ma_period).mean().iloc[-1])
        above = last_price > ma_val
        pct_from = (last_price / ma_val - 1.0) if ma_val > 0 else 0.0

        results.append({"ticker": ticker, "above_ma": above, "last": last_price, "ma_200": ma_val, "pct_from_ma": pct_from})

    valid = [r for r in results if r["above_ma"] is not None]
    above_count = sum(1 for r in valid if r["above_ma"])
    total = len(valid)
    pct_above = above_count / total if total > 0 else 0.0

    return {"etfs": results, "above_count": above_count, "total": total, "pct_above": pct_above}


def _aggregate_kpi_html(reading: str, detail: str, color: str) -> str:
    return (
        f'<div style="background:#0E1117;border:1px solid #222;border-radius:3px;padding:0.65rem 0.9rem;">'
        f'<div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;margin-bottom:0.3rem;">{reading}</div>'
        f'<div style="font-family:monospace;font-size:1.1rem;font-weight:600;color:{color};">{detail}</div>'
        f'</div>'
    )


def render_breadth_signals(breadth: dict) -> None:
    styled_section_label("MARKET BREADTH | 200d MA")

    pct = breadth["pct_above"]
    above = breadth["above_count"]
    total = breadth["total"]

    if pct > 0.7:
        agg_color = "#00C853"
        reading = "BROAD STRENGTH"
    elif pct > 0.4:
        agg_color = _ACCENT
        reading = "MIXED"
    else:
        agg_color = "#FF1744"
        reading = "WEAK BREADTH"

    st.markdown(
        _aggregate_kpi_html(reading, f"{above}/{total} above 200d MA ({pct:.0%})", agg_color),
        unsafe_allow_html=True,
    )

    html = '<table style="width:100%;border-collapse:collapse;font-family:monospace;font-size:13px;margin-top:8px;">'
    html += '<tr style="border-bottom:1px solid #333;color:#888;">'
    html += '<th style="text-align:left;padding:3px 6px;">ETF</th>'
    html += '<th style="text-align:right;padding:3px 6px;">LAST</th>'
    html += '<th style="text-align:right;padding:3px 6px;">200d MA</th>'
    html += '<th style="text-align:right;padding:3px 6px;">vs MA</th>'
    html += '<th style="text-align:center;padding:3px 6px;">STATUS</th></tr>'

    for r in breadth["etfs"]:
        if r["above_ma"] is None:
            status = '<span style="color:#555;">n/a</span>'
            last_str = "n/a"
            ma_str = "n/a"
            pct_str = "n/a"
            pct_color = "#555"
        else:
            above_flag = r["above_ma"]
            status_color = "#00C853" if above_flag else "#FF1744"
            status_text = "ABOVE" if above_flag else "BELOW"
            status = f'<span style="color:{status_color};">{status_text}</span>'
            last_str = f"${r['last']:.2f}"
            ma_str = f"${r['ma_200']:.2f}"
            pct_val = r["pct_from_ma"]
            pct_str = f"{pct_val:+.1%}"
            pct_color = "#00C853" if pct_val > 0 else "#FF1744"

        html += '<tr style="border-bottom:1px solid #1a1a1a;">'
        html += f'<td style="padding:3px 6px;color:#ccc;">{r["ticker"]}</td>'
        html += f'<td style="text-align:right;padding:3px 6px;color:#999;">{last_str}</td>'
        html += f'<td style="text-align:right;padding:3px 6px;color:#666;">{ma_str}</td>'
        html += f'<td style="text-align:right;padding:3px 6px;color:{pct_color};">{pct_str}</td>'
        html += f'<td style="text-align:center;padding:3px 6px;">{status}</td></tr>'

    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    if pct > 0.7:
        interp = "Most sectors trading above their long-term trend. Broad participation supports continued upside."
    elif pct > 0.4:
        interp = "Selective participation. Some sectors leading while others lag. Watch for narrowing breadth."
    else:
        interp = "Majority of sectors below their 200d moving average. Deteriorating breadth is a caution signal."

    st.markdown(
        f'<div style="color:#888;font-size:12px;margin-top:8px;padding:8px;border-left:2px solid {_ACCENT};font-family:monospace;">{interp}</div>',
        unsafe_allow_html=True,
    )
