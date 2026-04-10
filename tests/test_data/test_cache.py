"""Unit tests for the pickle-backed disk cache."""

from __future__ import annotations

import time

import pandas as pd
import pytest

from terminal.data.cache import CacheEntry, DiskCache


@pytest.fixture
def cache(tmp_path):
    return DiskCache(tmp_path / "cache", config_hash="hash_a")


def test_cache_set_and_get_round_trip(cache):
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})
    cache.set("prices", "AAPL|1y", df, ttl=60)
    fetched = cache.get("prices", "AAPL|1y")
    assert fetched is not None
    assert isinstance(fetched, pd.DataFrame)
    pd.testing.assert_frame_equal(fetched, df)


def test_cache_miss_returns_none(cache):
    assert cache.get("prices", "MISSING") is None


def test_cache_expired_entry_evicted(cache):
    cache.set("prices", "AAPL", {"k": 1}, ttl=0.01)
    time.sleep(0.05)
    assert cache.get("prices", "AAPL") is None


def test_cache_entry_freshness():
    entry = CacheEntry(value=1, stored_at=time.time(), ttl=60)
    assert entry.is_fresh()
    stale = CacheEntry(value=1, stored_at=time.time() - 100, ttl=60)
    assert not stale.is_fresh()


def test_cache_config_hash_isolation(tmp_path):
    cache_a = DiskCache(tmp_path / "cache", config_hash="hash_a")
    cache_b = DiskCache(tmp_path / "cache", config_hash="hash_b")
    cache_a.set("prices", "AAPL", {"value": "from_a"}, ttl=60)
    assert cache_a.get("prices", "AAPL") == {"value": "from_a"}
    # Different config hash -> different cache key -> no cross-talk.
    assert cache_b.get("prices", "AAPL") is None


def test_cache_clear_namespace(cache):
    cache.set("prices", "AAPL", 1, ttl=60)
    cache.set("fundamentals", "AAPL", 2, ttl=60)
    cache.clear("prices")
    assert cache.get("prices", "AAPL") is None
    assert cache.get("fundamentals", "AAPL") == 2


def test_cache_clear_all(cache):
    cache.set("prices", "AAPL", 1, ttl=60)
    cache.set("fundamentals", "AAPL", 2, ttl=60)
    removed = cache.clear()
    assert removed == 2
    assert cache.get("prices", "AAPL") is None
    assert cache.get("fundamentals", "AAPL") is None
