"""PORTFOLIO: Portfolio Builder workspace.

Two-phase workflow in v1: BUILD (optimizer weights) and DECOMPOSE
(concentration diagnostics).

Phase 3 VALIDATE (PBO / deflated Sharpe / plateau) was REMOVED from v1.
The earlier implementation generated a "trial matrix" by perturbing the
fitted weights with Gaussian noise, which is not a real parameter grid
and the resulting PBO had no statistical meaning. Theatre is worse than
absence. The robustness adapter remains available as a standalone
engine; v2 will reintroduce Phase 3 backed by a real parameter sweep.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from terminal.adapters.optimizer_adapter import run_optimizer
from terminal.utils.chart_helpers import bar_chart, interpretation_callout
from terminal.utils.error_handling import degraded_card, is_error
from terminal.utils.formatting import badge, fmt_ratio, styled_kpi


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]

    st.title("Portfolio Builder")
    st.caption("How should I allocate capital?")
    st.sidebar.markdown("### Portfolio limitations")
    st.sidebar.caption(
        "v1 implements MV and HRP only. Risk Parity and Black-Litterman "
        "are documented future upgrades. Ledoit-Wolf covariance by default. "
        "Phase 3 robustness validation is intentionally deferred to v2 "
        "until a real parameter-sweep trial matrix is wired in."
    )

    tickers = _ticker_input(config)
    if len(tickers) < int(config["portfolio"]["optimizer"]["min_assets"]):
        st.info(f"Enter at least {config['portfolio']['optimizer']['min_assets']} tickers to build a portfolio.")
        return

    returns = _fetch_returns(data_manager, tickers, int(config["portfolio"]["covariance"]["lookback_days"]))
    if returns is None or returns.shape[1] < 2:
        st.markdown(degraded_card("insufficient historical data for selected tickers", "data_manager"), unsafe_allow_html=True)
        return

    st.markdown("## Phase 1: Build")
    optimizer_result = run_optimizer(returns, config["portfolio"])
    _render_weights(optimizer_result["weights"])

    st.markdown("## Phase 2: Decompose")
    _render_concentration(optimizer_result["weights"])

    st.markdown("## Phase 3: Validate")
    st.markdown(
        badge("DEFERRED TO v2", "#FFAB00"),
        unsafe_allow_html=True,
    )
    st.caption(
        "Robustness validation (PBO, deflated Sharpe, plateau fraction) "
        "needs a real parameter grid, not weight perturbations. The "
        "underlying engine (terminal/adapters/robustness_adapter.py) is "
        "available standalone and will be wired into a real CSCV sweep "
        "in v2. See docs/analysis.md for the v2 roadmap."
    )


def _ticker_input(config) -> list[str]:
    watchlist = st.session_state.get("_watchlist")
    existing = watchlist.list_tickers() if watchlist is not None else []
    default = ", ".join(existing) if existing else "SPY, QQQ, TLT, GLD, EFA"
    raw = st.text_input("Tickers (comma separated)", value=default)
    return [t.strip().upper() for t in raw.split(",") if t.strip()]


def _fetch_returns(data_manager, tickers, lookback) -> pd.DataFrame | None:
    period = "5y" if lookback > 504 else "2y"
    closes: dict[str, pd.Series] = {}
    for ticker in tickers:
        data = data_manager.get_prices(ticker, period=period)
        if is_error(data) or data.is_empty():
            continue
        closes[ticker] = data.prices["close"]
    if not closes:
        return None
    df = pd.DataFrame(closes).dropna(how="all")
    returns = df.pct_change().dropna().tail(lookback)
    return returns


def _render_weights(weights: dict[str, dict[str, float]]) -> None:
    cols = st.columns(len(weights))
    for col, (method, w) in zip(cols, weights.items()):
        with col:
            st.markdown(f"#### {method.replace('_', ' ').title()}")
            fig = bar_chart({k: float(v) for k, v in w.items()}, title=f"{method} Weights", y_unit="weight (0-1)")
            st.plotly_chart(fig, use_container_width=True)
            top_asset = max(w.items(), key=lambda kv: kv[1]) if w else ("-", 0.0)
            st.markdown(
                interpretation_callout(
                    observation=f"Largest position: {top_asset[0]} at {top_asset[1] * 100:.1f}%.",
                    interpretation="MV maximizes risk-adjusted return; HRP ignores return estimates and clusters by risk.",
                    implication="Compare both to see how much the optimum depends on mean-return estimation error.",
                ),
                unsafe_allow_html=True,
            )


def _render_concentration(weights: dict[str, dict[str, float]]) -> None:
    cols = st.columns(len(weights))
    for col, (method, w) in zip(cols, weights.items()):
        herf = sum(v ** 2 for v in w.values())
        effective_n = 1.0 / herf if herf > 0 else float("nan")
        with col:
            st.markdown(styled_kpi(f"{method} Herfindahl", fmt_ratio(herf, decimals=3, suffix="")), unsafe_allow_html=True)
            st.markdown(styled_kpi(f"{method} Effective N", f"{effective_n:.1f}"), unsafe_allow_html=True)


render()
