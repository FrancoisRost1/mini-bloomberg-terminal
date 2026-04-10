"""ANALYTICS: LBO Quick Calc workspace.

Renders base-case LBO mechanics + sensitivity grid + P&L equity bridge.
All defaults come from config.yaml; users can tweak them in the sidebar.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap project root for the streamlit-as-script load path.
# See app/app.py docstring for the rationale.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from terminal.adapters.lbo_adapter import run_base_case, sensitivity_grid  # noqa: E402
from terminal.engines.pnl_engine import compute_lbo_equity_bridge  # noqa: E402
from terminal.utils.chart_helpers import heatmap, interpretation_callout, waterfall  # noqa: E402
from terminal.utils.formatting import fmt_money, fmt_pct, fmt_ratio, styled_kpi  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    st.title("LBO Quick Calc")
    st.caption("What are the PE return mechanics for this target?")

    defaults = config["lbo_quick_calc"]["defaults"]
    assumptions = _render_sidebar_inputs(defaults)

    result = run_base_case(assumptions)
    _render_summary(result)
    _render_bridge(result)
    _render_sensitivity(assumptions, config)


def _render_sidebar_inputs(defaults) -> dict:
    st.sidebar.markdown("### LBO Assumptions")
    st.sidebar.caption(
        "Model limitations: base case only, no Monte Carlo, no covenant "
        "breach detection, constant rates, flat margin trajectory."
    )
    assumptions = dict(defaults)
    assumptions["entry_ebitda"] = st.sidebar.number_input("Entry EBITDA ($M)", min_value=1.0, value=100.0, step=10.0) * 1e6
    assumptions["entry_multiple"] = st.sidebar.number_input("Entry Multiple (x)", min_value=1.0, value=float(defaults["entry_multiple"]), step=0.5)
    assumptions["exit_multiple"] = st.sidebar.number_input("Exit Multiple (x)", min_value=1.0, value=float(defaults["exit_multiple"]), step=0.5)
    assumptions["leverage"] = st.sidebar.number_input("Leverage (x EBITDA)", min_value=0.0, value=float(defaults["leverage"]), step=0.25)
    assumptions["revenue_growth"] = st.sidebar.number_input("Revenue Growth", min_value=-0.2, max_value=0.5, value=float(defaults["revenue_growth"]), step=0.01)
    assumptions["hold_period"] = int(st.sidebar.number_input("Hold (years)", min_value=1, max_value=10, value=int(defaults["hold_period"])))
    return assumptions


def _render_summary(result) -> None:
    cols = st.columns(5)
    with cols[0]:
        st.markdown(styled_kpi("Entry EV", fmt_money(result["entry_ev"])), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(styled_kpi("Sponsor Equity", fmt_money(result["sponsor_equity"])), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(styled_kpi("Exit EV", fmt_money(result["exit_ev"])), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(styled_kpi("IRR", fmt_pct(result["irr"])), unsafe_allow_html=True)
    with cols[4]:
        st.markdown(styled_kpi("MOIC", fmt_ratio(result["moic"])), unsafe_allow_html=True)


def _render_bridge(result) -> None:
    bridge = compute_lbo_equity_bridge(result)
    fig = waterfall(
        categories=["EBITDA Growth", "Multiple Change", "Debt Paydown", "Fees", "Total Value"],
        values=[
            bridge["ebitda_growth"],
            bridge["multiple_expansion"],
            bridge["debt_paydown"],
            bridge["fees_drag"],
            bridge["total_value_creation"],
        ],
        title="Equity Value Bridge: Entry to Exit",
        y_unit="USD",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        interpretation_callout(
            observation=f"Total value created: {fmt_money(bridge['total_value_creation'])}.",
            interpretation="Decomposes sponsor equity growth into operating, multiple, and leverage legs.",
            implication="A plan relying mostly on multiple expansion is more fragile than one driven by EBITDA growth or deleveraging.",
        ),
        unsafe_allow_html=True,
    )


def _render_sensitivity(assumptions, config) -> None:
    st.markdown("### IRR Sensitivity")
    sens = config["lbo_quick_calc"]["sensitivity"]
    exit_mult = list(sens["exit_multiples"])
    growth = list(sens["growth_rates"])
    grid = sensitivity_grid(assumptions, exit_mult, growth)
    df = pd.DataFrame(grid, index=[f"{g * 100:.0f}%" for g in growth], columns=[f"{m:.1f}x" for m in exit_mult])
    fig = heatmap(df, title="IRR: Exit Multiple x Revenue Growth", colorbar_unit="IRR")
    st.plotly_chart(fig, use_container_width=True)
    best = max(max(row) for row in grid)
    worst = min(min(row) for row in grid)
    st.markdown(
        interpretation_callout(
            observation=f"IRR ranges from {worst * 100:+.1f}% to {best * 100:+.1f}% across the grid.",
            interpretation="Wide dispersion signals high sensitivity to exit multiple or operating performance.",
            implication="Tight dispersion is safer; wide dispersion demands a tighter thesis on exit assumptions.",
        ),
        unsafe_allow_html=True,
    )


render()
