"""ANALYTICS. Comps Relative Value workspace.

Peer comps table, single ticker valuation positioning, and a slice of
the M&A database for sector matched deal multiples.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import (  # noqa: E402
    TOKENS,
    styled_card,
    styled_divider,
    styled_header,
    styled_kpi,
    styled_section_label,
)

from terminal.adapters.ma_comps_adapter import run_comps  # noqa: E402
from terminal.adapters.pe_scoring_adapter import score_single_ticker  # noqa: E402
from terminal.utils.chart_helpers import bar_chart, interpretation_callout_html  # noqa: E402
from terminal.utils.error_handling import degraded_card, is_error, status_pill, unavailable_card  # noqa: E402
from terminal.utils.formatting import format_metric  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    data_manager = st.session_state["_data_manager"]
    ticker = st.session_state.get("active_ticker", "AAPL")

    styled_header(f"Comps Relative Value. {ticker}", "Valuation bands | PE score | M&A comps")

    fundamentals = data_manager.get_fundamentals(ticker)
    if is_error(fundamentals):
        st.markdown(degraded_card(fundamentals.reason, fundamentals.provider), unsafe_allow_html=True)
        return

    sector = fundamentals.sector
    styled_kpi("SECTOR", sector)

    styled_divider()
    _render_valuation_card(fundamentals.key_ratios, config)
    styled_divider()
    _render_pe_score(fundamentals.key_ratios, config)
    styled_divider()
    _render_ma_comps(sector, config)


def _render_valuation_card(ratios, config) -> None:
    styled_section_label("VALUATION METRICS")
    metrics = config["comps"]["metrics"]
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            fmt = m.get("format", "ratio")
            value = ratios.get(m["key"])
            styled_kpi(m["label"].upper(), format_metric(value, fmt))


def _render_pe_score(ratios, config) -> None:
    styled_section_label("PE TARGET SCREENER SCORE")
    result = score_single_ticker(ratios, config["comps"]["pe_scoring_bands"])
    score = result["pe_score"]
    if score == score:
        if score >= 60:
            color = TOKENS["accent_success"]
        elif score >= 40:
            color = TOKENS["accent_warning"]
        else:
            color = TOKENS["accent_danger"]
    else:
        color = TOKENS["text_muted"]
    styled_kpi("COMPOSITE PE SCORE", f"{score:.1f}" if score == score else "n/a", delta_color=color)
    per_metric = {k: v for k, v in result["per_metric_scores"].items() if v == v}
    if per_metric:
        fig = bar_chart(per_metric, title="Per Metric Score (0 to 100)", y_unit="score")
        st.plotly_chart(fig, use_container_width=True)
    styled_card(
        interpretation_callout_html(
            observation=f"{len(result.get('red_flags', []))} red flag(s) detected.",
            interpretation="Score blends EBITDA margin, FCF conversion, leverage, ROE, and valuation bands.",
            implication="Use this as a screening signal, not a buy sell trigger.",
        ),
        accent_color=color,
    )


def _render_ma_comps(sector, config) -> None:
    styled_section_label("RECENT M&A COMPS")
    project_root = Path(config["_meta"]["project_root"])
    allow_synthetic = bool(config["comps"].get("allow_synthetic_demo", False))
    comps = run_comps(
        sector=sector,
        project_root=project_root,
        max_rows=int(config["comps"]["max_peers"]),
        allow_synthetic=allow_synthetic,
    )
    if comps["status"] == "data_unavailable":
        st.markdown(
            unavailable_card("M&A comps unavailable", comps["reason"]),
            unsafe_allow_html=True,
        )
        return
    if comps.get("data_source") == "synthetic":
        st.markdown(
            status_pill("SYNTHETIC DEMO DATA. NOT REAL DEALS", "failed"),
            unsafe_allow_html=True,
        )
    table = comps["comps_table"]
    if table.empty:
        st.markdown(degraded_card("no comps for sector", "ma_comps"), unsafe_allow_html=True)
        return
    st.dataframe(table, use_container_width=True, hide_index=True)


render()
