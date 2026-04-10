"""Research page visuals.

- Phase 3 deterministic rating renderer (KPIs + stacked bar + callout).
- Horizontal stacked bar showing the four sub scores as segments and
  the total composite score as a label.
- LLM memo presentation with a one line TLDR, a generation timestamp,
  and the full body wrapped in a collapsible expander.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from style_inject import TOKENS, apply_plotly_theme, styled_card

from terminal.utils.chart_helpers import interpretation_callout_html
from terminal.utils.density import dense_kpi_row, section_bar, signed_color


# Sub score colors. Order matters: same as the bar segment order.
SUB_SCORE_PALETTE: list[tuple[str, str]] = [
    ("valuation", TOKENS["accent_primary"]),
    ("quality",   TOKENS["accent_info"]),
    ("momentum",  TOKENS["accent_success"]),
    ("risk",      TOKENS["accent_warning"]),
]


def render_phase3_recommendation(packet: dict[str, Any]) -> None:
    rec = packet.get("recommendation") or {}
    rating = rec.get("rating", "INSUFFICIENT_DATA")
    color_map = {"BUY": TOKENS["accent_success"], "HOLD": TOKENS["accent_warning"],
                 "SELL": TOKENS["accent_danger"], "INSUFFICIENT_DATA": TOKENS["text_muted"]}
    accent = color_map.get(rating, TOKENS["accent_primary"])
    st.markdown(section_bar("DETERMINISTIC RATING", source="local"), unsafe_allow_html=True)
    composite = rec.get("composite_score", float("nan"))
    items = [
        {"label": "RATING", "value": rating, "delta": f"grade {rec.get('confidence_grade', 'F')}",
         "delta_color": accent, "value_color": accent},
        {"label": "COMPOSITE", "value": f"{composite:.1f}" if composite == composite else "n/a",
         "value_color": signed_color((composite - 50) if composite == composite else 0)},
        {"label": "CONFIDENCE", "value": f"{rec.get('confidence', 0):.2f}"},
    ]
    for key, val in (rec.get("sub_scores") or {}).items():
        items.append({"label": key.upper(), "value": f"{val:.1f}" if val == val else "n/a",
                      "value_color": signed_color(val - 50) if val == val else None})
    st.markdown(dense_kpi_row(items, min_cell_px=118), unsafe_allow_html=True)
    render_score_stacked_bar(rec)
    obs = f"Composite score {composite:.1f}." if composite == composite else "Composite unavailable."
    styled_card(
        interpretation_callout_html(
            observation=obs,
            interpretation="Derived deterministically from valuation, quality, momentum, and risk sub scores.",
            implication=f"Override reason. {rec.get('override_reason') or 'none'}.",
        ),
        accent_color=accent,
    )


def render_score_stacked_bar(rec: dict[str, Any]) -> None:
    """Horizontal stacked bar of valuation / quality / momentum / risk segments.

    Each segment is the sub score weighted by the composite weights so
    the four pieces sum to the composite. The composite score is shown
    as a single annotation on the right of the bar.
    """
    sub = rec.get("sub_scores") or {}
    if not sub:
        return
    composite = rec.get("composite_score")
    weights = {"valuation": 0.35, "quality": 0.25, "momentum": 0.20, "risk": 0.20}
    fig = go.Figure()
    cum = 0.0
    for key, color in SUB_SCORE_PALETTE:
        v = sub.get(key)
        if v is None or v != v:
            continue
        seg = float(v) * weights.get(key, 0.25)
        fig.add_trace(go.Bar(
            x=[seg], y=["COMPOSITE"], orientation="h",
            name=key.upper(),
            marker={"color": color, "line": {"width": 0}},
            text=[f"{key[:3].upper()} {v:.0f}"], textposition="inside",
            insidetextanchor="middle",
            textfont={"family": "JetBrains Mono, monospace", "size": 10,
                      "color": "#FFFFFF"},
            hovertemplate=f"{key}: %{{x:.1f}} pts<extra></extra>",
        ))
        cum += seg
    label = f"COMPOSITE {composite:.1f}" if composite == composite else "COMPOSITE n/a"
    fig.add_annotation(
        x=cum, y="COMPOSITE", xanchor="left", yanchor="middle",
        text=f"  {label}",
        showarrow=False,
        font={"family": "JetBrains Mono, monospace", "size": 12,
              "color": TOKENS["accent_primary"]},
    )
    fig.update_xaxes(title_text="Weighted score (0 to 100)", range=[0, 105])
    fig.update_yaxes(title_text="", showticklabels=False)
    fig.update_layout(
        title={"text": "Composite Score Decomposition"},
        height=140, barmode="stack", showlegend=True,
        legend={"orientation": "h", "y": 1.5, "x": 0},
        margin={"l": 4, "r": 8, "t": 36, "b": 24},
    )
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)


def render_memo_card(memo_result: dict[str, Any], rating: str, composite: float) -> None:
    """One line TLDR + timestamp + collapsible expander with the full memo."""
    if memo_result.get("status") != "success" or not memo_result.get("memo"):
        return
    color_map = {"BUY": TOKENS["accent_success"], "HOLD": TOKENS["accent_warning"],
                 "SELL": TOKENS["accent_danger"], "INSUFFICIENT_DATA": TOKENS["text_muted"]}
    accent = color_map.get(rating, TOKENS["accent_primary"])
    composite_str = f"{composite:.1f}" if composite == composite else "n/a"
    mono = TOKENS["font_mono"]
    text_primary = TOKENS["text_primary"]
    text_muted = TOKENS["text_muted"]
    tldr = (
        f"<div style='font-family:{mono};font-size:0.78rem;"
        f"color:{text_primary};margin:0.15rem 0 0.2rem 0;'>"
        f"<span style='color:{accent};font-weight:700;'>TLDR.</span> "
        f"Deterministic rating <span style='color:{accent};font-weight:700;'>{rating}</span> "
        f"with composite {composite_str}. The narrative below was generated around the locked rating; "
        f"the LLM is forbidden from overriding it."
        f"</div>"
    )
    st.markdown(tldr, unsafe_allow_html=True)
    ts = memo_result.get("generated_at") or "n/a"
    st.markdown(
        f"<div style='font-family:{mono};font-size:0.6rem;"
        f"color:{text_muted};letter-spacing:0.06em;text-transform:uppercase;"
        f"margin-bottom:0.25rem;'>GENERATED {ts} UTC</div>",
        unsafe_allow_html=True,
    )
    with st.expander("Full memo", expanded=False):
        if memo_result.get("inconsistency"):
            st.warning(memo_result["inconsistency"])
        st.markdown(memo_result["memo"])
