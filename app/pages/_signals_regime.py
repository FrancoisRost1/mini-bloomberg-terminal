"""Live regime classification for the Signals page.

Wraps the P5 rule-based classifier (`terminal.adapters.regime_adapter.run_regime`)
and renders the regime label plus component signals.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from style_inject import TOKENS, styled_section_label  # noqa: E402
from terminal.adapters.regime_adapter import run_regime  # noqa: E402
from terminal.data.schemas import MacroData, PriceData  # noqa: E402


_ACCENT = TOKENS.get("accent_primary", "#FF8C00")
_REGIME_COLORS = {"RISK_ON": "#00C853", "NEUTRAL": _ACCENT, "RISK_OFF": "#FF1744"}

_SIGNAL_LABELS = {
    "trend_return_pct": "TREND",
    "annualized_vol": "ANN VOL",
    "drawdown_pct": "DRAWDOWN",
    "hy_spread": "HY SPREAD",
}


@st.cache_data(ttl=900, show_spinner=False)
def compute_regime_state(_config: dict, _data_manager) -> dict:
    """Compute current regime classification via the P5 run_regime function."""
    try:
        regime_cfg = _config.get("market", {}).get("regime", {})
        index_data = _data_manager.get_index_prices("SPY", period="1y")
        if not isinstance(index_data, PriceData) or index_data.is_empty():
            return {"regime": "UNAVAILABLE", "confidence": 0, "signals": {}, "error": "SPY price data unavailable"}
        spy_close = index_data.prices["close"]

        macro = _data_manager.get_macro(["BAMLH0A0HYM2"])
        hy_spread = None
        if isinstance(macro, MacroData):
            hy_spread = macro.series.get("BAMLH0A0HYM2")

        return run_regime(spy_close, hy_spread, regime_cfg)
    except Exception as e:
        return {"regime": "UNAVAILABLE", "confidence": 0, "signals": {}, "error": str(e)}


def _format_value(key: str, value) -> str:
    if value is None:
        return "n/a"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if v != v:  # NaN
        return "n/a"
    if key == "trend_return_pct":
        return f"{v:+.1%}"
    if key == "annualized_vol":
        return f"{v:.1%}"
    if key == "drawdown_pct":
        return f"{v:.1%}"
    if key == "hy_spread":
        return f"{v:.2f}%"
    return f"{v:.2f}"


def _signal_color(key: str, value) -> str:
    if value is None:
        return "#555"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "#888"
    if v != v:
        return "#555"
    if key == "trend_return_pct":
        return "#00C853" if v > 0 else "#FF1744" if v < 0 else "#888"
    if key == "annualized_vol":
        return "#00C853" if v < 0.20 else _ACCENT if v < 0.30 else "#FF1744"
    if key == "drawdown_pct":
        return "#00C853" if v > -0.05 else _ACCENT if v > -0.10 else "#FF1744"
    if key == "hy_spread":
        return "#00C853" if v < 4.0 else _ACCENT if v < 5.0 else "#FF1744"
    return "#888"


def _kpi_html(label: str, value: str, color: str) -> str:
    return (
        f'<div style="background:#0E1117;border:1px solid #222;border-radius:3px;padding:0.65rem 0.9rem;">'
        f'<div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;margin-bottom:0.3rem;">{label}</div>'
        f'<div style="font-family:monospace;font-size:1.2rem;font-weight:600;color:{color};">{value}</div>'
        f'</div>'
    )


def render_regime_status(regime_state: dict) -> None:
    styled_section_label("REGIME STATUS")

    regime = regime_state.get("regime", "UNAVAILABLE")
    confidence = regime_state.get("confidence", 0)
    color = _REGIME_COLORS.get(regime, "#555")

    conf_str = f"{confidence:.0%}" if isinstance(confidence, (int, float)) else "n/a"
    badge_html = '<div style="display:flex;align-items:center;gap:16px;margin-bottom:12px;">'
    badge_html += f'<span style="background:{color};color:#000;padding:6px 16px;font-weight:bold;font-family:monospace;font-size:18px;letter-spacing:1px;">{regime}</span>'
    badge_html += f'<span style="color:#888;font-family:monospace;font-size:14px;">Confidence: {conf_str}</span>'
    badge_html += '</div>'
    st.markdown(badge_html, unsafe_allow_html=True)

    signals = regime_state.get("signals", {})
    display_keys = [k for k in _SIGNAL_LABELS if k in signals]
    if display_keys:
        cols = st.columns(len(display_keys))
        for col, key in zip(cols, display_keys):
            value = signals.get(key)
            with col:
                st.markdown(
                    _kpi_html(_SIGNAL_LABELS[key], _format_value(key, value), _signal_color(key, value)),
                    unsafe_allow_html=True,
                )
    elif regime == "UNAVAILABLE":
        err = regime_state.get("error", "Regime data unavailable")
        st.markdown(
            f'<div style="color:#FF1744;font-family:monospace;font-size:12px;">DEGRADED: {err}</div>',
            unsafe_allow_html=True,
        )

    if regime == "RISK_ON":
        interp = "Trend, volatility, and credit signals all point to favorable conditions. Full positioning is appropriate."
    elif regime == "RISK_OFF":
        interp = "Multiple stress signals active. Reduced exposure or defensive positioning warranted."
    elif regime == "NEUTRAL":
        interp = "Mixed signals across regime components. No strong directional bias from macro conditions."
    else:
        interp = "Unable to classify current regime. Check data availability."

    st.markdown(
        f'<div style="color:#888;font-size:12px;margin-top:4px;padding:8px;border-left:2px solid {_ACCENT};font-family:monospace;">{interp}</div>',
        unsafe_allow_html=True,
    )
