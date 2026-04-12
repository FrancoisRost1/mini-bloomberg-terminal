"""Portfolio Builder backtest metrics table.

Five-row summary (Ann Return / Ann Vol / Sharpe / Max DD / Calmar)
for MV vs HRP vs Equal Weight. Split out of _portfolio_attribution
so both modules stay under the 150 line budget.

Values are computed from the same ``build_portfolio_series`` path
as the cumulative return and drawdown charts so the numbers
reconcile against what the user sees in the right column.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from style_inject import TOKENS

from app.pages._portfolio_common import build_portfolio_series
from terminal.utils.density import section_bar


def _metrics_for_series(port: pd.Series) -> dict[str, float]:
    if port is None or port.empty:
        return {"ret": float("nan"), "vol": float("nan"), "sharpe": float("nan"),
                "mdd": float("nan"), "calmar": float("nan")}
    ret = float(port.mean() * 252.0)
    vol = float(port.std() * (252.0 ** 0.5))
    sharpe = (ret / vol) if vol > 0 else float("nan")
    nav = (1.0 + port).cumprod()
    peak = nav.cummax()
    mdd = float((nav / peak - 1.0).min())
    calmar = (ret / abs(mdd)) if mdd < 0 else float("nan")
    return {"ret": ret, "vol": vol, "sharpe": sharpe, "mdd": mdd, "calmar": calmar}


def _rank_color(value: float, values: list[float], higher_is_better: bool) -> str:
    """Green for best, red for worst, muted for middle across the row.

    ``higher_is_better=True`` gives max the green tag. Max DD is fed
    with higher_is_better=True so the least-negative drawdown wins.
    """
    clean = [v for v in values if v == v]
    if value != value or len(clean) < 2:
        return TOKENS["text_primary"]
    best = max(clean) if higher_is_better else min(clean)
    worst = min(clean) if higher_is_better else max(clean)
    if value == best and best != worst:
        return TOKENS["accent_success"]
    if value == worst and best != worst:
        return TOKENS["accent_danger"]
    return TOKENS["text_primary"]


def _fmt(key: str, value: float) -> str:
    if value != value:
        return "n/a"
    if key == "vol":
        return f"{value * 100:.1f}%"
    if key in {"ret", "mdd"}:
        return f"{value * 100:+.1f}%"
    return f"{value:.2f}"


def render_backtest_metrics(returns: pd.DataFrame,
                            weights: dict[str, dict[str, float]]) -> None:
    """Dense HTML table summarizing the three methods on five metrics."""
    st.markdown(section_bar("BACKTEST METRICS"), unsafe_allow_html=True)
    if returns is None or returns.empty:
        st.caption("DATA OFF | no return history available")
        return
    port_returns = build_portfolio_series(returns, weights)
    ordered_names: list[str] = [
        label for label in ("MEAN VARIANCE", "HRP", "EQUAL WEIGHT")
        if label in port_returns
    ]
    if not ordered_names:
        st.caption("DATA OFF | no methods to summarize")
        return
    metrics = {name: _metrics_for_series(port_returns[name]) for name in ordered_names}
    short = {"MEAN VARIANCE": "MV", "HRP": "HRP", "EQUAL WEIGHT": "EW"}

    rows: list[tuple[str, str, bool]] = [
        ("Ann Return", "ret",    True),
        ("Ann Vol",    "vol",    False),
        ("Sharpe",     "sharpe", True),
        ("Max DD",     "mdd",    True),    # less negative is better
        ("Calmar",     "calmar", True),
    ]

    mono = TOKENS["font_mono"]
    muted = TOKENS["text_muted"]
    border = TOKENS["border_subtle"]
    th = (
        f"font-family:{mono};font-size:0.6rem;color:{muted};"
        "text-transform:uppercase;letter-spacing:0.08em;font-weight:700;"
        f"border-bottom:1px solid {border};padding:0.18rem 0.5rem;text-align:right;"
    )
    th_left = th.replace("text-align:right", "text-align:left")
    td = (
        f"font-family:{mono};font-size:0.72rem;font-weight:600;"
        f"padding:0.18rem 0.5rem;text-align:right;border-bottom:1px solid {border};"
    )
    td_label = (
        f"font-family:{mono};font-size:0.66rem;color:{muted};"
        f"padding:0.18rem 0.5rem;text-align:left;border-bottom:1px solid {border};"
    )

    headers = ["Metric"] + [short[n] for n in ordered_names]
    head_html = "".join(
        f'<th style="{th_left if i == 0 else th}">{h}</th>'
        for i, h in enumerate(headers)
    )
    body: list[str] = []
    for row_label, key, higher in rows:
        vals = [metrics[n][key] for n in ordered_names]
        cells = [f'<td style="{td_label}">{row_label}</td>']
        for v in vals:
            color = _rank_color(v, vals, higher)
            cells.append(f'<td style="{td}color:{color};">{_fmt(key, v)}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(
        '<table style="width:100%;border-collapse:collapse;'
        'margin:0.2rem 0 0.9rem 0;">'
        f'<thead><tr>{head_html}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table>',
        unsafe_allow_html=True,
    )
