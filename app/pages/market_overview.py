"""MARKET. Market Overview workspace. 2x2 multi pane layout."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import styled_header  # noqa: E402

from app.pages._market_extras import render_fx_row, render_gainers_losers, render_yield_curve  # noqa: E402
from app.pages._market_overview_helpers import (  # noqa: E402
    render_breadth,
    render_indices_strip,
    render_rates_and_vol,
    render_regime,
    render_sector_heatmap,
)
from terminal.utils.density import dense_kpi_row, section_bar, signed_color  # noqa: E402
from terminal.utils.error_handling import is_error  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    styled_header("Market Overview", "Cross asset regime context")

    render_indices_strip(data_manager, config)
    render_fx_row(data_manager)
    render_gainers_losers(data_manager, config)

    render_sector_heatmap(data_manager, config)

    row1_l, row1_r = st.columns([1, 1])
    with row1_l:
        render_rates_and_vol(data_manager, config)
        render_yield_curve(data_manager)
    with row1_r:
        render_regime(data_manager, config)

    row2_l, row2_r = st.columns([1, 1])
    with row2_l:
        render_breadth(data_manager, config)
    with row2_r:
        _render_macro_snapshot(data_manager, config)


def _render_macro_snapshot(data_manager, config) -> None:
    st.markdown(section_bar("MACRO SNAPSHOT", source="FRED + yfinance"), unsafe_allow_html=True)
    vix_id = config["market"]["macro_series"]["volatility"]["vix_series"]
    hy_id = config["market"]["macro_series"]["volatility"]["hy_spread_series"]
    macro = data_manager.get_macro([vix_id, hy_id, "FEDFUNDS"])
    items: list[dict] = []
    if not is_error(macro):
        for key, label in [(vix_id, "VIX"), (hy_id, "HY OAS"), ("FEDFUNDS", "FED FUNDS")]:
            v = macro.latest(key)
            items.append({"label": label, "value": f"{v:.2f}" if v == v else "n/a"})
    for ticker, label in [("GLD", "GOLD"), ("USO", "OIL"), ("UUP", "DXY")]:
        data = data_manager.get_index_prices(ticker, period="1mo")
        if is_error(data) or data.is_empty():
            items.append({"label": label, "value": "n/a"})
            continue
        last = data.last_close()
        prev = float(data.prices["close"].iloc[0])
        chg = (last / prev - 1) if prev else 0.0
        items.append({"label": label, "value": f"{last:,.2f}",
                      "delta": f"{chg * 100:+.2f}%", "delta_color": signed_color(chg)})
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)


render()
