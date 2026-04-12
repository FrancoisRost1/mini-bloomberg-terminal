"""ANALYTICS. LBO Quick Calc workspace."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from style_inject import TOKENS, styled_header  # noqa: E402

from app.pages._lbo_helpers import render_assumptions_row, render_credit_metrics, render_sources_and_uses  # noqa: E402
from terminal.adapters.lbo_adapter import run_base_case, sensitivity_grid  # noqa: E402
from terminal.engines.pnl_engine import compute_lbo_equity_bridge  # noqa: E402
from terminal.utils.chart_helpers import heatmap, waterfall  # noqa: E402
from terminal.utils.density import colored_dataframe, dense_kpi_rows, section_bar, signed_color  # noqa: E402
from terminal.utils.formatting import fmt_money, fmt_pct, fmt_ratio  # noqa: E402


def render() -> None:
    config = st.session_state["_config"]
    styled_header("LBO Quick Calc", "Base case mechanics | Equity bridge | IRR sensitivity")

    defaults = config["lbo_quick_calc"]["defaults"]
    assumptions = _render_sidebar_inputs(defaults)
    result = run_base_case(assumptions)

    st.markdown(section_bar("LBO MODEL", source="local"), unsafe_allow_html=True)
    render_assumptions_row(assumptions)
    # Outputs + Sources & Uses at the top (full width). Bridge and
    # sensitivity sit side by side below so the page reads as one
    # scrollable dashboard instead of three stacked tabs with empty
    # vertical space between them.
    _render_summary(result)
    bridge_col, sens_col = st.columns([1, 1])
    with bridge_col:
        _render_bridge(result)
    with sens_col:
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
    # 11 KPIs with wide labels ("EQUITY EXIT", "ENTRY EBITDA") do not
    # fit in a single row without clipping. Split into two rows of six
    # and five: row 1 = entry side, row 2 = exit side + returns.
    st.markdown(dense_kpi_rows(items, rows=2, min_cell_px=135), unsafe_allow_html=True)
    debt_rate = float(st.session_state["_config"]["lbo_quick_calc"]["defaults"]["debt_rate"])
    render_credit_metrics(result, debt_rate=debt_rate)
    render_sources_and_uses(result)


def _render_bridge(result) -> None:
    st.markdown(section_bar("EQUITY BRIDGE"), unsafe_allow_html=True)
    bridge = compute_lbo_equity_bridge(result)
    implied_equity_delta = float(result["equity_at_exit"]) - float(result["sponsor_equity"])
    bridge_total = float(bridge["total_value_creation"])
    reconciled = abs(bridge_total - implied_equity_delta) < 1.0
    status = "RECONCILED" if reconciled else "BRIDGE MISMATCH"
    st.caption(f"DATA LIVE | {status} | bridge {fmt_money(bridge_total)} vs equity delta {fmt_money(implied_equity_delta)}")
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
    fig.update_layout(height=280)
    st.plotly_chart(fig, use_container_width=True)
    bridge_table = pd.DataFrame(
        [
            ("EBITDA growth", float(bridge["ebitda_growth"])),
            ("Multiple change", float(bridge["multiple_expansion"])),
            ("Debt paydown", float(bridge["debt_paydown"])),
            ("Fees drag", float(bridge["fees_drag"])),
            ("Total value", float(bridge["total_value_creation"])),
        ],
        columns=["Leg", "Value"],
    )
    st.dataframe(
        colored_dataframe(bridge_table, ["Value"], format_map={"Value": fmt_money}),
        use_container_width=True, hide_index=True,
    )


def _render_sensitivity(assumptions, config) -> None:
    st.markdown(section_bar("IRR SENSITIVITY"), unsafe_allow_html=True)
    sens = config["lbo_quick_calc"]["sensitivity"]
    exit_mult = list(sens["exit_multiples"])
    growth = list(sens["growth_rates"])
    grid = sensitivity_grid(assumptions, exit_mult, growth)
    df = pd.DataFrame(grid, index=[f"{g * 100:.0f}%" for g in growth], columns=[f"{m:.1f}x" for m in exit_mult])
    fig = heatmap(df, title="IRR. Exit Multiple by Revenue Growth", colorbar_unit="IRR")
    fig.update_layout(height=280)
    st.plotly_chart(fig, use_container_width=True)
    display = df.map(lambda v: f"{v * 100:+.1f}%" if v == v else "n/a")
    display.insert(0, "Growth", display.index)
    directional = [c for c in display.columns if c != "Growth"]
    st.dataframe(colored_dataframe(display, directional), use_container_width=True, hide_index=True)


render()
