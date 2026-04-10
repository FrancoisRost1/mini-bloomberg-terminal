"""Unit tests for the AnalyticsManager memoization layer."""

from __future__ import annotations

import copy
import time

import pytest

from terminal.managers.analytics_manager import AnalyticsManager


@pytest.fixture
def manager(config, tmp_path):
    cfg = copy.deepcopy(config)
    cfg["_meta"]["project_root"] = str(tmp_path)
    (tmp_path / "data" / "cache").mkdir(parents=True, exist_ok=True)
    cfg["data"]["cache_ttl"]["engine_results"] = 60
    return AnalyticsManager(cfg)


def test_memoize_caches_callable(manager):
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"value": 42}

    first = manager.memoize("lbo", "AAPL", compute)
    second = manager.memoize("lbo", "AAPL", compute)
    assert first == second == {"value": 42}
    assert calls["n"] == 1


def test_memoize_recomputes_after_ttl(config, tmp_path):
    cfg = copy.deepcopy(config)
    cfg["_meta"]["project_root"] = str(tmp_path)
    cfg["data"]["cache_ttl"]["engine_results"] = 0.05
    mgr = AnalyticsManager(cfg)
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return calls["n"]

    mgr.memoize("lbo", "AAPL", compute)
    time.sleep(0.1)
    mgr.memoize("lbo", "AAPL", compute)
    assert calls["n"] == 2


def test_config_hash_invalidation(config, tmp_path):
    cfg_a = copy.deepcopy(config)
    cfg_a["_meta"]["project_root"] = str(tmp_path)
    cfg_a["lbo_quick_calc"]["defaults"]["entry_multiple"] = 8.0
    mgr_a = AnalyticsManager(cfg_a)
    mgr_a.memoize("lbo", "AAPL", lambda: "result_a")

    cfg_b = copy.deepcopy(config)
    cfg_b["_meta"]["project_root"] = str(tmp_path)
    cfg_b["lbo_quick_calc"]["defaults"]["entry_multiple"] = 9.0
    mgr_b = AnalyticsManager(cfg_b)
    # Different config hash -> no collision: compute_fn runs again.
    result = mgr_b.memoize("lbo", "AAPL", lambda: "result_b")
    assert result == "result_b"


def test_invalidate_namespace(manager):
    manager.memoize("lbo", "AAPL", lambda: 1)
    manager.memoize("factor", "AAPL", lambda: 2)
    manager.invalidate("lbo")
    calls = {"n": 0}

    def recompute():
        calls["n"] += 1
        return 99

    manager.memoize("lbo", "AAPL", recompute)
    assert calls["n"] == 1
