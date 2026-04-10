"""MARKET. Market Overview workspace. Indices, rates, regime, breadth."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import styled_divider, styled_header, styled_section_label  # noqa: E402

from app.pages._market_overview_helpers import (  # noqa: E402
    render_breadth,
    render_indices_strip,
    render_rates_and_vol,
    render_regime,
)


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    styled_header("Market Overview", "Cross asset regime context")

    render_indices_strip(data_manager, config)
    styled_divider()
    styled_section_label("RATES AND VOLATILITY")
    render_rates_and_vol(data_manager, config)
    styled_divider()
    styled_section_label("REGIME CLASSIFIER")
    render_regime(data_manager, config)
    styled_divider()
    styled_section_label("MARKET BREADTH")
    render_breadth(data_manager, config)


render()
