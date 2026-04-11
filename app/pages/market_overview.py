"""MARKET. Market Overview workspace.

Dense grid layout: most of the dashboard fits above the fold on a
1400px+ viewport.

  Row 1 : Global indices (60%)        | Regime classifier (40%)
  Row 2 : Rates table (50%)           | Yield curve (50%)
  Row 3 : FX (33%) | Commodities (33%)| Macro snapshot (33%)
  Row 4 : Sector heatmap              (full width)
  Row 5 : Breadth table (60%)         | Gainers/losers (40%)
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import styled_header  # noqa: E402

from app.pages._market_extras import (  # noqa: E402
    render_commodities_row,
    render_fx_row,
    render_gainers_losers,
    render_yield_curve,
)
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

    # Row 1: indices | regime
    row1_l, row1_r = st.columns([6, 4])
    with row1_l:
        render_indices_strip(data_manager, config)
    with row1_r:
        render_regime(data_manager, config)

    # Row 2: rates | yield curve
    row2_l, row2_r = st.columns([1, 1])
    with row2_l:
        render_rates_and_vol(data_manager, config)
    with row2_r:
        render_yield_curve(data_manager)

    # Row 3: FX | commodities | macro
    row3_l, row3_c, row3_r = st.columns([1, 1, 1])
    with row3_l:
        render_fx_row(data_manager)
    with row3_c:
        render_commodities_row(data_manager)
    with row3_r:
        _render_macro_snapshot(data_manager, config)

    # Row 4: sector heatmap (full width)
    render_sector_heatmap(data_manager, config)

    # Row 5: breadth | gainers-losers
    row5_l, row5_r = st.columns([6, 4])
    with row5_l:
        render_breadth(data_manager, config)
    with row5_r:
        render_gainers_losers(data_manager, config)


def _render_macro_snapshot(data_manager, config) -> None:
    st.markdown(section_bar("MACRO SNAPSHOT", source="FRED + yfinance"), unsafe_allow_html=True)
    vix_id = config["market"]["macro_series"]["volatility"]["vix_series"]
    hy_id = config["market"]["macro_series"]["volatility"]["hy_spread_series"]
    macro = data_manager.get_macro([vix_id, hy_id, "FEDFUNDS"])
    items: list[dict] = []
    if not is_error(macro):
        for key, label in [(vix_id, "VIX"), (hy_id, "HY OAS"), ("FEDFUNDS", "FED FUNDS")]:
            v = macro.latest(key)
            stale = macro.is_stale(key) if hasattr(macro, "is_stale") else False
            if v == v:
                value = f"{v:.2f}"
                item = {"label": label, "value": value}
                if stale:
                    item["delta"] = "STALE"
                items.append(item)
            else:
                items.append({"label": label, "value": "n/a"})
    for ticker, label in [("UUP", "DXY")]:
        data = data_manager.get_index_prices(ticker, period="1mo")
        if is_error(data) or data.is_empty():
            items.append({"label": label, "value": "n/a"})
            continue
        last = data.last_close()
        prev = float(data.prices["close"].iloc[0])
        chg = (last / prev - 1) if prev else 0.0
        items.append({"label": label, "value": f"{last:,.2f}",
                      "delta": f"{chg * 100:+.2f}%", "delta_color": signed_color(chg)})
    st.markdown(dense_kpi_row(items, min_cell_px=135), unsafe_allow_html=True)


render()
