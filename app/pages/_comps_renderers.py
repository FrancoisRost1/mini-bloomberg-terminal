"""Comps page tab renderers: valuation card, PE score, M&A comps."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from style_inject import TOKENS

from app.pages._comps_charts import render_pe_metric_bars
from terminal.adapters.ma_comps_adapter import run_comps
from terminal.adapters.pe_scoring_adapter import score_single_ticker
from terminal.utils.density import colored_dataframe, dense_kpi_row, dense_kpi_rows, section_bar, signed_color
from terminal.utils.error_handling import inline_status_line, status_pill
from terminal.utils.formatting import format_metric


_SHORT_LABELS = {
    "ebitda margin":    "EBITDA MGN",
    "revenue growth":   "REV GR",
    "net debt/ebitda":  "ND/EBITDA",
    "fcf conversion":   "FCF CONV",
}


def render_valuation_card(fundamentals, config) -> None:
    st.markdown(section_bar("VALUATION METRICS"), unsafe_allow_html=True)
    metrics = config["comps"]["metrics"]
    items = [{"label": "SECTOR", "value": (fundamentals.sector or "n/a")[:14]}]
    for m in metrics:
        fmt = m.get("format", "ratio")
        value = fundamentals.key_ratios.get(m["key"])
        raw_label = m["label"].strip().lower()
        short = _SHORT_LABELS.get(raw_label, m["label"].upper())
        items.append({"label": short, "value": format_metric(value, fmt)})
    # This card lives in a 50% column on the Comps scrollable layout.
    # 8 KPIs in 2 rows of 4 at 160px so labels like "EBITDA MGN" and
    # "ND/EBITDA" have room to breathe on either side.
    st.markdown(dense_kpi_rows(items, rows=2, min_cell_px=160), unsafe_allow_html=True)


def render_pe_score(ratios, config) -> None:
    """PE Screener composite. KPI strip + chart + per-metric table."""
    st.markdown(section_bar("PE TARGET SCREENER SCORE"), unsafe_allow_html=True)
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
    items = [
        {"label": "COMPOSITE", "value": f"{score:.1f}" if score == score else "n/a", "delta_color": color},
        {"label": "RED FLAGS", "value": str(len(result.get("red_flags", []))),
         "delta_color": TOKENS["accent_danger"] if result.get("red_flags") else TOKENS["accent_success"]},
        {"label": "VALID METRICS", "value": str(result.get("valid_metric_count", 0))},
    ]
    for k, v in result["per_metric_scores"].items():
        items.append({
            "label": k.upper().replace("_", " "),
            "value": f"{v:.0f}" if v == v else "n/a",
            "delta_color": signed_color(v - 50) if v == v else None,
        })
    # 10 items (3 summary + 7 per-metric) in a full-width strip were
    # clipping "REVENUE GROWTH" and "NET DEBT EBITDA". Split into 3
    # rows at 150px so every label renders in full.
    st.markdown(dense_kpi_rows(items, rows=3, min_cell_px=150), unsafe_allow_html=True)

    chart_col, table_col = st.columns([1, 1])
    with chart_col:
        render_pe_metric_bars(ratios, config["comps"]["pe_scoring_bands"])
    with table_col:
        per_metric = {k: v for k, v in result["per_metric_scores"].items() if v == v}
        if per_metric:
            df = pd.DataFrame(
                [(k.replace("_", " ").title(), round(v - 50, 1)) for k, v in per_metric.items()],
                columns=["Metric", "Score (vs 50)"],
            )
            styler = colored_dataframe(df, ["Score (vs 50)"]).format({"Score (vs 50)": "{:.1f}"})
            st.dataframe(styler, use_container_width=True, hide_index=True)
        flags = result.get("red_flags", [])
        flag_text = f"{len(flags)} red flag(s)" if flags else "No red flags"
        st.caption(f"{flag_text}. Score blends margin, FCF, leverage, ROE, and valuation bands.")


def render_ma_comps(sector, config) -> None:
    st.markdown(section_bar("RECENT M&A COMPS", source="P4 ma-database"), unsafe_allow_html=True)
    project_root = Path(config["_meta"]["project_root"])
    allow_synthetic = bool(config["comps"].get("allow_synthetic_demo", False))
    comps = run_comps(
        sector=sector,
        project_root=project_root,
        max_rows=int(config["comps"]["max_peers"]),
        allow_synthetic=allow_synthetic,
    )
    if comps["status"] == "data_unavailable":
        st.markdown(inline_status_line("OFF", source="ma_comps"), unsafe_allow_html=True)
        st.caption("M&A database not connected. Add data/raw/ma_deals.csv to activate this pane.")
        return
    if comps.get("data_source") == "synthetic":
        st.markdown(status_pill("SYNTHETIC DEMO DATA. NOT REAL DEALS", "failed"), unsafe_allow_html=True)
    table = comps["comps_table"]
    if table.empty:
        st.caption(
            f"No M&A deals in sector {sector!r}. "
            "Cross-sector deals are intentionally not shown; the M&A comps "
            "pane only lists transactions whose sector label matches the "
            "active ticker."
        )
        return
    display = table.copy()
    _fmt_mult = lambda v: f"{v:.1f}x" if v == v and v > 0 else "n/a"
    _fmt_pct = lambda v: f"{v:.0f}%" if v == v else "n/a"
    if "ev_usd" in display.columns:
        display["ev_usd"] = display["ev_usd"].apply(
            lambda v: f"${v / 1e9:,.2f}B" if v == v and v > 0 else "n/a"
        )
    for col in ("ev_ebitda", "ev_revenue"):
        if col in display.columns:
            display[col] = display[col].apply(_fmt_mult)
    if "premium_pct" in display.columns:
        display["premium_pct"] = display["premium_pct"].apply(_fmt_pct)
    rename = {
        "year": "Year", "target": "Target", "acquirer": "Acquirer",
        "sector": "Sector", "deal_type": "Type", "ev_usd": "EV",
        "ev_ebitda": "EV/EBITDA", "ev_revenue": "EV/Rev",
        "premium_pct": "Premium",
    }
    display = display.rename(columns={k: v for k, v in rename.items() if k in display.columns})
    st.dataframe(display, use_container_width=True, hide_index=True)
    cov = comps.get("coverage") or {}
    parts = [f"Showing {len(display)} deals in sector '{sector}' from Project 4 (ma-database)."]
    for field, label in [("ev_ebitda", "EV/EBITDA"), ("ev_revenue", "EV/Rev"), ("premium_pct", "Premium")]:
        c = float(cov.get(field, 0.0))
        if 0 < c < 1.0:
            parts.append(f"{label} {c * 100:.0f}% disclosed.")
    parts.append("Public M&A data often has incomplete multiples and premiums.")
    st.caption(" ".join(parts))
