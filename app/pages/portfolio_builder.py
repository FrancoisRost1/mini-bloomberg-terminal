"""PORTFOLIO. Portfolio Builder workspace.

Two phase workflow in v1. BUILD (optimizer weights) and DECOMPOSE
(concentration diagnostics). Phase 3 is deferred to v2 because the
prior implementation generated a fake trial matrix.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from style_inject import (  # noqa: E402
    TOKENS,
    styled_divider,
    styled_header,
    styled_section_label,
)

from terminal.adapters.optimizer_adapter import run_optimizer  # noqa: E402
from terminal.utils.chart_helpers import bar_chart  # noqa: E402
from terminal.utils.density import dense_kpi_row, signed_color  # noqa: E402
from terminal.utils.error_handling import degraded_card, is_error, status_pill  # noqa: E402
from terminal.utils.formatting import fmt_pct, fmt_ratio  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]

    styled_header("Portfolio Builder", "MV and HRP | Concentration | Robustness deferred to v2")
    st.sidebar.markdown("### Portfolio limitations")
    st.sidebar.caption(
        "v1 implements MV and HRP only. Risk Parity and Black Litterman are documented future upgrades. "
        "Ledoit Wolf covariance by default. Phase 3 robustness deferred to v2."
    )

    tickers = _ticker_input(config)
    if len(tickers) < int(config["portfolio"]["optimizer"]["min_assets"]):
        st.info(f"Enter at least {config['portfolio']['optimizer']['min_assets']} tickers to build a portfolio.")
        return

    returns = _fetch_returns(data_manager, tickers, int(config["portfolio"]["covariance"]["lookback_days"]))
    if returns is None or returns.shape[1] < 2:
        st.markdown(degraded_card("insufficient historical data", "data_manager"), unsafe_allow_html=True)
        return

    optimizer_result = run_optimizer(returns, config["portfolio"])
    weights = optimizer_result["weights"]

    styled_section_label("PHASE 1. BUILD")
    _render_weights(weights, returns)
    styled_divider()
    styled_section_label("PHASE 2. DECOMPOSE")
    _render_concentration(weights)
    styled_divider()
    styled_section_label("PHASE 3. VALIDATE")
    st.markdown(status_pill("DEFERRED TO v2", "missing"), unsafe_allow_html=True)
    st.caption(
        "Robustness validation needs a real parameter grid. The robustness adapter "
        "(terminal/adapters/robustness_adapter.py) is available standalone and will "
        "be wired into a real CSCV sweep in v2. See docs/analysis.md."
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
    return df.pct_change().dropna().tail(lookback)


def _render_weights(weights: dict[str, dict[str, float]], returns: pd.DataFrame) -> None:
    cols = st.columns(len(weights))
    for col, (method, w) in zip(cols, weights.items()):
        with col:
            styled_section_label(method.replace("_", " ").upper())
            ann_ret = float((returns.dot(pd.Series(w).reindex(returns.columns).fillna(0))).mean() * 252)
            ann_vol = float((returns.dot(pd.Series(w).reindex(returns.columns).fillna(0))).std() * (252 ** 0.5))
            sharpe = ann_ret / ann_vol if ann_vol > 0 else float("nan")
            items = [
                {"label": "ANN RETURN", "value": fmt_pct(ann_ret), "delta_color": signed_color(ann_ret)},
                {"label": "ANN VOL", "value": fmt_pct(ann_vol)},
                {"label": "SHARPE", "value": fmt_ratio(sharpe, suffix=""), "delta_color": signed_color(sharpe)},
                {"label": "MAX W", "value": fmt_pct(max(w.values()) if w else 0)},
                {"label": "MIN W", "value": fmt_pct(min(w.values()) if w else 0)},
                {"label": "ASSETS", "value": str(sum(1 for v in w.values() if v > 1e-4))},
            ]
            st.markdown(dense_kpi_row(items, min_cell_px=95), unsafe_allow_html=True)
            chart_col, table_col = st.columns([3, 2])
            with chart_col:
                fig = bar_chart(
                    {k: float(v) for k, v in w.items()},
                    title=f"{method} weights", y_unit="weight",
                )
                st.plotly_chart(fig, use_container_width=True)
            with table_col:
                df = pd.DataFrame(
                    sorted(((k, v) for k, v in w.items()), key=lambda kv: -kv[1]),
                    columns=["Asset", "Weight"],
                )
                df["Weight"] = df["Weight"].apply(lambda x: f"{x * 100:.1f}%")
                st.dataframe(df, use_container_width=True, hide_index=True)


def _render_concentration(weights: dict[str, dict[str, float]]) -> None:
    items: list[dict] = []
    for method, w in weights.items():
        herf = sum(v ** 2 for v in w.values())
        effective_n = 1.0 / herf if herf > 0 else float("nan")
        items.append({"label": f"{method.upper()} HHI", "value": fmt_ratio(herf, decimals=3, suffix="")})
        items.append({"label": f"{method.upper()} EFF N", "value": f"{effective_n:.1f}"})
        items.append({"label": f"{method.upper()} TOP", "value": fmt_pct(max(w.values()) if w else 0)})
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)


render()
