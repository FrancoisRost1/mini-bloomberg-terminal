"""Page level freshness footer.

Renders a small monospace timestamp band at the bottom of every page.
The CSS class ``.freshness-footer`` is defined in density_css.py so
all formatting (border, font, colors) lives in one place.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

from terminal.managers.data_manager import SharedDataManager


def render_footer(data_manager: SharedDataManager, config: dict[str, Any]) -> None:
    """Footer band: page name on the left, freshness UTC stamp on the right.

    The mode segment ('MODE PRODUCTION') was dropped from the left
    line on 2026-04-17 - see header_status.py docstring. The multi
    source provider list stays visible because it is a credibility
    signal (multi vendor data) rather than dev jargon.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    snapshot = data_manager.snapshot_age().strftime("%Y-%m-%d %H:%M:%S UTC")
    version = config.get("app", {}).get("version", "1.3.0")
    src = "FMP STABLE | YFINANCE | FRED | FINNHUB | ANTHROPIC"
    st.markdown(
        f'<div class="freshness-footer">'
        f'<span>FROSTAING TERMINAL v{version} | {src}</span>'
        f'<span>SNAPSHOT {snapshot} | RENDERED {now}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
