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
    """Footer band: page name on the left, freshness UTC stamp on the right."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    snapshot = data_manager.snapshot_age().strftime("%Y-%m-%d %H:%M:%S UTC")
    mode = data_manager.registry.mode_label()
    version = config.get("app", {}).get("version", "1.0.0")
    src = "FMP STABLE | YFINANCE | FRED | ANTHROPIC"
    st.markdown(
        f'<div class="freshness-footer">'
        f'<span>MINI BLOOMBERG TERMINAL v{version} | MODE {mode} | {src}</span>'
        f'<span>SNAPSHOT {snapshot} | RENDERED {now}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
