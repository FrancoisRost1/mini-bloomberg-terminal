"""AnalyticsManager.

Caches expensive adapter outputs (LBO snapshots, factor exposures, Greeks,
robustness reports) keyed by ticker + config hash, so that config changes
invalidate automatically and repeated page renders stay cheap.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..config_loader import config_hash
from ..data.cache import DiskCache


class AnalyticsManager:
    """Disk-cached memoizer for deterministic adapter outputs.

    Keys incorporate the active config hash so mutating any weight or
    threshold in config.yaml invalidates cached analytics automatically.
    """

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        cache_dir = Path(config["_meta"]["project_root"]) / "data" / "cache"
        self.cache = DiskCache(cache_dir, config_hash(config))
        self.ttl = float(config["data"]["cache_ttl"]["engine_results"])

    def memoize(
        self,
        namespace: str,
        key: str,
        compute_fn: Callable[[], Any],
    ) -> Any:
        cached = self.cache.get(namespace, key)
        if cached is not None:
            return cached
        value = compute_fn()
        self.cache.set(namespace, key, value, self.ttl)
        return value

    def invalidate(self, namespace: str | None = None) -> int:
        return self.cache.clear(namespace)
