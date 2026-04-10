"""Pickle-backed cache with config-hash-aware keys.

Why pickle, not JSON: JSON silently corrupts pandas DataFrames via
``default=str`` and forces reconstruction. We cache expensive provider
responses and engine outputs; losing dtype fidelity is not acceptable.
"""

from __future__ import annotations

import hashlib
import pickle
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    stored_at: float
    ttl: float

    def is_fresh(self) -> bool:
        return (time.time() - self.stored_at) < self.ttl


class DiskCache:
    """Small pickle cache on disk, keyed by (namespace, config_hash, args).

    Not designed to replace Redis. It exists to keep API spend low on
    low-tier Alpha Vantage plans and to make page navigation snappy.
    """

    def __init__(self, base_dir: Path, config_hash: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.config_hash = config_hash

    def _path(self, namespace: str, key: str) -> Path:
        digest = hashlib.sha256(f"{self.config_hash}|{key}".encode()).hexdigest()[:24]
        return self.base_dir / f"{namespace}__{digest}.pkl"

    def get(self, namespace: str, key: str) -> Any | None:
        path = self._path(namespace, key)
        if not path.exists():
            return None
        try:
            with path.open("rb") as handle:
                entry: CacheEntry = pickle.load(handle)
            if not entry.is_fresh():
                path.unlink(missing_ok=True)
                return None
            return entry.value
        except (pickle.UnpicklingError, EOFError, AttributeError):
            path.unlink(missing_ok=True)
            return None

    def set(self, namespace: str, key: str, value: Any, ttl: float) -> None:
        entry = CacheEntry(value=value, stored_at=time.time(), ttl=ttl)
        path = self._path(namespace, key)
        with path.open("wb") as handle:
            pickle.dump(entry, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def clear(self, namespace: str | None = None) -> int:
        removed = 0
        for path in self.base_dir.glob("*.pkl"):
            if namespace is None or path.name.startswith(f"{namespace}__"):
                path.unlink(missing_ok=True)
                removed += 1
        return removed
