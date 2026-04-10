"""Error boundary helpers for the UI.

The app must never crash on data failure. These helpers render explicit
DEGRADED / DATA UNAVAILABLE cards that keep the layout intact while
flagging exactly what broke.
"""

from __future__ import annotations

from typing import Any

from .formatting import badge

DEGRADED_COLOR = "#FFAB00"
UNAVAILABLE_COLOR = "#FF3D57"
DEV_COLOR = "#00B0FF"


def degraded_card(reason: str, provider: str = "-") -> str:
    return f'<div style="padding:12px 16px;background:#161A23;border-left:3px solid {DEGRADED_COLOR};border-radius:4px;font-family:JetBrains Mono,monospace;color:#E6E6E6;font-size:12px;">{badge("DEGRADED", DEGRADED_COLOR)}<div style="margin-top:6px;color:#AAA;">Provider: {provider}</div><div style="margin-top:4px;">{reason}</div></div>'


def unavailable_card(what: str, reason: str) -> str:
    return f'<div style="padding:12px 16px;background:#161A23;border-left:3px solid {UNAVAILABLE_COLOR};border-radius:4px;font-family:JetBrains Mono,monospace;color:#E6E6E6;font-size:12px;">{badge("DATA UNAVAILABLE", UNAVAILABLE_COLOR)}<div style="margin-top:6px;color:#AAA;">{what}</div><div style="margin-top:4px;">{reason}</div></div>'


def dev_mode_banner() -> str:
    return f'<div style="padding:8px 14px;background:#161A23;border:1px solid {DEV_COLOR};border-radius:4px;font-family:JetBrains Mono,monospace;color:{DEV_COLOR};font-size:11px;text-align:center;letter-spacing:0.5px;">{badge("DEV MODE", DEV_COLOR)}  Serving development data (yfinance). Not for production use.</div>'


def is_error(obj: Any) -> bool:
    """True if ``obj`` is a ProviderError returned from the data manager."""
    return hasattr(obj, "reason") and hasattr(obj, "provider") and hasattr(obj, "data_type")
