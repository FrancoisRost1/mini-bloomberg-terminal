"""Mini Bloomberg Terminal -- entry point.

Sets up page config, injects the theme, builds the shared data manager,
wires the four workspaces via st.navigation, and renders the global
header on every page. All orchestration only; no business logic here.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make ``terminal`` importable when Streamlit launches ``app/app.py`` directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st  # noqa: E402

from terminal.config_loader import load_config  # noqa: E402
from terminal.managers.analytics_manager import AnalyticsManager  # noqa: E402
from terminal.managers.data_manager import SharedDataManager  # noqa: E402
from terminal.utils.watchlist_io import WatchlistStore  # noqa: E402

from .header import render as render_header  # noqa: E402
from .style_inject import inject as inject_style  # noqa: E402


@st.cache_resource
def _bootstrap() -> tuple[dict, SharedDataManager, AnalyticsManager, WatchlistStore]:
    cfg = load_config()
    return cfg, SharedDataManager(cfg), AnalyticsManager(cfg), WatchlistStore(cfg)


def _init_session_state() -> None:
    defaults = {
        "active_ticker": "AAPL",
        "active_portfolio": {"tickers": [], "weights": {}},
        "market_context": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main() -> None:
    cfg = load_config()
    st.set_page_config(
        page_title=cfg["app"]["title"],
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_style()
    _init_session_state()
    config, data_manager, analytics_manager, watchlist = _bootstrap()
    st.session_state["_config"] = config
    st.session_state["_data_manager"] = data_manager
    st.session_state["_analytics_manager"] = analytics_manager
    st.session_state["_watchlist"] = watchlist

    render_header(data_manager, watchlist, config)

    pages = {
        "MARKET": [
            st.Page("pages/market_overview.py", title="Market Overview", url_path="market-overview"),
        ],
        "RESEARCH": [
            st.Page("pages/ticker_deep_dive.py", title="Ticker Deep Dive", url_path="ticker-deep-dive"),
        ],
        "ANALYTICS": [
            st.Page("pages/options_lab.py", title="Options Lab", url_path="options-lab"),
            st.Page("pages/lbo_quick_calc.py", title="LBO Quick Calc", url_path="lbo-quick-calc"),
            st.Page("pages/comps_relative_value.py", title="Comps & Relative Value", url_path="comps-relative-value"),
        ],
        "PORTFOLIO": [
            st.Page("pages/portfolio_builder.py", title="Portfolio Builder", url_path="portfolio-builder"),
        ],
    }
    navigation = st.navigation(pages)
    navigation.run()


if __name__ == "__main__":
    main()
