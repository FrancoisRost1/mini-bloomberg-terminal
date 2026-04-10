"""ANALYTICS. LBO Quick Calc workspace."""

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
    styled_header,
)

from terminal.adapters.lbo_adapter import run_base_case, sensitivity_grid  # noqa: E402
from terminal.engines.pnl_engine import compute_lbo_equity_bridge  # noqa: E402
from terminal.utils.chart_helpers import heatmap, interpretation_callout_html, waterfall  # noqa: E402
from terminal.utils.density import colored_dataframe, dense_kpi_row, section_bar, signed_color  # noqa: E402
from terminal.utils.formatting import fmt_money, fmt_pct, fmt_ratio  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    styled_header("LBO Quick Calc", "Base case mechanics | Equity bridge | IRR sensitivity")

    defaults = config["lbo_quick_calc"]["defaults"]
    assumptions = _render_sidebar_inputs(defaults)
    result = run_base_case(assumptions)

    st.markdown(section_bar("LBO MODEL", source="local"), unsafe_allow_html=True)
    tab_outputs, tab_bridge, tab_sens = st.tabs(["OUTPUTS", "EQUITY BRIDGE", "IRR SENSITIVITY"])
    with tab_outputs:
        _render_summary(result)
    with tab_bridge:
        _render_bridge(result)
    with tab_sens:
        _render_sensitivity(assumptions, config)


def _render_sidebar_inputs(defaults) -> dict:
    st.sidebar.markdown("### LBO Assumptions")
    st.sidebar.caption("Base case only. No Monte Carlo. Constant rates and margin trajectory.")
    assumptions = dict(defaults)
    assumptions["entry_ebitda"] = st.sidebar.number_input("Entry EBITDA ($M)", min_value=1.0, value=100.0, step=10.0) * 1e6
    assumptions["entry_multiple"] = st.sidebar.number_input("Entry Multiple (x)", min_value=1.0, value=float(defaults["entry_multiple"]), step=0.5)
    assumptions["exit_multiple"] = st.sidebar.number_input("Exit Multiple (x)", min_value=1.0, value=float(defaults["exit_multiple"]), step=0.5)
    assumptions["leverage"] = st.sidebar.number_input("Leverage (x EBITDA)", min_value=0.0, value=float(defaults["leverage"]), step=0.25)
    assumptions["revenue_growth"] = st.sidebar.number_input("Revenue Growth", min_value=-0.2, max_value=0.5, value=float(defaults["revenue_growth"]), step=0.01)
    assumptions["hold_period"] = int(st.sidebar.number_input("Hold (years)", min_value=1, max_value=10, value=int(defaults["hold_period"])))
    return assumptions


def _render_summary(result) -> None:
    irr = result["irr"]
    moic = result["moic"]
    items = [
        {"label": "ENTRY EV", "value": fmt_money(result["entry_ev"])},
        {"label": "ENTRY EBITDA", "value": fmt_money(result["entry_ebitda"])},
        {"label": "ENTRY DEBT", "value": fmt_money(result["entry_debt"])},
        {"label": "SPONSOR EQ", "value": fmt_money(result["sponsor_equity"])},
        {"label": "FEES", "value": fmt_money(result["fees"]), "delta_color": TOKENS["accent_danger"]},
        {"label": "EXIT EBITDA", "value": fmt_money(result["exit_ebitda"])},
        {"label": "EXIT DEBT", "value": fmt_money(result["exit_debt"])},
        {"label": "EXIT EV", "value": fmt_money(result["exit_ev"])},
        {"label": "EQUITY EXIT", "value": fmt_money(result["equity_at_exit"])},
        {"label": "IRR", "value": fmt_pct(irr), "delta_color": signed_color(irr)},
        {"label": "MOIC", "value": fmt_ratio(moic),
         "delta_color": signed_color(moic - 1.0) if moic == moic else None},
    ]
    st.markdown(dense_kpi_row(items, min_cell_px=110), unsafe_allow_html=True)


def _render_bridge(result) -> None:
    bridge = compute_lbo_equity_bridge(result)
    chart_col, table_col = st.columns([2, 3])
    with chart_col:
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
    with table_col:
        bridge_table = pd.DataFrame(
            [
                ("EBITDA growth", bridge["ebitda_growth"]),
                ("Multiple change", bridge["multiple_expansion"]),
                ("Debt paydown", bridge["debt_paydown"]),
                ("Fees drag", bridge["fees_drag"]),
                ("Total value", bridge["total_value_creation"]),
            ],
            columns=["Leg", "Value ($)"],
        )
        st.dataframe(colored_dataframe(bridge_table, ["Value ($)"]),
                     use_container_width=True, hide_index=True)
    styled_card(
        interpretation_callout_html(
            observation=f"Total value created. {fmt_money(bridge['total_value_creation'])}.",
            interpretation="Decomposes sponsor equity growth into operating, multiple, and leverage legs.",
            implication="A plan relying mostly on multiple expansion is more fragile than EBITDA growth or deleveraging.",
        ),
        accent_color=TOKENS["accent_primary"],
    )


def _render_sensitivity(assumptions, config) -> None:
    sens = config["lbo_quick_calc"]["sensitivity"]
    exit_mult = list(sens["exit_multiples"])
    growth = list(sens["growth_rates"])
    grid = sensitivity_grid(assumptions, exit_mult, growth)
    df = pd.DataFrame(grid, index=[f"{g * 100:.0f}%" for g in growth], columns=[f"{m:.1f}x" for m in exit_mult])
    chart_col, table_col = st.columns([2, 3])
    with chart_col:
        fig = heatmap(df, title="IRR. Exit Multiple by Revenue Growth", colorbar_unit="IRR")
        st.plotly_chart(fig, use_container_width=True)
    with table_col:
        display = df.map(lambda v: f"{v * 100:+.1f}%" if v == v else "n/a")
        display.insert(0, "Growth", display.index)
        directional = [c for c in display.columns if c != "Growth"]
        st.dataframe(colored_dataframe(display, directional), use_container_width=True, hide_index=True)


render()
