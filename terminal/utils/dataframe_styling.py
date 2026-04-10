"""Pandas Styler helpers for directional coloring.

Split from density.py so that module stays under the per file budget.
Use ``colored_dataframe`` to wrap any DataFrame whose cells should
render green (positive) or red (negative) by sign.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from style_inject import TOKENS


def _parse_signed(val: Any) -> float:
    """Parse a string or numeric cell into a signed float, NaN if not parseable."""
    if isinstance(val, str):
        try:
            cleaned = (val.replace("%", "").replace("+", "").replace(",", "")
                          .replace("bp", "").replace("x", "").strip())
            return float(cleaned)
        except ValueError:
            return float("nan")
    try:
        return float(val)
    except (TypeError, ValueError):
        return float("nan")


def colored_dataframe(df: pd.DataFrame, directional_cols: list[str] | None = None):
    """Return a pandas Styler that colors directional cells by sign.

    Parses string cells like '+1.23%', '-12.50bp', or numeric cells.
    Use as ``st.dataframe(colored_dataframe(df, ["Chg %", "1D bp"]))``.
    """
    cols = directional_cols or []

    def _color(val: Any) -> str:
        num = _parse_signed(val)
        if num != num or num == 0:
            return ""
        if num > 0:
            return f'color:{TOKENS["accent_success"]};font-weight:600'
        return f'color:{TOKENS["accent_danger"]};font-weight:600'

    styler = df.style
    for col in cols:
        if col in df.columns:
            styler = styler.map(_color, subset=[col])
    return styler
