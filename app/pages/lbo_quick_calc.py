"""ANALYTICS. LBO Quick Calc workspace.

Renders base case LBO mechanics, the equity bridge waterfall, and the
IRR sensitivity heatmap. Defaults come from config.yaml; users can
tweak them in the sidebar.
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
    styled_card,
    styled_divider,
    styled_header,
    styled_kpi,
    styled_section_label,
)

from terminal.adapters.lbo_adapter import run_base_case, sensitivity_grid  # noqa: E402
from terminal.engines.pnl_engine import compute_lbo_equity_bridge  # noqa: E402
from terminal.utils.chart_helpers import heatmap, interpretation_callout_html, waterfall  # noqa: E402
from terminal.utils.formatting import fmt_money, fmt_pct, fmt_ratio  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    styled_header("LBO Quick Calc", "Base case mechanics | Equity bridge | IRR sensitivity")

    defaults = config["lbo_quick_calc"]["defaults"]
    assumptions = _render_sidebar_inputs(defaults)

    result = run_base_case(assumptions)
    styled_section_label("OUTPUTS")
    _render_summary(result)
    styled_divider()
    styled_section_label("EQUITY BRIDGE")
    _render_bridge(result)
    styled_divider()
    styled_section_label("IRR SENSITIVITY")
    _render_sensitivity(assumptions, config)


def _render_sidebar_inputs(defaults) -> dict:
    st.sidebar.markdown("### LBO Assumptions")
    st.sidebar.caption(
        "Model limitations. Base case only, no Monte Carlo, no covenant "
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
        styled_kpi("ENTRY EV", fmt_money(result["entry_ev"]))
    with cols[1]:
        styled_kpi("SPONSOR EQUITY", fmt_money(result["sponsor_equity"]))
    with cols[2]:
        styled_kpi("EXIT EV", fmt_money(result["exit_ev"]))
    with cols[3]:
        irr = result["irr"]
        irr_color = TOKENS["accent_success"] if (irr == irr and irr >= 0) else TOKENS["accent_danger"]
        styled_kpi("IRR", fmt_pct(irr), delta_color=irr_color)
    with cols[4]:
        styled_kpi("MOIC", fmt_ratio(result["moic"]))


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
        title="Equity Value Bridge. Entry to Exit",
        y_unit="USD",
    )
    st.plotly_chart(fig, use_container_width=True)
    styled_card(
        interpretation_callout_html(
            observation=f"Total value created. {fmt_money(bridge['total_value_creation'])}.",
            interpretation="Decomposes sponsor equity growth into operating, multiple, and leverage legs.",
            implication="A plan relying mostly on multiple expansion is more fragile than one driven by EBITDA growth or deleveraging.",
        ),
        accent_color=TOKENS["accent_primary"],
    )


def _render_sensitivity(assumptions, config) -> None:
    sens = config["lbo_quick_calc"]["sensitivity"]
    exit_mult = list(sens["exit_multiples"])
    growth = list(sens["growth_rates"])
    grid = sensitivity_grid(assumptions, exit_mult, growth)
    df = pd.DataFrame(grid, index=[f"{g * 100:.0f}%" for g in growth], columns=[f"{m:.1f}x" for m in exit_mult])
    fig = heatmap(df, title="IRR. Exit Multiple by Revenue Growth", colorbar_unit="IRR")
    st.plotly_chart(fig, use_container_width=True)
    best = max(max(row) for row in grid)
    worst = min(min(row) for row in grid)
    styled_card(
        interpretation_callout_html(
            observation=f"IRR ranges from {worst * 100:+.1f}% to {best * 100:+.1f}% across the grid.",
            interpretation="Wide dispersion signals high sensitivity to exit multiple or operating performance.",
            implication="Tight dispersion is safer; wide dispersion demands a tighter thesis on exit assumptions.",
        ),
        accent_color=TOKENS["accent_primary"],
    )


render()
