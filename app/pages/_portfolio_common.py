"""Primitives shared by every Portfolio Builder helper module.

Kept in its own file because both ``_portfolio_helpers`` (backtest +
correlation) and ``_portfolio_attribution`` (drawdown + risk
contribution) use the same method -> color palette and the same
portfolio-series builder. Splitting into a third file avoids a circular
import between the two sibling modules.
"""

from __future__ import annotations

import pandas as pd

from style_inject import TOKENS


METHOD_PALETTE: dict[str, str] = {
    "MEAN_VARIANCE": TOKENS["accent_primary"],
    "MEAN VARIANCE": TOKENS["accent_primary"],
    "HRP":           TOKENS["accent_info"],
    "EQUAL WEIGHT":  TOKENS["text_secondary"],
}


def build_portfolio_series(returns: pd.DataFrame,
                           weights: dict[str, dict[str, float]]) -> dict[str, pd.Series]:
    """Weighted daily return series for every method + equal weight.

    Returns a dict keyed by the upper-cased, space-separated method name
    (e.g. "MEAN VARIANCE", "HRP", "EQUAL WEIGHT"). Callers look these up
    in ``METHOD_PALETTE`` to keep the color consistent across every
    portfolio chart.
    """
    out: dict[str, pd.Series] = {}
    for method, w in weights.items():
        wv = pd.Series(w).reindex(returns.columns).fillna(0.0)
        out[method.upper().replace("_", " ")] = returns.dot(wv)
    n = returns.shape[1]
    if n > 0:
        eq = pd.Series([1.0 / n] * n, index=returns.columns)
        out["EQUAL WEIGHT"] = returns.dot(eq)
    return out
