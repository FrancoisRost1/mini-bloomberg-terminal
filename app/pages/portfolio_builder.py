"""PORTFOLIO: Portfolio Builder workspace.

Three-phase workflow: BUILD (optimizer weights), DECOMPOSE (factor and
concentration diagnostics), VALIDATE (robustness via PBO, DSR, plateau).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from terminal.adapters.optimizer_adapter import run_optimizer
from terminal.adapters.robustness_adapter import run_robustness
from terminal.utils.chart_helpers import bar_chart, interpretation_callout
from terminal.utils.error_handling import degraded_card, is_error
from terminal.utils.formatting import badge, fmt_pct, fmt_ratio, styled_kpi


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]

    st.title("Portfolio Builder")
    st.caption("How should I allocate capital, and is the allocation stable?")
    st.sidebar.markdown("### Portfolio limitations")
    st.sidebar.caption(
        "v1 implements MV and HRP only (Risk Parity and Black-Litterman "
        "are documented future upgrades). Ledoit-Wolf covariance by "
        "default. Transaction costs applied only at rebalance."
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
    _render_robustness(returns, optimizer_result["weights"], config)


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


def _render_robustness(returns: pd.DataFrame, weights: dict[str, dict[str, float]], config) -> None:
    method = next(iter(weights.keys()))
    w = pd.Series(weights[method]).reindex(returns.columns).fillna(0.0)
    portfolio_returns = returns.dot(w)
    # Build a small synthetic trial matrix by perturbing weights; the robustness
    # engine consumes a T x N matrix, not raw weights. This is deliberately
    # simple for v1 since full CSCV on random portfolios is out of scope.
    n_trials = 20
    rng = np.random.default_rng(42)
    trials = []
    metrics = []
    for _ in range(n_trials):
        perturb = rng.normal(0, 0.05, size=len(w))
        w_trial = np.clip(w.values + perturb, 0, None)
        w_trial = w_trial / w_trial.sum()
        t_returns = returns.dot(w_trial)
        trials.append(t_returns.rename(None))
        metrics.append(float(t_returns.mean() / t_returns.std() * np.sqrt(252)) if t_returns.std() > 0 else 0.0)
    trial_matrix = pd.concat(trials, axis=1)
    trial_matrix.columns = [f"trial_{i}" for i in range(n_trials)]
    trial_metrics = pd.Series(metrics, index=trial_matrix.columns)
    report = run_robustness(trial_matrix, trial_metrics, portfolio_returns, config["portfolio"]["robustness"])
    verdict = report["verdict"]
    color_map = {"ROBUST": "#00C853", "LIKELY ROBUST": "#9CCC65", "BORDERLINE": "#FFAB00",
                 "LIKELY OVERFIT": "#FF7043", "OVERFIT": "#FF3D57"}
    st.markdown(styled_kpi("Robustness Verdict", verdict, color_map.get(verdict, "#FF8C00")), unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]:
        st.markdown(styled_kpi("PBO", fmt_ratio(report["pbo"], decimals=3, suffix="")), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(styled_kpi("Deflated Sharpe", fmt_ratio(report["deflated_sharpe"], decimals=3, suffix="")), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(styled_kpi("Plateau Fraction", fmt_pct(report["plateau_fraction"])), unsafe_allow_html=True)
    st.markdown(
        interpretation_callout(
            observation=f"Verdict: {verdict}.",
            interpretation="PBO measures how often IS-best underperforms OOS median; DSR inflates for multiple testing.",
            implication="Robust portfolios earn their verdict because their edge survives both tests.",
        ),
        unsafe_allow_html=True,
    )


render()
