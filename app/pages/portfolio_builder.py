"""PORTFOLIO. Portfolio Builder workspace. 2x2 multi pane layout."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from style_inject import styled_header  # noqa: E402

from terminal.adapters.optimizer_adapter import run_optimizer  # noqa: E402
from terminal.utils.chart_helpers import bar_chart  # noqa: E402
from terminal.utils.density import dense_kpi_row, section_bar, signed_color  # noqa: E402
from terminal.utils.error_handling import degraded_card, is_error, status_pill  # noqa: E402
from terminal.utils.formatting import fmt_pct, fmt_ratio  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    styled_header("Portfolio Builder", "MV and HRP | Concentration | Robustness deferred to v2")
    st.sidebar.markdown("### Portfolio limitations")
    st.sidebar.caption("v1 implements MV and HRP only. Ledoit Wolf covariance by default. Phase 3 deferred.")

    tickers = _ticker_input(config)
    if len(tickers) < int(config["portfolio"]["optimizer"]["min_assets"]):
        st.info(f"Enter at least {config['portfolio']['optimizer']['min_assets']} tickers to build a portfolio.")
        return

    returns, excluded, tier = _fetch_returns(data_manager, tickers)
    if returns is None or returns.shape[1] < 2:
        st.caption("DATA OFF | no historical data for any ticker | tried 5y / 1y / 6mo")
        return
    if excluded:
        st.caption(f"DATA PARTIAL | TIER {tier} | excluded {len(excluded)}: {', '.join(excluded)}")
    else:
        st.caption(f"DATA LIVE | TIER {tier} | {returns.shape[1]} assets / {len(returns)} obs")

    weights = run_optimizer(returns, config["portfolio"])["weights"]
    methods = list(weights.keys())

    row1_l, row1_r = st.columns([1, 1])
    if methods:
        with row1_l:
            _render_method_pane(methods[0], weights[methods[0]], returns)
    if len(methods) > 1:
        with row1_r:
            _render_method_pane(methods[1], weights[methods[1]], returns)

    row2_l, row2_r = st.columns([1, 1])
    with row2_l:
        _render_concentration(weights)
    with row2_r:
        _render_validate_pane()


def _ticker_input(config) -> list[str]:
    watchlist = st.session_state.get("_watchlist")
    existing = watchlist.list_tickers() if watchlist is not None else []
    default = ", ".join(existing) if existing else "SPY, QQQ, TLT, GLD, EFA"
    raw = st.text_input("Tickers (comma separated)", value=default)
    return [t.strip().upper() for t in raw.split(",") if t.strip()]


def _fetch_returns(data_manager, tickers) -> tuple[pd.DataFrame | None, list[str], str]:
    """Cascade 5y/3Y -> 1y -> 6mo with min row guards."""
    tiers = [("5y", "3Y", 756, 504), ("1y", "1Y", 252, 126), ("6mo", "6M", 126, 60)]
    for period, tier, target, min_rows in tiers:
        closes: dict[str, pd.Series] = {}
        excluded: list[str] = []
        for t in tickers:
            d = data_manager.get_any_prices(t, period=period)
            if is_error(d) or d.is_empty():
                excluded.append(t)
            else:
                closes[t] = d.prices["close"]
        if not closes:
            continue
        df = pd.DataFrame(closes).dropna(how="all").pct_change().dropna()
        if len(df) >= min_rows:
            return df.tail(target), excluded, tier
    return None, list(tickers), "NONE"


def _render_method_pane(method: str, w: dict[str, float], returns: pd.DataFrame) -> None:
    st.markdown(section_bar(method.replace("_", " ").upper(), source="FMP + yfinance"), unsafe_allow_html=True)
    series = pd.Series(w).reindex(returns.columns).fillna(0)
    port = returns.dot(series)
    ann_ret = float(port.mean() * 252)
    ann_vol = float(port.std() * (252 ** 0.5))
    sharpe = ann_ret / ann_vol if ann_vol > 0 else float("nan")
    items = [
        {"label": "ANN RET", "value": fmt_pct(ann_ret), "value_color": signed_color(ann_ret)},
        {"label": "ANN VOL", "value": fmt_pct(ann_vol)},
        {"label": "SHARPE", "value": fmt_ratio(sharpe, suffix=""), "value_color": signed_color(sharpe)},
        {"label": "MAX W", "value": fmt_pct(max(w.values()) if w else 0)},
        {"label": "MIN W", "value": fmt_pct(min(w.values()) if w else 0)},
        {"label": "ASSETS", "value": str(sum(1 for v in w.values() if v > 1e-4))},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=85), unsafe_allow_html=True)
    rows = [{"Asset": a, "Weight": f"{wt * 100:.1f}%",
             "60D Trend": (1 + returns[a]).cumprod().tail(60).tolist() if a in returns.columns else []}
            for a, wt in sorted(w.items(), key=lambda kv: -kv[1])]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                 column_config={"60D Trend": st.column_config.LineChartColumn("60D", width="small")})
    st.plotly_chart(
        bar_chart({k: float(v) for k, v in w.items()}, title=f"{method} weights", y_unit="weight"),
        use_container_width=True,
    )


def _render_concentration(weights: dict[str, dict[str, float]]) -> None:
    st.markdown(section_bar("CONCENTRATION"), unsafe_allow_html=True)
    items: list[dict] = []
    for method, w in weights.items():
        herf = sum(v ** 2 for v in w.values())
        eff_n = 1.0 / herf if herf > 0 else float("nan")
        items.append({"label": f"{method.upper()} HHI", "value": fmt_ratio(herf, decimals=3, suffix="")})
        items.append({"label": f"{method.upper()} EFF N", "value": f"{eff_n:.1f}"})
        items.append({"label": f"{method.upper()} TOP", "value": fmt_pct(max(w.values()) if w else 0)})
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)


def _render_validate_pane() -> None:
    st.markdown(section_bar("PHASE 3. VALIDATE"), unsafe_allow_html=True)
    st.markdown(status_pill("DEFERRED TO v2", "missing"), unsafe_allow_html=True)
    st.caption(
        "Robustness validation needs a real parameter grid. The robustness adapter "
        "(terminal/adapters/robustness_adapter.py) is available standalone and will "
        "be wired into a real CSCV sweep in v2. See docs/analysis.md."
    )


render()
