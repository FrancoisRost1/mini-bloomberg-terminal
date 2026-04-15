"""TSMOM live signal computation for the Signals page.

Computes today's 12-1 momentum signal snapshot for each ETF in the P6
universe. Not a backtest, just the current-day signal.

Signal: sign(cumulative_return(t-252, t-21))
  LONG  if return > flat_threshold
  SHORT if return < -flat_threshold
  FLAT  if |return| <= flat_threshold
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from terminal.data.schemas import PriceData  # noqa: E402


def _compute_single_signal(prices, lookback: int, skip: int, flat_thresh: float, vol_halflife: int) -> dict:
    """Compute TSMOM signal for a single ETF from its price history."""
    if prices is None or len(prices) < lookback + 10:
        return {"signal": "NO DATA", "return_12_1": None, "ann_vol": None}

    close = prices["close"] if "close" in prices.columns else prices.iloc[:, 0]
    close = close.dropna()
    if len(close) < lookback + 10:
        return {"signal": "NO DATA", "return_12_1": None, "ann_vol": None}

    p_end = close.iloc[-skip] if skip > 0 else close.iloc[-1]
    idx_start = -(lookback + skip)
    p_start = close.iloc[idx_start] if abs(idx_start) <= len(close) else close.iloc[0]
    ret_12_1 = (p_end / p_start) - 1.0

    if abs(ret_12_1) <= flat_thresh:
        signal = "FLAT"
    elif ret_12_1 > 0:
        signal = "LONG"
    else:
        signal = "SHORT"

    daily_ret = close.pct_change().dropna()
    ann_vol = None
    if len(daily_ret) > vol_halflife:
        ann_vol = float(daily_ret.ewm(halflife=vol_halflife).std().iloc[-1] * np.sqrt(252))

    return {"signal": signal, "return_12_1": float(ret_12_1), "ann_vol": ann_vol}


def _compute_prior_signal(prices, lookback: int, skip: int, flat_thresh: float) -> str:
    """Compute yesterday's signal for change detection."""
    close = prices["close"] if "close" in prices.columns else prices.iloc[:, 0]
    close = close.dropna()
    if len(close) < lookback + skip + 2:
        return "NO DATA"

    prior_close = close.iloc[:-1]
    p_end = prior_close.iloc[-skip] if skip > 0 else prior_close.iloc[-1]
    idx_start = -(lookback + skip)
    p_start = prior_close.iloc[idx_start] if abs(idx_start) <= len(prior_close) else prior_close.iloc[0]
    ret = (p_end / p_start) - 1.0

    if abs(ret) <= flat_thresh:
        return "FLAT"
    return "LONG" if ret > 0 else "SHORT"


@st.cache_data(ttl=900, show_spinner=False)
def compute_tsmom_signals(_config: dict, _data_manager) -> pd.DataFrame:
    """Compute TSMOM signals for the full 13-ETF universe."""
    sig_cfg = _config.get("signals", {}).get("tsmom", {})
    lookback = sig_cfg.get("lookback_days", 252)
    skip = sig_cfg.get("skip_days", 21)
    flat_thresh = sig_cfg.get("flat_threshold", 0.01)
    vol_hl = sig_cfg.get("vol_halflife", 60)
    universe = sig_cfg.get("universe", {})

    rows = []
    for asset_class, etfs in universe.items():
        for etf in etfs:
            ticker = etf["ticker"]
            label = etf["label"]
            prices = None
            try:
                price_data = _data_manager.get_index_prices(ticker, period="2y")
                if isinstance(price_data, PriceData) and not price_data.is_empty():
                    prices = price_data.prices
            except Exception:
                prices = None

            result = _compute_single_signal(prices, lookback, skip, flat_thresh, vol_hl)

            has_hist = prices is not None and len(prices) >= lookback + skip + 2
            prior = _compute_prior_signal(prices, lookback, skip, flat_thresh) if has_hist else "NO DATA"
            changed = (result["signal"] != prior and result["signal"] != "NO DATA" and prior != "NO DATA")

            rows.append({
                "ticker": ticker, "name": label,
                "asset_class": asset_class.replace("_", " ").title(),
                "signal": result["signal"], "return_12_1": result["return_12_1"],
                "ann_vol": result["ann_vol"], "prior_signal": prior, "changed": changed,
            })

    return pd.DataFrame(rows)
