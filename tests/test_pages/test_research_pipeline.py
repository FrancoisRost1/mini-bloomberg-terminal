"""Integration test: full Research pipeline on synthetic data.

Covered by the spec (Section 12). Uses the ``FakeProvider`` so the test
runs fully offline and does not touch Alpha Vantage or yfinance.
"""

from __future__ import annotations

import copy

import pytest

from terminal.adapters.research_adapter import run_pipeline
from terminal.data.schemas import ProviderError
from terminal.managers.data_manager import SharedDataManager
from tests.fakes import FakeProvider


@pytest.fixture
def wired_manager(config, tmp_path):
    cfg = copy.deepcopy(config)
    cfg["_meta"]["project_root"] = str(tmp_path)
    (tmp_path / "data" / "cache").mkdir(parents=True, exist_ok=True)
    mgr = SharedDataManager(cfg)
    mgr.registry._equity = FakeProvider(cfg)
    return cfg, mgr


def test_pipeline_end_to_end_success(wired_manager):
    cfg, mgr = wired_manager
    packet = run_pipeline("AAPL", mgr, cfg)
    assert packet["status"] == "success"
    assert packet["ticker"] == "AAPL"
    assert "engines" in packet
    assert set(packet["engines"].keys()) >= {"pe_scoring", "factor_exposure", "tsmom", "lbo"}


def test_pipeline_recommendation_is_valid_rating(wired_manager):
    cfg, mgr = wired_manager
    packet = run_pipeline("AAPL", mgr, cfg)
    rec = packet["recommendation"]
    assert rec["rating"] in {"BUY", "HOLD", "SELL", "INSUFFICIENT_DATA"}
    assert rec["confidence_grade"] in {"A", "B", "C", "D", "F"}
    assert "composite_score" in rec
    assert "rule_trace" in rec


def test_pipeline_includes_scenario_payoffs(wired_manager):
    cfg, mgr = wired_manager
    packet = run_pipeline("AAPL", mgr, cfg)
    scenarios = packet["scenarios"]
    assert len(scenarios) == len(cfg["pnl"]["scenarios"])
    for scenario in scenarios:
        assert "dollar_pnl" in scenario
        assert "price_target" in scenario


def test_pipeline_hard_fails_on_no_prices(config, tmp_path):
    cfg = copy.deepcopy(config)
    cfg["_meta"]["project_root"] = str(tmp_path)
    (tmp_path / "data" / "cache").mkdir(parents=True, exist_ok=True)
    mgr = SharedDataManager(cfg)
    mgr.registry._equity = FakeProvider(cfg, fail_on={"BADTKR"})
    packet = run_pipeline("BADTKR", mgr, cfg)
    assert packet["status"] == "hard_failure"
    assert packet["reason"] == "no price data"


def test_pipeline_recommendation_reproducible(wired_manager):
    cfg, mgr = wired_manager
    # Same inputs -> same deterministic rating (no RNG, no network).
    first = run_pipeline("AAPL", mgr, cfg)["recommendation"]
    second = run_pipeline("AAPL", mgr, cfg)["recommendation"]
    assert first["rating"] == second["rating"]
    assert first["composite_score"] == second["composite_score"]
