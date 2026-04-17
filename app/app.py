"""Mini Bloomberg Terminal entry point.

Sets up page config, injects the canonical design system, builds the
shared data manager, wires the four workspaces via st.navigation, and
renders the global header on every page. Orchestration only; no
business logic.

Import strategy: ``streamlit run app/app.py`` loads this file as a
top-level script (``__name__ == "__main__"``), NOT as the
``app.app`` package member. Relative imports therefore raise
``ImportError: attempted relative import with no known parent package``.
We bootstrap the project root onto sys.path before any project import
and use absolute ``app.*`` and ``terminal.*`` imports throughout. The
canonical ``style_inject`` lives at the project root and is imported
flat, matching every other Streamlit project in the Finance Lab.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import inject_styles  # noqa: E402

from app.density_css import inject_density  # noqa: E402
from app.footer import render_footer  # noqa: E402
from app.header import render as render_header  # noqa: E402
from app.sidebar_ticker import render as render_sidebar_ticker  # noqa: E402
from terminal.config_loader import load_config  # noqa: E402
from terminal.managers.analytics_manager import AnalyticsManager  # noqa: E402
from terminal.managers.data_manager import SharedDataManager  # noqa: E402
from terminal.utils.density import set_show_data_sources  # noqa: E402
from terminal.utils.watchlist_io import WatchlistStore  # noqa: E402


@st.cache_resource
def _bootstrap() -> tuple[dict, SharedDataManager, AnalyticsManager, WatchlistStore]:
    cfg = load_config()
    return cfg, SharedDataManager(cfg), AnalyticsManager(cfg), WatchlistStore(cfg)


def _init_session_state() -> None:
    defaults = {
        "active_ticker": "AAPL",
        "active_portfolio": {"tickers": [], "weights": {}},
        "market_context": {},
        "sidebar_visible": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _inject_sidebar_visibility() -> None:
    """Apply a CSS override that collapses the sidebar to zero width
    when ``sidebar_visible`` is False. Flipped by the header toggle.
    """
    if st.session_state.get("sidebar_visible", True):
        return
    st.markdown(
        '<style>'
        'section[data-testid="stSidebar"] {'
        ' width: 0 !important; min-width: 0 !important; max-width: 0 !important;'
        ' border-right: none !important;'
        ' transform: translateX(-100%) !important;'
        ' visibility: hidden !important;'
        '}'
        '</style>',
        unsafe_allow_html=True,
    )


def main() -> None:
    cfg = load_config()
    st.set_page_config(
        page_title=cfg["app"]["title"],
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()
    inject_density()
    _init_session_state()
    _inject_sidebar_visibility()
    # Toggle per chart "SRC X" watermarks based on config.yaml app.debug.
    # When false (default) the chart headers stay clean for visitors;
    # when true the internal provider tags render for debugging.
    set_show_data_sources(bool(cfg.get("app", {}).get("debug", False)))
    config, data_manager, analytics_manager, watchlist = _bootstrap()
    st.session_state["_config"] = config
    st.session_state["_data_manager"] = data_manager
    st.session_state["_analytics_manager"] = analytics_manager
    st.session_state["_watchlist"] = watchlist

    ticker_state = render_sidebar_ticker(data_manager)
    render_header(data_manager, watchlist, config, ticker_state)

    # Short nav titles fit the 180px sidebar without truncation.
    # url_path stays stable so bookmarks keep working.
    analytics: list = [
        st.Page("pages/lbo_quick_calc.py", title="LBO", url_path="lbo-quick-calc"),
        st.Page("pages/comps_relative_value.py", title="Comps", url_path="comps-relative-value"),
    ]
    # Options chain comes from yfinance regardless of which equity provider
    # is wired (FMP Starter does not include options). The page renders if
    # the options provider reports it can serve the endpoint.
    if data_manager.registry.options_provider().supports_options_chain():
        analytics.insert(0, st.Page("pages/options_lab.py", title="Options", url_path="options-lab"))

    pages = {
        "MARKET": [
            st.Page("pages/market_overview.py", title="Market", url_path="market-overview"),
            st.Page("pages/live_signals.py", title="Signals", url_path="live-signals"),
        ],
        "RESEARCH": [st.Page("pages/ticker_deep_dive.py", title="Research", url_path="ticker-deep-dive")],
        "ANALYTICS": analytics,
        "PORTFOLIO": [st.Page("pages/portfolio_builder.py", title="Portfolio", url_path="portfolio-builder")],
    }
    navigation = st.navigation(pages)
    navigation.run()
    render_footer(data_manager, config)


if __name__ == "__main__":
    main()
