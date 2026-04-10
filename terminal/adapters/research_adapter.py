"""Research adapter (wraps P10 AI Research Agent orchestrator).

Runs the full deterministic research pipeline for a single ticker:
fetches prices + fundamentals via the shared data manager, invokes
every engine adapter, builds sub-scores (via ``_research_sub_scores``),
runs the recommendation engine, and optionally calls the LLM for memo
synthesis.

Critical invariants:
1. The deterministic rating is computed BEFORE the LLM is ever called.
2. The LLM receives the rating in its prompt and MAY NOT override it.
3. A hard-fail on price or financials skips the whole pipeline with a
   standard dict so the UI can render the error state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from ..engines.pnl_engine import compute_scenario_payoffs
from ..engines.recommendation_engine import run_recommendation
from ..managers.data_manager import SharedDataManager
from ..utils.error_handling import is_error
from . import _research_sub_scores as subs
from .factor_adapter import compute_factor_snapshot
from .lbo_adapter import run_base_case
from .pe_scoring_adapter import score_single_ticker
from .tsmom_adapter import compute_signal


SOURCE_PROJECT = "P10: AI Research Agent"


def run_pipeline(
    ticker: str,
    data_manager: SharedDataManager,
    config: dict[str, Any],
) -> dict[str, Any]:
    """End-to-end Research pipeline. Never raises; always returns a dict."""
    prices = data_manager.get_prices(ticker, config["research"]["default_price_period"])
    fundamentals = data_manager.get_fundamentals(ticker)
    gates = config["research"]["data_gates"]
    if is_error(prices) and gates["hard_fail_on_no_prices"]:
        return _hard_fail(ticker, "no price data", prices)
    if is_error(fundamentals) and gates["hard_fail_on_no_financials"]:
        return _hard_fail(ticker, "no financials", fundamentals)

    price_series = prices.prices["close"] if not prices.is_empty() else pd.Series(dtype=float)
    ratios = dict(fundamentals.key_ratios)
    ratios["market_cap"] = fundamentals.market_cap

    pe_result = score_single_ticker(ratios)
    factor_result = compute_factor_snapshot(ratios, price_series)
    tsmom_result = compute_signal(price_series)
    lbo_assumptions = subs.lbo_assumptions_from_fundamentals(fundamentals, config)
    if lbo_assumptions is None:
        lbo_result = {"status": "failed", "reason": "insufficient financials for LBO"}
    else:
        lbo_result = run_base_case(lbo_assumptions)

    sub_scores = subs.build_sub_scores(pe_result, factor_result, tsmom_result, lbo_result, ratios, price_series)
    confidences = subs.engine_confidences(pe_result, factor_result, tsmom_result, lbo_result)
    flags = {"negative_ebitda": "negative_ebitda" in pe_result.get("red_flags", [])}
    recommendation = run_recommendation(sub_scores, confidences, flags, config["research"])

    spot = float(price_series.iloc[-1]) if not price_series.empty else 0.0
    scenarios = compute_scenario_payoffs(
        {"spot": spot, "shares": 100.0},
        config["pnl"]["scenarios"],
    )

    return {
        "status": "success",
        "source_project": SOURCE_PROJECT,
        "ticker": ticker,
        "as_of": datetime.utcnow().isoformat(),
        "prices": prices,
        "fundamentals": fundamentals,
        "engines": {
            "pe_scoring": pe_result,
            "factor_exposure": factor_result,
            "tsmom": tsmom_result,
            "lbo": lbo_result,
        },
        "recommendation": recommendation,
        "scenarios": scenarios,
    }


def _hard_fail(ticker: str, reason: str, obj: Any) -> dict[str, Any]:
    return {
        "status": "hard_failure",
        "source_project": SOURCE_PROJECT,
        "ticker": ticker,
        "reason": reason,
        "error": obj.as_dict() if hasattr(obj, "as_dict") else str(obj),
    }
