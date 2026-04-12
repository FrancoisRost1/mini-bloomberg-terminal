"""RESEARCH. Ticker Deep Dive workspace.

Always renders the full 2x2 skeleton. Each phase fills with whatever
data is available and shows an inline status pill where data is
missing. The page never collapses to a void.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import TOKENS, styled_header  # noqa: E402

from app.pages._research_earnings import render_earnings  # noqa: E402
from app.pages._research_news import render_news  # noqa: E402
from app.pages._research_ownership import render_ownership  # noqa: E402
from app.pages._research_page_helpers import (  # noqa: E402
    render_phase1_chart,
    render_phase1_stats,
    render_phase2_engines,
    render_phase3_recommendation,
    render_phase4_llm,
)
from terminal.adapters.research_adapter import run_pipeline
from terminal.utils.error_handling import dev_detail_caption, is_error, safe_render
from terminal.utils.skeletons import chart_skeleton, kpi_skeleton


def _looks_like_non_equity(fundamentals) -> bool:
    """Detect tickers the stock provider could not resolve to a company.

    Indices and broad ETFs (DJI, SPY, VIX, etc.) have no income
    statement and no market cap under FMP. Returning True here tells
    the page to show a clear nudge to Market Overview instead of
    rendering an n/a KPI strip with stale chart data.
    """
    if fundamentals is None or is_error(fundamentals):
        return True
    has_fin = hasattr(fundamentals, "has_financials") and fundamentals.has_financials()
    mkt_cap = float(getattr(fundamentals, "market_cap", 0) or 0)
    return (not has_fin) and mkt_cap <= 0


def _render_non_equity_state(ticker: str) -> None:
    accent = TOKENS["accent_primary"]
    st.markdown(
        f'<div style="font-family:{TOKENS["font_mono"]};font-size:0.82rem;'
        f'color:{TOKENS["text_primary"]};background:{TOKENS["bg_surface"]};'
        f'border:1px solid {TOKENS["border_default"]};'
        f'border-left:3px solid {accent};padding:0.8rem 1rem;margin:0.4rem 0;">'
        f'<span style="color:{accent};font-weight:800;letter-spacing:0.08em;'
        f'text-transform:uppercase;">Index or ETF detected.</span><br/>'
        f'<span style="color:{TOKENS["text_secondary"]};font-size:0.72rem;">'
        f'The Research workspace runs on single-stock fundamentals from FMP. '
        f'<b>{ticker}</b> has no income statement or market cap on the provider '
        f'and is almost certainly an index, sector ETF, currency, or future. '
        f'Use <b>Market Overview</b> for cross-asset and index context.</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    ticker = st.session_state.get("active_ticker", "AAPL")

    styled_header(f"Research. {ticker}", "Deterministic pipeline | Sub scores | Memo synthesis")

    # Fetch raw building blocks before the pipeline so Phase 1 KPIs
    # always have data, even on hard_failure.
    raw_prices = data_manager.get_stock_prices(ticker, config["research"]["default_price_period"])
    raw_fundamentals = data_manager.get_fundamentals(ticker)

    # Guard: indices/ETFs have no fundamentals. Nudge to Market Overview.
    if _looks_like_non_equity(raw_fundamentals):
        _render_non_equity_state(ticker)
        return

    chart_slot = chart_skeleton(height=380)
    kpi_slot = kpi_skeleton(rows=2, cells=6)
    with st.spinner(f"Running research pipeline for {ticker}."):
        try:
            packet = run_pipeline(ticker, data_manager, config)
        except Exception as exc:
            packet = {"status": "hard_failure", "ticker": ticker, "reason": "pipeline error"}
            dev_detail_caption(f"run_pipeline raised: {type(exc).__name__}: {exc}")
    chart_slot.empty()
    kpi_slot.empty()

    # Build a partial packet so the skeleton always has something to render.
    packet.setdefault("ticker", ticker)
    packet.setdefault("engines", {})
    packet.setdefault("recommendation", {
        "rating": "INSUFFICIENT_DATA", "composite_score": float("nan"),
        "confidence": 0.0, "confidence_grade": "F",
        "sub_scores": {}, "override_reason": None, "rule_trace": [],
    })
    packet.setdefault("scenarios", [])
    # Inject raw data if pipeline didn't (e.g. hard_failure).
    packet.setdefault("prices", raw_prices)
    packet.setdefault("fundamentals", raw_fundamentals)
    packet.setdefault("analyst", data_manager.get_analyst_data(ticker))
    packet.setdefault("ownership", data_manager.get_ownership(ticker))
    packet.setdefault("earnings", data_manager.get_earnings(ticker))

    row1_l, row1_r = st.columns([1, 1])
    with row1_l:
        safe_render(lambda: render_phase1_chart(packet, data_manager),
                    label="phase1_chart", source="FMP")
    with row1_r:
        safe_render(lambda: render_phase1_stats(packet), label="phase1_stats", source="FMP")

    # Engine grid next to the LLM memo so the memo is not buried
    # under three more sections. 55/45 split gives the 2x2 engine
    # grid enough breathing room while the memo column still shows
    # a full TLDR card and the expander trigger.
    engines_col, memo_col = st.columns([55, 45])
    with engines_col:
        safe_render(lambda: render_phase2_engines(packet), label="phase2_engines", source="FMP")
    with memo_col:
        safe_render(lambda: render_phase4_llm(packet, config), label="phase4_llm", source="anthropic")

    # Deterministic rating stays below the engines as the conclusion
    # of the pipeline. Full width so the composite score bar has
    # room to read every sub-score segment.
    safe_render(lambda: render_phase3_recommendation(packet), label="phase3_recommendation", source="local")

    # Ownership and earnings side by side to save vertical space.
    own_col, earn_col = st.columns(2)
    with own_col:
        safe_render(lambda: render_ownership(packet.get("ownership", {})), label="ownership", source="yfinance")
    with earn_col:
        safe_render(lambda: render_earnings(packet.get("earnings", {})), label="earnings", source="yfinance")

    # News feed at the bottom.
    safe_render(lambda: render_news(ticker, data_manager), label="news", source="yfinance")


render()
