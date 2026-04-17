"""Portfolio Builder progressive render helpers.

Split from ``portfolio_builder.py`` on 2026-04-17 when the skeleton +
hydrate pipeline pushed the entry page over the 150 line budget. The
entry file now only handles config reads, ticker input, and delegating
to ``render_progressive(...)`` here.

Shape of the flow:

1. ``render_progressive`` paints every section bar plus a placeholder
   skeleton for every downstream chart / KPI row. Streamlit renders
   these instantly because they are pure HTML strings.
2. The data fetch + optimizer call runs inline.
3. Each ``st.empty`` slot is cleared and the real content is rendered
   into its ``slot.container()`` so the skeleton is replaced in place.

This way a cold LinkedIn click sees the full page shell on first paint
and each region fills as the pipeline completes, instead of staring at
a blank screen for 35 seconds.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.pages._portfolio_alloc import render_allocation_donut, render_efficient_frontier
from app.pages._portfolio_helpers import (
    render_backtest_chart,
    render_correlation_heatmap,
    render_drawdown_chart,
    render_risk_contributions,
)
from app.pages._portfolio_metrics import render_backtest_metrics
from terminal.adapters.optimizer_adapter import run_optimizer
from terminal.utils.density import dense_kpi_row, dense_kpi_rows, section_bar, signed_color
from terminal.utils.error_handling import is_error
from terminal.utils.formatting import fmt_pct, fmt_ratio
from terminal.utils.skeletons import chart_skeleton, kpi_skeleton


def fetch_returns(data_manager, tickers) -> tuple[pd.DataFrame | None, list[str], str]:
    """Cascade 5y/3Y -> 1y -> 6mo with minimum row guards per tier."""
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


def _method_pane(method: str, w: dict[str, float], returns: pd.DataFrame, kpi_slot) -> None:
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
    kpi_slot.markdown(dense_kpi_rows(items, rows=2, min_cell_px=135), unsafe_allow_html=True)
    rows = [{"Asset": a, "Weight": f"{wt * 100:.1f}%",
             "60D Trend": (1 + returns[a]).cumprod().tail(60).tolist() if a in returns.columns else []}
            for a, wt in sorted(w.items(), key=lambda kv: -kv[1])]
    table_col, donut_col = st.columns([3, 2])
    with table_col:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                     column_config={"60D Trend": st.column_config.LineChartColumn("60D", width="small")})
    with donut_col:
        render_allocation_donut(w, method)


def _concentration_kpis(weights: dict[str, dict[str, float]]) -> str:
    items: list[dict] = []
    for method, w in weights.items():
        herf = sum(v ** 2 for v in w.values())
        eff_n = 1.0 / herf if herf > 0 else float("nan")
        items.append({"label": f"{method.upper()} HHI", "value": fmt_ratio(herf, decimals=3, suffix="")})
        items.append({"label": f"{method.upper()} EFF N", "value": f"{eff_n:.1f}"})
        items.append({"label": f"{method.upper()} TOP", "value": fmt_pct(max(w.values()) if w else 0)})
    return dense_kpi_row(items, min_cell_px=135)


def render_progressive(data_manager, config: dict, tickers: list[str]) -> None:
    """Paint page shell, then hydrate each region as data returns."""
    data_slot = st.empty()
    data_slot.caption("Fetching prices and running optimizer...")

    row1_l, row1_r = st.columns([1, 1])
    with row1_l:
        st.markdown(section_bar("MEAN VARIANCE"), unsafe_allow_html=True)
        mv_kpi = kpi_skeleton(rows=2, cells=3)
        mv_body = chart_skeleton(height=220)
    with row1_r:
        st.markdown(section_bar("HRP"), unsafe_allow_html=True)
        hrp_kpi = kpi_skeleton(rows=2, cells=3)
        hrp_body = chart_skeleton(height=220)

    row2_l, row2_r = st.columns([1, 1])
    with row2_l:
        st.markdown(section_bar("CONCENTRATION"), unsafe_allow_html=True)
        conc_slot = kpi_skeleton(rows=1, cells=6)
        frontier_slot = chart_skeleton(height=260)
        metrics_slot = kpi_skeleton(rows=1, cells=5)
    with row2_r:
        backtest_slot = chart_skeleton(height=300)
        drawdown_slot = chart_skeleton(height=220)

    row3_l, row3_r = st.columns([1, 1])
    with row3_l:
        risk_slot = chart_skeleton(height=280)
    with row3_r:
        corr_slot = chart_skeleton(height=280)

    all_slots = [mv_kpi, mv_body, hrp_kpi, hrp_body, conc_slot, frontier_slot,
                 metrics_slot, backtest_slot, drawdown_slot, risk_slot, corr_slot]

    returns, excluded, tier = fetch_returns(data_manager, tickers)
    if returns is None or returns.shape[1] < 2:
        for slot in all_slots:
            slot.empty()
        data_slot.caption("DATA OFF | no historical data for any ticker | tried 5y / 1y / 6mo")
        return
    msg = (f"DATA PARTIAL | TIER {tier} | excluded {len(excluded)}: {', '.join(excluded)}"
           if excluded else f"DATA LIVE | TIER {tier} | {returns.shape[1]} assets / {len(returns)} obs")
    data_slot.caption(msg)

    optimizer_out = run_optimizer(returns, config["portfolio"])
    weights = optimizer_out["weights"]
    cov = optimizer_out.get("cov")
    methods = list(weights.keys())

    if methods:
        mv_body.empty()
        with mv_body.container():
            _method_pane(methods[0], weights[methods[0]], returns, mv_kpi)
    if len(methods) > 1:
        hrp_body.empty()
        with hrp_body.container():
            _method_pane(methods[1], weights[methods[1]], returns, hrp_kpi)

    conc_slot.markdown(_concentration_kpis(weights), unsafe_allow_html=True)
    for slot, renderer in (
        (frontier_slot, lambda: render_efficient_frontier(returns, weights)),
        (metrics_slot, lambda: render_backtest_metrics(returns, weights)),
        (backtest_slot, lambda: render_backtest_chart(returns, weights)),
        (drawdown_slot, lambda: render_drawdown_chart(returns, weights)),
        (risk_slot, lambda: render_risk_contributions(returns, weights, cov)),
        (corr_slot, lambda: render_correlation_heatmap(returns)),
    ):
        slot.empty()
        with slot.container():
            renderer()
